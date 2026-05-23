"""Sprint reverse-scoring 2026-05-23 — unit tests for the new `radius` kwarg
on reverse(), reverse_full(), and reverse_batch().

Mirror of tests/test_routing.py — monkey-patches Client._request to capture
the params the SDK would forward, then asserts that `radius` is present /
absent / forwarded with the correct value depending on how the SDK is called.
Does NOT hit the network.

Server-side enforcement (clamp to 1500, default 100, malformed → default) is
covered by overture-geocoder's TestParseReverseRadius. These tests cover only
the SDK-side contract: "if the customer passes radius=N, the SDK forwards
radius=N; if they don't, the SDK doesn't forward anything (server applies
default)."
"""

import pytest
from csv2geo import Client


@pytest.fixture
def client():
    """A Client with _request stubbed to capture call params."""
    c = Client(api_key="dummy_key_for_unit_test")
    c._captured = []

    def fake_request(method, path, params=None, json=None, **kw):
        c._captured.append({"method": method, "path": path,
                            "params": params, "json": json})
        # Return a minimal-valid response shape so from_dict() doesn't blow up.
        return {"results": [], "meta": {"version": "1.0.0"}}

    c._request = fake_request
    yield c
    c.close()


# ─────────────────────────────────────────────────────────
# reverse() — single coord, GET
# ─────────────────────────────────────────────────────────

def test_reverse_omits_radius_by_default(client):
    """Customers who don't pass radius get the server default (100m).
    The SDK MUST NOT inject a radius value of its own — that would change
    behaviour silently. Forward only what the customer supplied."""
    client.reverse(38.8977, -77.0365)
    assert len(client._captured) == 1
    assert "radius" not in client._captured[0]["params"]


def test_reverse_forwards_radius_when_set(client):
    client.reverse(46.49125, -120.395, radius=1000)
    assert client._captured[0]["params"]["radius"] == 1000


def test_reverse_forwards_minimum_radius(client):
    client.reverse(38.8977, -77.0365, radius=1)
    assert client._captured[0]["params"]["radius"] == 1


def test_reverse_forwards_radius_at_max(client):
    client.reverse(38.8977, -77.0365, radius=1500)
    assert client._captured[0]["params"]["radius"] == 1500


def test_reverse_forwards_out_of_range_radius_unchanged(client):
    """Server-side clamps to 1500 — SDK should NOT do its own validation
    so that future server changes (e.g. raising the cap) work without
    requiring an SDK bump."""
    client.reverse(38.8977, -77.0365, radius=9999)
    assert client._captured[0]["params"]["radius"] == 9999


# ─────────────────────────────────────────────────────────
# reverse_full() — single coord, GET, returns full response
# ─────────────────────────────────────────────────────────

def test_reverse_full_omits_radius_by_default(client):
    client.reverse_full(38.8977, -77.0365)
    assert "radius" not in client._captured[0]["params"]


def test_reverse_full_forwards_radius_when_set(client):
    client.reverse_full(46.49125, -120.395, radius=500)
    assert client._captured[0]["params"]["radius"] == 500


# ─────────────────────────────────────────────────────────
# reverse_batch() — POST with body
# ─────────────────────────────────────────────────────────

def test_reverse_batch_omits_radius_by_default(client):
    client.reverse_batch([(38.8977, -77.0365), (40.7484, -73.9857)])
    captured = client._captured[0]
    assert captured["method"] == "POST"
    assert captured["path"] == "/reverse"
    assert "radius" not in captured["params"]


def test_reverse_batch_forwards_radius_to_query_string(client):
    """radius is a query-string param even on POST batch, because the
    underlying Go handler reads it from c.Query() not from the body."""
    client.reverse_batch(
        [(38.8977, -77.0365), (40.7484, -73.9857)],
        radius=1000,
    )
    captured = client._captured[0]
    assert captured["params"]["radius"] == 1000
    # Coordinates still go in the JSON body, not in params.
    assert captured["json"] == {
        "coordinates": [
            {"lat": 38.8977, "lng": -77.0365},
            {"lat": 40.7484, "lng": -73.9857},
        ]
    }


def test_reverse_batch_radius_combines_with_lang(client):
    """radius is orthogonal to lang/include — verify they don't trample
    each other when both are passed."""
    client.reverse_batch(
        [(38.8977, -77.0365)],
        lang="de",
        radius=500,
    )
    params = client._captured[0]["params"]
    assert params["radius"] == 500
    assert params.get("lang") == "de"
