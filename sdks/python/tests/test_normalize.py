"""/normalize SDK <-> API wire contract (no network).

The normalization rules are tested in overture-geocoder/api/internal/usps; here we lock
what the SDK sends. Pattern mirrors tests/test_places_elevation.py.
"""

import pytest
from csv2geo import Client
from csv2geo.exceptions import InvalidRequestError


@pytest.fixture
def client():
    c = Client(api_key="dummy_key_for_unit_test")
    c._captured = []

    def fake_request(method, path, params=None, json=None, **kw):
        c._captured.append({"method": method, "path": path, "params": params, "json": json})
        return {"results": [], "meta": {"version": "1.0.0"}}

    c._request = fake_request
    yield c
    c.close()


def test_normalize_string_sends_q(client):
    client.normalize("123 Stewart Street Northwest, Huntsville AL 35801")
    cap = client._captured[0]
    assert (cap["method"], cap["path"]) == ("GET", "/normalize")
    assert cap["params"] == {"q": "123 Stewart Street Northwest, Huntsville AL 35801"}


def test_normalize_dict_forwards_fields(client):
    client.normalize({"address": "9 Elm Ave", "city": "Huntsville", "state": "AL", "zip": "35801"})
    assert client._captured[0]["params"] == {"address": "9 Elm Ave", "city": "Huntsville", "state": "AL", "zip": "35801"}


def test_normalize_batch_posts_addresses(client):
    rows = ["1 Oak St", {"id": "r2", "address": "2 Pine Rd", "zip": "35801"}]
    client.normalize_batch(rows)
    cap = client._captured[0]
    assert (cap["method"], cap["path"]) == ("POST", "/normalize")
    assert cap["json"] == {"addresses": rows}


def test_normalize_batch_limits(client):
    with pytest.raises(InvalidRequestError):
        client.normalize_batch([])
    with pytest.raises(InvalidRequestError):
        client.normalize_batch(["a"] * 1001)
    assert client._captured == []
    client.normalize_batch(["a"] * 1000)
    assert len(client._captured) == 1


def test_parse_batch_limit_is_1000(client):
    with pytest.raises(InvalidRequestError):
        client.parse_batch(["a"] * 1001)
    assert client._captured == []
