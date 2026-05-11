"""Sprint 2.4 — unit tests for the 7 routing SDK methods.

These tests do NOT hit the network. They monkey-patch ``client._request``
to capture the (method, path, params/json) the SDK would send, then assert
on those captured values. This guards the contract between SDK method
signatures and the customer URL.

Pair with `tests/Feature/RoutingApiTest.php` in the csv2geo repo, which
covers the auth + plan-gate behavior on the server side.
"""

import json
import pytest
from csv2geo import Client
from csv2geo.exceptions import InvalidRequestError


@pytest.fixture
def client():
    """A Client with _request stubbed to capture calls."""
    c = Client(api_key="dummy_key_for_unit_test")
    c._captured = []
    def fake_request(method, path, params=None, json=None, **kw):
        c._captured.append({"method": method, "path": path,
                            "params": params, "json": json})
        return {"results": [], "meta": {"version": "1.0.0"}}
    c._request = fake_request
    yield c
    c.close()


# ─────────────────────────────────────────────────────────
# /v1/routing
# ─────────────────────────────────────────────────────────

def test_route_with_tuple_waypoints(client):
    client.route([(40.7128, -74.0060), (34.0522, -118.2437)], mode="drive")
    call = client._captured[0]
    assert call["method"] == "GET"
    assert call["path"] == "/routing"
    assert call["params"]["waypoints"] == "40.7128,-74.006|34.0522,-118.2437"
    assert call["params"]["mode"] == "drive"

def test_route_with_string_waypoints_passes_through(client):
    client.route("40.7,-74.0|34.0,-118.2", mode="walk")
    assert client._captured[0]["params"]["waypoints"] == "40.7,-74.0|34.0,-118.2"
    assert client._captured[0]["params"]["mode"] == "walk"

def test_route_truck_attrs_sent_when_provided(client):
    client.route(
        [(40.7, -74.0), (34.0, -118.2)],
        mode="truck",
        truck_height=4.0, truck_weight=20000,
        truck_length=15, truck_width=2.5, truck_hazmat=True,
    )
    p = client._captured[0]["params"]
    assert p["truck_height"] == 4.0
    assert p["truck_weight"] == 20000
    assert p["truck_length"] == 15
    assert p["truck_width"] == 2.5
    assert p["truck_hazmat"] == "true"

def test_route_omits_truck_attrs_when_not_provided(client):
    client.route([(40.7, -74.0), (34.0, -118.2)], mode="drive")
    p = client._captured[0]["params"]
    for k in ("truck_height", "truck_weight", "truck_length", "truck_width", "truck_hazmat"):
        assert k not in p, f"{k} leaked into params"

def test_route_alternates_and_instructions(client):
    client.route([(40.7, -74.0), (34.0, -118.2)], mode="drive",
                 alternatives=2, instructions=True, lang="de")
    p = client._captured[0]["params"]
    assert p["alternatives"] == 2
    assert p["instructions"] == "true"
    assert p["lang"] == "de"

def test_route_rejects_single_waypoint(client):
    with pytest.raises(InvalidRequestError):
        # Single point doesn't satisfy "at least 2"; we use the static helper
        # which is permissive for elevation (1+) but the server will 400.
        client.route([(40.7,)], mode="drive")

def test_route_format_polyline(client):
    client.route([(40.7, -74.0), (34.0, -118.2)], mode="drive", format="polyline")
    assert client._captured[0]["params"]["format"] == "polyline"


# ─────────────────────────────────────────────────────────
# /v1/isoline
# ─────────────────────────────────────────────────────────

def test_isoline_with_list_ranges(client):
    client.isoline(40.7, -74.0, "drive", ranges=[300, 600, 900])
    p = client._captured[0]["params"]
    assert client._captured[0]["path"] == "/isoline"
    assert p["lat"] == 40.7 and p["lng"] == -74.0
    assert p["ranges"] == "300,600,900"
    assert p["type"] == "time"  # default

def test_isoline_distance_type(client):
    client.isoline(34.05, -118.24, "walk", ranges=[1000, 2000], type="distance")
    assert client._captured[0]["params"]["type"] == "distance"
    assert client._captured[0]["params"]["ranges"] == "1000,2000"

def test_isoline_with_csv_string_ranges(client):
    client.isoline(40.7, -74.0, "drive", ranges="300,600")
    assert client._captured[0]["params"]["ranges"] == "300,600"

def test_isoline_denoise_passed(client):
    client.isoline(40.7, -74.0, "drive", ranges=[600], denoise=0.8)
    assert client._captured[0]["params"]["denoise"] == 0.8


# ─────────────────────────────────────────────────────────
# /v1/route-matrix
# ─────────────────────────────────────────────────────────

