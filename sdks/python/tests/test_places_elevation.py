"""Sprint ele-on-places 2026-05-24 — unit tests asserting that
?include=elevation reaches the wire on every Places-family method.

The server-side ele logic is covered by the geocoder Go tests; here we
lock the SDK ↔ API contract: a customer who passes include="elevation"
(or "other_names,elevation") gets that exact string forwarded on the
URL the server actually sees.

No network. Pattern mirrors tests/test_reverse_radius.py.
"""

import pytest
from csv2geo import Client


@pytest.fixture
def client():
    """A Client with _request stubbed to capture the params it would send."""
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
# include="elevation" alone — every Places method.
# ─────────────────────────────────────────────────────────

def test_places_forwards_include_elevation(client):
    client.places(query="cafe", country="US", include="elevation")
    assert client._captured[0]["params"]["include"] == "elevation"


def test_places_nearby_forwards_include_elevation(client):
    client.places_nearby(38.8977, -77.0365, radius_m=300, include="elevation")
    assert client._captured[0]["params"]["include"] == "elevation"


def test_places_random_forwards_include_elevation(client):
    client.places_random(country="US", limit=5, include="elevation")
    assert client._captured[0]["params"]["include"] == "elevation"


# ─────────────────────────────────────────────────────────
# include="other_names,elevation" — composes with the
# existing convenience. Server parses both.
# ─────────────────────────────────────────────────────────

def test_places_composes_other_names_and_elevation(client):
    client.places(query="cafe", country="US", include="other_names,elevation")
    assert client._captured[0]["params"]["include"] == "other_names,elevation"


def test_places_explicit_include_overrides_other_names_bool(client):
    # The existing convention: an explicit include= overrides the
    # include_other_names=True bool. Same when include adds elevation.
    client.places(query="cafe", country="US",
                  include_other_names=True,
                  include="other_names,elevation")
    assert client._captured[0]["params"]["include"] == "other_names,elevation"


# ─────────────────────────────────────────────────────────
# Default behaviour — no include kwarg means no include param.
# Lock this so a future "always include elevation" regression
# can't quietly add cost to every Places call.
# ─────────────────────────────────────────────────────────

def test_places_default_omits_include_param(client):
    client.places(query="cafe", country="US")
    assert "include" not in client._captured[0]["params"]


def test_places_nearby_default_omits_include_param(client):
    client.places_nearby(38.8977, -77.0365, radius_m=300)
    assert "include" not in client._captured[0]["params"]
