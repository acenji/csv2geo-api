"""Sprint staticmap-pin-labels 2026-05-23 — unit tests for the marker
wire-form builder.

Mirror of `tests/test_reverse_radius.py` — no network, locks the SDK ↔ API
contract by asserting on the exact wire string the SDK would emit. Pairs
with the Go-side handler tests (icon_pin_label_test.go) and the Laravel
proxy tests for end-to-end coverage.

The wire form is what tileserver-gl ultimately parses, so getting the
positional vs keyed decision right matters: a hex color in positional form
would be mis-parsed as a named color.
"""

import pytest
from csv2geo import Client
from csv2geo.client import Client as ClientCls


# ─────────────────────────────────────────────────────────
# _static_map_marker — pure unit tests on the helper.
# ─────────────────────────────────────────────────────────

class TestStaticMapMarkerHelper:

    def test_string_passes_through(self):
        # The customer already wrote the wire form themselves.
        assert ClientCls._static_map_marker("47.6,-122.3,red,7") == "47.6,-122.3,red,7"

    def test_tuple_2_field_lat_lng_only(self):
        assert ClientCls._static_map_marker((47.6, -122.3)) == "47.6,-122.3"

    def test_tuple_3_field_with_color(self):
        assert ClientCls._static_map_marker((47.6, -122.3, "red")) == "47.6,-122.3,red"

    def test_tuple_4_field_with_label(self):
        # Sprint staticmap-pin-labels 2026-05-23 — new shape.
        assert ClientCls._static_map_marker((47.6, -122.3, "red", "7")) == "47.6,-122.3,red,7"

    def test_tuple_too_short(self):
        with pytest.raises(ValueError, match="marker tuple must be"):
            ClientCls._static_map_marker((47.6,))

    def test_tuple_too_long(self):
        with pytest.raises(ValueError, match="marker tuple must be"):
            ClientCls._static_map_marker((47.6, -122.3, "red", "7", "extra"))

    def test_dict_lat_lng_only_uses_positional(self):
        # No label, no hex → cheapest path is positional, matches the
        # tuple form for back-compat with older SDK versions.
        assert ClientCls._static_map_marker({"lat": 47.6, "lng": -122.3}) == "47.6,-122.3"

    def test_dict_with_named_color_positional(self):
        assert ClientCls._static_map_marker(
            {"lat": 47.6, "lng": -122.3, "color": "red"}
        ) == "47.6,-122.3,red"

    def test_dict_with_label_emits_keyed(self):
        # Label is present → MUST emit keyed form, because positional
        # form's label slot is only unambiguous after a color.
        assert ClientCls._static_map_marker(
            {"lat": 47.6, "lng": -122.3, "color": "red", "label": "7"}
        ) == "47.6,-122.3,color:red,label:7"

    def test_dict_with_hex_color_emits_keyed(self):
        # Hex color is illegal in positional form (server parser rejects
        # `#ff8800` as a named palette). MUST emit keyed.
        assert ClientCls._static_map_marker(
            {"lat": 47.6, "lng": -122.3, "color": "#ff8800"}
        ) == "47.6,-122.3,color:#ff8800"

    def test_dict_with_hex_color_and_label(self):
        assert ClientCls._static_map_marker(
            {"lat": 47.6, "lng": -122.3, "color": "#ff8800", "label": "42"}
        ) == "47.6,-122.3,color:#ff8800,label:42"

    def test_dict_with_only_label_no_color(self):
        # No color key → server defaults to red. SDK still emits the
        # label keyed so the server picks up the label slot.
        assert ClientCls._static_map_marker(
            {"lat": 47.6, "lng": -122.3, "label": "7"}
        ) == "47.6,-122.3,label:7"

    def test_dict_missing_lat(self):
        with pytest.raises(ValueError, match="lat.*lng"):
            ClientCls._static_map_marker({"lng": -122.3})

    def test_dict_missing_lng(self):
        with pytest.raises(ValueError, match="lat.*lng"):
            ClientCls._static_map_marker({"lat": 47.6})

    def test_invalid_type_int_raises(self):
        with pytest.raises(ValueError, match="each marker must be"):
            ClientCls._static_map_marker(42)


# ─────────────────────────────────────────────────────────
# static_map_url — end-to-end URL construction.
# ─────────────────────────────────────────────────────────

class TestStaticMapURLBuilder:

    @pytest.fixture
    def client(self):
        return Client(api_key="dummy_key_for_unit_test")

    def test_url_contains_labelled_marker_in_keyed_form(self, client):
        from urllib.parse import unquote
        url = client.static_map_url(
            center=(47.6, -122.3),
            zoom=14,
            markers=[
                {"lat": 47.6062, "lng": -122.3321, "color": "red", "label": "7"},
            ],
        )
        # The wire form must include `color:red,label:7` so the server's
        # keyed-mode parser picks both up. unquote() normalizes whatever
        # encoding the urlencode() implementation chose.
        assert "47.6062,-122.3321,color:red,label:7" in unquote(url)

    def test_url_mixes_labelled_and_unlabelled(self, client):
        from urllib.parse import unquote
        url = client.static_map_url(
            center=(47.6, -122.3),
            zoom=14,
            markers=[
                {"lat": 47.6062, "lng": -122.3321, "color": "red", "label": "1"},
                {"lat": 47.6090, "lng": -122.3360, "color": "blue"},
            ],
        )
        decoded = unquote(url)
        # Pipe-separated on the wire.
        assert "|" in decoded
        # First marker keyed (has label), second positional (no label).
        assert "color:red,label:1" in decoded
        assert "47.609,-122.336,blue" in decoded

    def test_url_no_markers_omits_markers_param(self, client):
        url = client.static_map_url(center=(47.6, -122.3), zoom=14)
        assert "markers=" not in url

    def test_url_hex_color_uses_keyed(self, client):
        from urllib.parse import unquote
        url = client.static_map_url(
            center=(47.6, -122.3),
            zoom=14,
            markers=[
                {"lat": 47.6, "lng": -122.3, "color": "#ff8800", "label": "42"},
            ],
        )
        # urlencode escapes EVERY reserved char ('#' → %23, ':' → %3A,
        # ',' → %2C). Round-tripping via unquote() proves the decoded
        # substring is present without coupling to which chars got
        # escaped by which encoder.
        assert "color:#ff8800,label:42" in unquote(url)