def test_route_matrix_with_dicts(client):
    client.route_matrix(
        sources=[{"lat": 40.7, "lng": -74.0}],
        targets=[{"lat": 34.0, "lng": -118.2}, {"lat": 29.7, "lng": -95.3}],
        mode="drive",
    )
    call = client._captured[0]
    assert call["method"] == "POST"
    assert call["path"] == "/route-matrix"
    body = call["json"]
    assert body["sources"] == [{"lat": 40.7, "lng": -74.0}]
    assert body["targets"] == [{"lat": 34.0, "lng": -118.2}, {"lat": 29.7, "lng": -95.3}]
    assert body["mode"] == "drive"

def test_route_matrix_with_tuples(client):
    client.route_matrix(
        sources=[(40.7, -74.0)],
        targets=[(34.0, -118.2)],
        mode="walk",
    )
    body = client._captured[0]["json"]
    assert body["sources"] == [{"lat": 40.7, "lng": -74.0}]
    assert body["targets"] == [{"lat": 34.0, "lng": -118.2}]

def test_route_matrix_truck_attrs(client):
    client.route_matrix(
        sources=[(40.7, -74.0)], targets=[(34.0, -118.2)], mode="truck",
        truck_height=4.0, truck_hazmat=True,
    )
    body = client._captured[0]["json"]
    assert body["truck_height"] == 4.0
    assert body["truck_hazmat"] is True

def test_route_matrix_include_filter(client):
    client.route_matrix(
        sources=[(40.7, -74.0)], targets=[(34.0, -118.2)], mode="drive",
        include=["durations"],
    )
    assert client._captured[0]["json"]["include"] == ["durations"]


# ─────────────────────────────────────────────────────────
# /v1/map-match
# ─────────────────────────────────────────────────────────

def test_map_match_with_tuple_trace(client):
    client.map_match([(40.7128, -74.006), (40.7130, -74.0058)], mode="drive")
    call = client._captured[0]
    assert call["method"] == "POST"
    assert call["path"] == "/map-match"
    assert call["json"]["trace"] == [
        {"lat": 40.7128, "lng": -74.006},
        {"lat": 40.7130, "lng": -74.0058},
    ]
    assert call["json"]["mode"] == "drive"

def test_map_match_with_dict_trace_preserves_metadata(client):
    client.map_match([
        {"lat": 40.7, "lng": -74.0, "time": "2026-05-11T14:00:00Z", "accuracy_m": 5},
        {"lat": 40.71, "lng": -74.01, "time": "2026-05-11T14:00:05Z", "accuracy_m": 5},
    ], mode="drive", gps_accuracy_m=5)
    trace = client._captured[0]["json"]["trace"]
    assert trace[0]["time"] == "2026-05-11T14:00:00Z"
    assert trace[0]["accuracy_m"] == 5
    assert client._captured[0]["json"]["gps_accuracy_m"] == 5


# ─────────────────────────────────────────────────────────
# /v1/optimize_route
# ─────────────────────────────────────────────────────────

def test_optimize_route_basic(client):
    client.optimize_route([(40.7, -74.0), (34.0, -118.2), (29.7, -95.3)], mode="drive")
    call = client._captured[0]
    assert call["method"] == "GET"
    assert call["path"] == "/optimize_route"
    assert call["params"]["waypoints"] == "40.7,-74.0|34.0,-118.2|29.7,-95.3"

def test_optimize_route_roundtrip(client):
    client.optimize_route([(40.7, -74.0), (34.0, -118.2)], mode="drive", roundtrip=True)
    assert client._captured[0]["params"]["roundtrip"] == "true"


# ─────────────────────────────────────────────────────────
# /v1/locate
# ─────────────────────────────────────────────────────────

def test_locate_basic(client):
    client.locate(40.7128, -74.006)
    call = client._captured[0]
    assert call["method"] == "GET"
    assert call["path"] == "/locate"
    assert call["params"] == {"lat": 40.7128, "lng": -74.006, "mode": "drive"}

def test_locate_with_radius(client):
    client.locate(40.7128, -74.006, mode="truck", radius_m=1000)
    p = client._captured[0]["params"]
    assert p["mode"] == "truck"
    assert p["radius_m"] == 1000


# ─────────────────────────────────────────────────────────
# /v1/elevation
# ─────────────────────────────────────────────────────────

def test_elevation_basic(client):
    client.elevation([(40.7, -74.0), (34.0, -118.2)])
    call = client._captured[0]
    assert call["method"] == "GET"
    assert call["path"] == "/elevation"
    assert call["params"]["points"] == "40.7,-74.0|34.0,-118.2"

def test_elevation_imperial_geojson(client):
    client.elevation([(40.7, -74.0)], units="imperial", format="geojson")
    p = client._captured[0]["params"]
    assert p["units"] == "imperial"
    assert p["format"] == "geojson"


# ─────────────────────────────────────────────────────────
# Cross-cutting: all 7 methods exist + correctly named
# ─────────────────────────────────────────────────────────

def test_all_seven_routing_methods_exist():
    """Locks the public surface — any rename breaks customers."""
    expected = {"route", "isoline", "route_matrix", "map_match",
                "optimize_route", "locate", "elevation"}
    actual = {m for m in dir(Client) if not m.startswith("_")}
    assert expected.issubset(actual), f"missing: {expected - actual}"
