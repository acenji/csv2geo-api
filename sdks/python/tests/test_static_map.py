"""Unit tests for the static map URL builder (Sprint 3.1).

These do NOT hit the network. static_map_url() builds a URL string with
real translation logic — marker/path normalization, lat,lng wire format,
viewport selection — so the logic is locked here.
"""

from urllib.parse import urlparse, parse_qs

import pytest
from csv2geo import Client


def _client():
    return Client(api_key="geo_live_unit_test_key")


def _query(url):
    """Parsed query of a static map URL, with values already URL-decoded."""
    parsed = urlparse(url)
    assert parsed.path.endswith("/staticmap")
    return {k: v[0] for k, v in parse_qs(parsed.query).items()}


def test_basic_center_zoom_url():
    q = _query(_client().static_map_url((40.5, -73.5), 12))
    assert q["center"] == "40.5,-73.5"
    assert q["zoom"] == "12"
    assert q["style"] == "csv2geo-bright"
    assert q["api_key"] == "geo_live_unit_test_key"


def test_defaults_are_applied():
    q = _query(_client().static_map_url((0, 0), 3))
    assert q["width"] == "600"
    assert q["height"] == "400"
    assert q["format"] == "png"
    assert q["scale"] == "1"


def test_size_format_scale_passthrough():
    q = _query(_client().static_map_url(
        (1, 2), 5, width=800, height=300, fmt="webp", scale=2,
    ))
    assert q["width"] == "800"
    assert q["height"] == "300"
    assert q["format"] == "webp"
    assert q["scale"] == "2"


def test_marker_tuple_becomes_lat_lng_color():
    q = _query(_client().static_map_url(
        (40.5, -73.5), 12, markers=[(40.5, -73.5, "green")],
    ))
    assert q["markers"] == "40.5,-73.5,green"


def test_multiple_markers_joined_with_pipe():
    q = _query(_client().static_map_url(
        (37, -100), 4, markers=[(40.5, -73.5), (34.05, -118.2, "blue")],
    ))
    assert q["markers"] == "40.5,-73.5|34.05,-118.2,blue"


def test_marker_string_passthrough():
    q = _query(_client().static_map_url(
        (1, 2), 5, markers=["40.5,-73.5,red"],
    ))
    assert q["markers"] == "40.5,-73.5,red"


def test_path_dict_becomes_wire_form():
    q = _query(_client().static_map_url(
        (40.5, -73.5), 12,
        path={"color": "ff0000", "width": 6,
              "points": [(40.5, -73.5), (40.6, -73.6)]},
    ))
    assert q["path"] == "color:ff0000|width:6|40.5,-73.5|40.6,-73.6"


def test_path_string_passthrough():
    q = _query(_client().static_map_url(
        (1, 2), 5, path="width:3|1,2|3,4",
    ))
    assert q["path"] == "width:3|1,2|3,4"


def test_auto_fit_omits_center_and_zoom():
    q = _query(_client().static_map_url(markers=[(40.5, -73.5), (34.05, -118.2)]))
    assert "center" not in q
    assert "zoom" not in q
    assert q["markers"] == "40.5,-73.5|34.05,-118.2"


@pytest.mark.parametrize("kwargs", [
    {"style": "satellite"},
    {"fmt": "gif"},
    {"scale": 3},
])
def test_invalid_options_raise(kwargs):
    with pytest.raises(ValueError):
        _client().static_map_url((1, 2), 5, **kwargs)


def test_bad_center_raises():
    with pytest.raises(ValueError):
        _client().static_map_url((1, 2, 3), 5)


def test_bad_marker_raises():
    with pytest.raises(ValueError):
        _client().static_map_url((1, 2), 5, markers=[(1,)])


def test_path_needs_two_points():
    with pytest.raises(ValueError):
        _client().static_map_url((1, 2), 5, path={"points": [(1, 2)]})
