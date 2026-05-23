"""Sprint property-image 2026-05-23 — unit tests for the
property_image / property_image_url builders.

No network. Locks the SDK ↔ API contract by asserting on the exact URL
the SDK would emit. Pairs with the Go-side property_image_test.go and
the Laravel proxy tests for end-to-end coverage.
"""

import pytest
from urllib.parse import unquote, urlparse, parse_qs

from csv2geo import Client
from csv2geo.exceptions import InvalidRequestError


@pytest.fixture
def client():
    return Client(api_key="dummy_key_for_unit_test")


# ─────────────────────────────────────────────────────────
# property_image_url — pure URL construction.
# ─────────────────────────────────────────────────────────

class TestPropertyImageURL:

    def test_q_form_emits_q_param(self, client):
        url = client.property_image_url(q="3168 Beckie Dr SW, Wyoming, MI 49418")
        params = parse_qs(urlparse(url).query)
        assert params["q"] == ["3168 Beckie Dr SW, Wyoming, MI 49418"]
        # lat/lng must NOT be in the q-form URL.
        assert "lat" not in params
        assert "lng" not in params

    def test_latlng_form_emits_both(self, client):
        url = client.property_image_url(lat=42.86753, lng=-85.7419)
        params = parse_qs(urlparse(url).query)
        assert params["lat"] == ["42.86753"]
        assert params["lng"] == ["-85.7419"]
        assert "q" not in params

    def test_size_param_forwarded(self, client):
        url = client.property_image_url(lat=42.86753, lng=-85.7419, size=1000)
        assert "size=1000" in url

    def test_size_omitted_when_none(self, client):
        # Server defaults to 350 — SDK MUST NOT inject one of its own so
        # a future server default change doesn't require an SDK bump.
        url = client.property_image_url(lat=42.86753, lng=-85.7419)
        assert "size=" not in url

    def test_format_param_forwarded(self, client):
        url = client.property_image_url(lat=42.86753, lng=-85.7419, fmt="jpg")
        assert "format=jpg" in url

    def test_format_omitted_when_none(self, client):
        url = client.property_image_url(lat=42.86753, lng=-85.7419)
        assert "format=" not in url

    def test_api_key_always_present(self, client):
        url = client.property_image_url(lat=42.86753, lng=-85.7419)
        assert "api_key=dummy_key_for_unit_test" in url

    def test_path_is_property_image(self, client):
        # Customer URL: csv2geo.com/api/v1/property/image — NOT a Go
        # internal path. Lock against the path regressing to /api/v1/icon
        # or similar.
        url = client.property_image_url(lat=42.86753, lng=-85.7419)
        path = urlparse(url).path
        assert path.endswith("/property/image"), f"path = {path}"


# ─────────────────────────────────────────────────────────
# Validation — missing both q and lat+lng.
# ─────────────────────────────────────────────────────────

class TestPropertyImageValidation:

    def test_missing_both_raises_locally(self, client):
        # Local validation — SDK refuses to build a URL the server will
        # 400 on. Saves a round-trip + the missing_query error reads
        # nicer when raised client-side.
        with pytest.raises(InvalidRequestError) as exc:
            client.property_image_url()
        assert "missing_query" in exc.value.code or "missing_query" in str(exc.value)

    def test_only_lat_raises(self, client):
        with pytest.raises(InvalidRequestError):
            client.property_image_url(lat=42.86753)

    def test_only_lng_raises(self, client):
        with pytest.raises(InvalidRequestError):
            client.property_image_url(lng=-85.7419)

    def test_q_alone_ok(self, client):
        # q without lat/lng is fine — server geocodes internally.
        url = client.property_image_url(q="White House, Washington DC")
        assert "q=" in url
