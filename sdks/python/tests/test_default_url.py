"""URL-lock unit tests.

These tests do NOT hit the network. They guard the single class of bug
that broke the v1.1.x SDK: the default base URL pointing at the internal
Go service (api.csv2geo.com/v1) instead of the customer-facing Laravel
proxy (csv2geo.com/api/v1). A geo_live_* key never validates against
the internal service, so a bad default would 401 every customer install.

Locking the value here means any future change to the constant fails
CI before it can ship to PyPI.
"""

import re
import requests
from csv2geo import Client
from csv2geo.client import Client as ClientCls


CUSTOMER_BASE_URL = "https://csv2geo.com/api/v1"


def test_default_base_url_is_customer_facing():
    """The hardcoded default MUST be the Laravel proxy, not the Go service."""
    assert ClientCls.DEFAULT_BASE_URL == CUSTOMER_BASE_URL, (
        f"DEFAULT_BASE_URL drifted to {ClientCls.DEFAULT_BASE_URL!r} — "
        f"customer keys (geo_live_*) only validate against {CUSTOMER_BASE_URL}. "
        f"If you genuinely meant to point at the internal Go service, "
        f"set base_url=... when constructing Client, do not change the default."
    )


def test_client_instance_inherits_default():
    """A Client built without overrides ends up on the customer URL."""
    c = Client(api_key="dummy_key_for_unit_test")
    assert c.base_url == CUSTOMER_BASE_URL
    c.close()


def test_explicit_base_url_override_still_works():
    """A user pointing at their own gateway / proxy stays in control."""
    c = Client(api_key="dummy", base_url="https://my-proxy.example.com/v1")
    assert c.base_url == "https://my-proxy.example.com/v1"
    c.close()


def test_base_url_trailing_slash_normalized():
    """Trailing slash on user-supplied base_url should not produce //v1."""
    c = Client(api_key="dummy", base_url="https://example.com/v1/")
    assert c.base_url == "https://example.com/v1"
    c.close()


def test_user_agent_matches_package_version():
    """Drift between session UA and pyproject.toml hides reporting bugs."""
    import csv2geo
    c = Client(api_key="dummy")
    ua = c._session.headers.get("User-Agent", "")
    # Format: "csv2geo-python/<semver>"
    m = re.match(r"^csv2geo-python/(\d+\.\d+\.\d+)$", ua)
    assert m, f"User-Agent malformed: {ua!r}"
    assert m.group(1) == csv2geo.__version__, (
        f"User-Agent version {m.group(1)!r} does not match "
        f"csv2geo.__version__ {csv2geo.__version__!r}"
    )
    c.close()
