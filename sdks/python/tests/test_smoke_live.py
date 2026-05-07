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
