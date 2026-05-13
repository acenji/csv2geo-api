"""Live smoke tests against production.

Skipped by default; runs only when CSV2GEO_TEST_KEY is set in the env
(set on a developer machine or in CI). Catches the class of bug where
the SDK technically compiles but customers can't actually reach the
service with their real key.

Run locally:
    CSV2GEO_TEST_KEY=geo_live_... pytest sdks/python/tests/test_smoke_live.py -v

Run inside CI: store the key in the secret store, expose as env var.
The key used should be a CI-only key, ideally with a low rate limit.
"""

import os
import pytest

from csv2geo import Client


_KEY = os.environ.get("CSV2GEO_TEST_KEY", "")
_HAS_KEY = bool(_KEY and _KEY.startswith("geo_live_"))

skip_if_no_key = pytest.mark.skipif(
    not _HAS_KEY,
    reason="CSV2GEO_TEST_KEY not set or not a geo_live_* key — skipping live tests",
)


@pytest.fixture
def client():
    c = Client(api_key=_KEY)
    yield c
    c.close()


@skip_if_no_key
def test_geocode_returns_200(client):
    """Default URL + real key + simple query = a real geocode result."""
    r = client.geocode("90210")
    # Defensive: response shape may evolve; assert on the must-haves
    assert r is not None
    assert r.lat is not None
    assert r.lng is not None
    # Beverly Hills, CA — known stable answer
    assert 33 < r.lat < 35, f"Latitude {r.lat} far off expected"
    assert -119 < r.lng < -117, f"Longitude {r.lng} far off expected"


@skip_if_no_key
def test_reverse_returns_200(client):
    """White House lat/lng → an address."""
    r = client.reverse(38.8977, -77.0365)
    assert r is not None
    assert r.formatted_address is not None
    assert "Washington" in r.formatted_address or "DC" in r.formatted_address


@skip_if_no_key
def test_ip_endpoint_returns_payload(client):
    """Sprint 2.7 — /v1/ip with a known residential IP returns county overlay."""
    # This endpoint may not exist in older SDK versions; defensive check.
    if not hasattr(client, "ip"):
        pytest.skip("client.ip() not present in this SDK version")
    r = client.ip("8.8.8.8")
    assert r is not None
    # 8.8.8.8 is anycast → country only, but country must be present
    assert r.get("country", {}).get("code") == "US"
    # Confidence label must be set
    assert r.get("confidence") in ("high", "medium", "low")


@skip_if_no_key
def test_invalid_key_returns_401_not_404():
    """If the SDK accidentally pointed at the wrong host, /v1/geocode wouldn't
    exist there and we'd get a 404 / connection error rather than a 401.
    A 401 with invalid_api_key proves we're hitting the right Laravel proxy."""
    c = Client(api_key="geo_live_INVALIDinvalidINVALIDinvalid")
    try:
        from csv2geo.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError):
            c.geocode("90210")
    finally:
        c.close()


# ── Routing (Sprint 2.4) — Pro+ plans only ─────────────────────────────
# These tests gracefully skip if the test key isn't on a Pro/Unlimited
# plan with the `routing` permission. Pass criteria reflect the locked
# spec in overture-geocoder/docs/sprint-2.4-routing-endpoints.md.

def _skip_if_not_pro(client, method_name):
    """If the SDK has the routing method but the key isn't Pro+, skip."""
    if not hasattr(client, method_name):
        pytest.skip(f"client.{method_name}() not in this SDK version")


@skip_if_no_key
def test_routing_drive_nyc_to_la(client):
    _skip_if_not_pro(client, "route")
    try:
        r = client.route(waypoints=[(40.7128, -74.006), (34.0522, -118.2437)], mode="drive")
    except Exception as e:
        # Pro+ gate or permission gate kicks in here on lower-tier keys
        if "permission" in str(e).lower() or "403" in str(e):
            pytest.skip(f"key is not Pro+ for routing: {e}")
        raise
    summary = r["results"][0]["summary"]
    # NYC→LA is roughly 4500 km / 40h via interstate; assert wide bands.
    assert 4_000_000 < summary["distance_m"] < 5_000_000
    assert 100_000 < summary["duration_s"] < 200_000


@skip_if_no_key
def test_routing_isoline_times_square(client):
    _skip_if_not_pro(client, "isoline")
    try:
        r = client.isoline(lat=40.7580, lng=-73.9855, mode="drive", ranges=[600, 900])
    except Exception as e:
        if "permission" in str(e).lower() or "403" in str(e):
            pytest.skip(f"key is not Pro+ for routing: {e}")
        raise
    assert len(r["results"]) == 2
    for entry in r["results"]:
        assert entry["geometry"]["type"] == "Polygon"


@skip_if_no_key
def test_routing_matrix_nyc_to_regional(client):
    _skip_if_not_pro(client, "route_matrix")
    try:
        r = client.route_matrix(
            sources=[{"lat": 40.7128, "lng": -74.006}],
            targets=[{"lat": 42.36, "lng": -71.05}, {"lat": 38.9, "lng": -77.03}],
            mode="drive",
        )
    except Exception as e:
        if "permission" in str(e).lower() or "403" in str(e):
            pytest.skip(f"key is not Pro+ for routing: {e}")
        raise
    d = r["results"]["durations_s"]
    # Both NYC→Boston and NYC→DC must be reachable (proves matrix cap bump).
    assert d[0][0] is not None and d[0][0] > 0
    assert d[0][1] is not None and d[0][1] > 0


@skip_if_no_key
def test_routing_locate_times_square(client):
    _skip_if_not_pro(client, "locate")
    try:
        r = client.locate(lat=40.7580, lng=-73.9855, mode="drive")
    except Exception as e:
        if "permission" in str(e).lower() or "403" in str(e):
            pytest.skip(f"key is not Pro+ for routing: {e}")
        raise
    # Snap should land within a few hundred meters of input
    assert "snapped_lat" in r["result"]
    assert "snapped_lng" in r["result"]
    assert r["result"].get("edge", {}).get("name") is not None


@skip_if_no_key
def test_routing_elevation_skipped_when_dem_missing(client):
    """Elevation returns 503 elevation_data_unavailable until Copernicus
    DEM tiles are installed (Sprint 2.4 followup). Both 200 and that
    specific 503 are acceptable outcomes; anything else is a regression."""
    _skip_if_not_pro(client, "elevation")
    from csv2geo.exceptions import CSV2GEOError
    try:
        r = client.elevation(points=[(39.7392, -104.9903), (40.7128, -74.006)])
        # If we got here, DEM tiles are live — assert real numbers.
        assert r["results"][0]["elevation_m"] is not None
    except CSV2GEOError as e:
        msg = str(e).lower()
        # APIError msg from the handler is "elevation tiles are not installed
        # on this geocoder node — please retry later" with code=elevation_data_unavailable.
        # We accept either textual signal OR the explicit error_code on the exception.
        code = getattr(e, "code", "") or ""
        if "elevation tiles are not installed" in msg or code == "elevation_data_unavailable":
            pytest.skip("DEM tiles not yet installed (expected pre-Phase-1c)")
        if "permission" in msg or code in ("plan_permission_denied", "insufficient_permissions"):
            pytest.skip(f"key is not Pro+ for routing: {e}")
        raise
