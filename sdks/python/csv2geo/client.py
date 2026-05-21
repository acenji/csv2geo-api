"""CSV2GEO API Client."""

import time
from typing import List, Optional, Union, Tuple
import requests

from .models import GeocodeResult, GeocodeResponse, BatchGeocodeResponse, Location
from .exceptions import (
    CSV2GEOError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    PermissionError,
    APIError,
)

# Pull the version from package metadata so the User-Agent never drifts
# behind a version bump. Caught 2026-05-13 in CI: the previous code hard-coded
# 'csv2geo-python/1.4.0' and stayed that way through 1.5.0/1.6.0/1.7.x/1.8.0
# releases. Same drift the Node SDK had — fixed in lockstep. Uses
# importlib.metadata (not `from . import __version__`) to avoid the circular
# import that breaks the package's normal init order.
try:
    from importlib.metadata import version as _pkg_version
    _SDK_VERSION = _pkg_version("csv2geo")
except Exception:
    # Fallback for source-tree-only checkouts where the package isn't installed.
    _SDK_VERSION = "0.0.0+source"
_USER_AGENT = f"csv2geo-python/{_SDK_VERSION}"


class Client:
    """
    CSV2GEO API Client.

    Usage:
        client = Client("your_api_key")

        # Forward geocoding
        result = client.geocode("1600 Pennsylvania Ave, Washington DC")
        print(result.lat, result.lng)

        # Reverse geocoding
        result = client.reverse(38.8977, -77.0365)
        print(result.formatted_address)

        # Batch geocoding
        results = client.geocode_batch([
            "1600 Pennsylvania Ave, Washington DC",
            "350 Fifth Avenue, New York, NY",
        ])
        for r in results:
            print(r.best.formatted_address if r.best else "Not found")
    """

    # Customer-facing base URL — the Laravel proxy at csv2geo.com/api/v1 is
    # what accepts geo_live_* keys. (api.csv2geo.com/v1 is the internal Go
    # service and only honors internal keys.)
    DEFAULT_BASE_URL = "https://csv2geo.com/api/v1"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        timeout: int = None,
        auto_retry: bool = True,
    ):
        """
        Initialize the CSV2GEO client.

        Args:
            api_key: Your CSV2GEO API key
            base_url: API base URL (default: https://csv2geo.com/api/v1)
            timeout: Request timeout in seconds (default: 30)
            auto_retry: Automatically retry on rate limit (default: True)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.auto_retry = auto_retry

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/json",
        })

        # Rate limit tracking
        self.rate_limit = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def _handle_response(self, response: requests.Response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        # Update rate limit info from headers
        self.rate_limit = response.headers.get("X-RateLimit-Limit")
        self.rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
        self.rate_limit_reset = response.headers.get("X-RateLimit-Reset")

        # Any 2xx is success. Async endpoints like /v1/batch return 202
        # (Accepted) on create + while polling pending/running; the
        # response body is still JSON we want to surface to the caller.
        if 200 <= response.status_code < 300:
            return response.json()

        # Handle errors
        try:
            error_data = response.json().get("error", {})
            code = error_data.get("code", "unknown")
            message = error_data.get("message", "Unknown error")
            status = error_data.get("status", response.status_code)
        except (ValueError, KeyError):
            code = "unknown"
            message = response.text or "Unknown error"
            status = response.status_code

        if response.status_code == 401:
            raise AuthenticationError(message, code=code, status=status)
        elif response.status_code == 403:
            raise PermissionError(message, code=code, status=status)
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(
                message, code=code, status=status, retry_after=retry_after
            )
        elif response.status_code == 400:
            raise InvalidRequestError(message, code=code, status=status)
        else:
            raise APIError(message, code=code, status=status)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        json: dict = None,
        retry_count: int = 0,
    ) -> dict:
        """Make an API request with retry logic."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
            )
            return self._handle_response(response)

        except RateLimitError as e:
            if self.auto_retry and retry_count < self.MAX_RETRIES:
                wait_time = min(e.retry_after or self.RETRY_DELAY, 60)
                time.sleep(wait_time)
                return self._request(
                    method, endpoint, params, json, retry_count + 1
                )
            raise

        except requests.exceptions.Timeout:
            raise APIError("Request timed out", code="timeout")
        except requests.exceptions.ConnectionError:
            raise APIError("Connection failed", code="connection_error")

    def geocode(
        self,
        address: str,
        country: str = None,
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> Optional[GeocodeResult]:
        """
        Geocode a single address.

        Args:
            address: The address to geocode
            country: Limit results to a specific country (ISO 3166-1 alpha-2)
            lang: BCP-47 tag (e.g. "de", "ja", "zh-Hant"). When set, embedded
                admin-level names (city, state, country, district) come back
                in the requested language. Street + house_number stay in
                source language because Overture has no address-level
                translation data. Sprint 2.1c.
            include_other_names: When True, attach a per-admin-level
                translation map under `result.other_names`:
                `{"country": {"en": ..., "de": ..., ...}, "region": {...}, "locality": {...}}`.
                Composes with `lang`. Sprint 2.1d.
            include: Comma-separated raw `?include=` value. Overrides the
                convenience flag. Use this when you want multiple includes
                (e.g. "meta,other_names").

        Returns:
            GeocodeResult or None if not found

        Example:
            result = client.geocode("1010 Vienna", country="AT", lang="de", include_other_names=True)
            # result.components.country == "Österreich"
            # result.other_names["country"]["fr"] == "Autriche"
        """
        params = {"q": address}
        if country:
            params["country"] = country
        self._merge_places_i18n(params, lang, include_other_names, include)

        data = self._request("GET", "/geocode", params=params)
        response = GeocodeResponse.from_dict(data)
        return response.best

    def geocode_full(
        self,
        address: str,
        country: str = None,
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> GeocodeResponse:
        """
        Geocode a single address and return full response with all results.

        Args:
            address: The address to geocode
            country: Limit results to a specific country (ISO 3166-1 alpha-2)
            lang: BCP-47 tag for translated admin-level names. See geocode().
            include_other_names: Attach per-admin-level translation maps. See geocode().
            include: Comma-separated raw `?include=` value (e.g. "meta,other_names").

        Returns:
            GeocodeResponse with all matching results
        """
        params = {"q": address}
        if country:
            params["country"] = country
        self._merge_places_i18n(params, lang, include_other_names, include)

        data = self._request("GET", "/geocode", params=params)
        return GeocodeResponse.from_dict(data)

    def reverse(
        self,
        lat: float,
        lng: float,
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> Optional[GeocodeResult]:
        """
        Reverse geocode coordinates to an address.

        Args:
            lat: Latitude
            lng: Longitude
            lang: BCP-47 tag for translated admin-level names. See geocode().
            include_other_names: Attach per-admin-level translation maps. See geocode().
            include: Comma-separated raw `?include=` value.

        Returns:
            GeocodeResult or None if not found

        Example:
            result = client.reverse(48.2082, 16.3738, lang="de", include_other_names=True)
            # result.other_names["country"]["en"] == "Austria"
        """
        params = {"lat": lat, "lng": lng}
        self._merge_places_i18n(params, lang, include_other_names, include)
        data = self._request("GET", "/reverse", params=params)
        response = GeocodeResponse.from_dict(data)
        return response.best

    def reverse_full(
        self,
        lat: float,
        lng: float,
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> GeocodeResponse:
        """
        Reverse geocode coordinates and return full response.

        Args:
            lat: Latitude
            lng: Longitude
            lang: BCP-47 tag for translated admin-level names.
            include_other_names: Attach per-admin-level translation maps. See geocode().
            include: Comma-separated raw `?include=` value.

        Returns:
            GeocodeResponse with all matching results
        """
        params = {"lat": lat, "lng": lng}
        self._merge_places_i18n(params, lang, include_other_names, include)
        data = self._request("GET", "/reverse", params=params)
        return GeocodeResponse.from_dict(data)

    def geocode_batch(
        self,
        addresses: List[str],
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> List[GeocodeResponse]:
        """
        Geocode multiple addresses in a single request.

        Args:
            addresses: List of addresses to geocode (max 10,000)
            lang: BCP-47 tag — applied to every result in the batch.

        Returns:
            List of GeocodeResponse objects

        Example:
            results = client.geocode_batch(
                ["1600 Pennsylvania Ave NW, Washington DC", "Champs-Élysées Paris"],
                lang="de",
            )
        """
        if len(addresses) > 10000:
            raise InvalidRequestError("Maximum 10,000 addresses per batch request")

        params = {}
        self._merge_places_i18n(params, lang, include_other_names, include)
        data = self._request("POST", "/geocode", params=params, json={"addresses": addresses})
        response = BatchGeocodeResponse.from_dict(data)
        return response.results

    def reverse_batch(
        self,
        coordinates: List[Union[Tuple[float, float], Location, dict]],
        lang: str = None,
        include_other_names: bool = False,
        include: str = None,
    ) -> List[GeocodeResponse]:
        """
        Reverse geocode multiple coordinates in a single request.

        Args:
            coordinates: List of coordinates as (lat, lng) tuples, Location objects,
                        or dicts with 'lat' and 'lng' keys (max 10,000)

        Returns:
            List of GeocodeResponse objects

        Example:
            results = client.reverse_batch([
                (38.8977, -77.0365),
                (40.7484, -73.9857),
            ])
            for r in results:
                if r.best:
                    print(r.best.formatted_address)
        """
        if len(coordinates) > 10000:
            raise InvalidRequestError("Maximum 10,000 coordinates per batch request")

        # Normalize coordinates to dict format
        coords_list = []
        for coord in coordinates:
            if isinstance(coord, tuple):
                coords_list.append({"lat": coord[0], "lng": coord[1]})
            elif isinstance(coord, Location):
                coords_list.append(coord.to_dict())
            elif isinstance(coord, dict):
                coords_list.append(coord)
            else:
                raise InvalidRequestError(
                    f"Invalid coordinate format: {type(coord)}"
                )

        params = {}
        self._merge_places_i18n(params, lang, include_other_names, include)
        data = self._request("POST", "/reverse", params=params, json={"coordinates": coords_list})
        response = BatchGeocodeResponse.from_dict(data)
        return response.results

    # ─────────────────────────────────────────────────────────
    # Address Tools
    # ─────────────────────────────────────────────────────────

    def validate(self, address: str, country: str = None) -> dict:
        """Validate an address. GET /validate"""
        params = {"q": address}
        if country: params["country"] = country
        return self._request("GET", "/validate", params=params)

    def validate_batch(self, addresses: List[str]) -> dict:
        """Validate up to 10,000 addresses. POST /validate"""
        if len(addresses) > 10000:
            raise InvalidRequestError("Max 10,000 per batch")
        return self._request("POST", "/validate", json={"addresses": addresses})

    def autocomplete(self, query: str, country: str = None, limit: int = None) -> dict:
        """Address autocomplete suggestions. GET /autocomplete"""
        params = {"q": query}
        if country: params["country"] = country
        if limit:   params["limit"] = limit
        return self._request("GET", "/autocomplete", params=params)

    def parse(self, address: str) -> dict:
        """Parse a free-form address into components. GET /parse"""
        return self._request("GET", "/parse", params={"q": address})

    def parse_batch(self, addresses: List[str]) -> dict:
        """Parse up to 10,000 addresses. POST /parse"""
        if len(addresses) > 10000:
            raise InvalidRequestError("Max 10,000 per batch")
        return self._request("POST", "/parse", json={"addresses": addresses})

    def standardize(self, address: str) -> dict:
        """Return a canonical / standardized form of the address. GET /standardize"""
        return self._request("GET", "/standardize", params={"q": address})

    def compare_addresses(self, address1: str, address2: str) -> dict:
        """Score similarity between two addresses. GET /addresses/compare"""
        return self._request("GET", "/addresses/compare", params={"a": address1, "b": address2})

    # ─────────────────────────────────────────────────────────
    # Address inspection
    # ─────────────────────────────────────────────────────────

    def addresses_nearby(self, lat: float, lng: float, radius_m: int = 200, limit: int = None) -> dict:
        """Find addresses within radius of a coordinate. GET /addresses/nearby"""
        params = {"lat": lat, "lng": lng, "radius": radius_m}
        if limit: params["limit"] = limit
        return self._request("GET", "/addresses/nearby", params=params)

    def addresses_street(self, country: str, city: str, street: str) -> dict:
        """Get all addresses on a street. GET /addresses/street"""
        return self._request("GET", "/addresses/street",
                             params={"country": country, "city": city, "street": street})

    def addresses_stats(self, country: str = None) -> dict:
        """Address counts (per country if specified). GET /addresses/stats"""
        params = {}
        if country: params["country"] = country
        return self._request("GET", "/addresses/stats", params=params)

    def addresses_random(self, country: str = None, limit: int = 1) -> dict:
        """Random sample of addresses. GET /addresses/random"""
        params = {"limit": limit}
        if country: params["country"] = country
        return self._request("GET", "/addresses/random", params=params)

    def addresses_interpolate(self, query: str, country: str = "US") -> dict:
        """Interpolate a coordinate from address-range data. GET /addresses/interpolate

        The Go service takes a single free-form `q` (parsed internally)
        plus optional `country`. SDK 1.6.0 fixed the previous
        signature which sent (country, city, street, house_number) — those
        params were silently ignored by Go.
        """
        return self._request("GET", "/addresses/interpolate", params={"q": query, "country": country})

    def addresses_crossstreet(self, lat: float, lng: float, radius: int = 100,
                              country: str = None, city: str = None) -> dict:
        """Find the cross-street nearest to a coordinate. GET /addresses/crossstreet

        The Go service takes (lat, lng) and finds the nearest intersecting
        streets. SDK 1.6.0 fixed the previous signature which sent
        (country, city, street_a, street_b) — wrong shape entirely.
        """
        params = {"lat": lat, "lng": lng, "radius": radius}
        if country: params["country"] = country
        if city:    params["city"]    = city
        return self._request("GET", "/addresses/crossstreet", params=params)

    # ─────────────────────────────────────────────────────────
    # Places
    # ─────────────────────────────────────────────────────────

    def places(self, query: str = None, country: str = None, category: str = None,
               limit: int = None, lang: str = None, include_other_names: bool = False,
               include: str = None) -> dict:
        """Search places (POIs) by name / category. GET /places

        Args:
            lang: BCP-47 tag (e.g. 'ja', 'de', 'pt-BR') — swaps `name` for the
                Overture translation when available (Sprint 2.1b).
            include_other_names: attach the full translation map under
                `other_names` on each result.
            include: comma list — e.g. 'other_names'. Overrides include_other_names.
        """
        params = {}
        if query:    params["q"] = query
        if country:  params["country"] = country
        if category: params["category"] = category
        if limit:    params["limit"] = limit
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", "/places", params=params)

    def places_nearby(self, lat: float, lng: float, radius_m: int = 200,
                      category: str = None, limit: int = None,
                      lang: str = None, include_other_names: bool = False,
                      include: str = None) -> dict:
        """Places within radius of a coordinate. GET /places/nearby"""
        params = {"lat": lat, "lng": lng, "radius": radius_m}
        if category: params["category"] = category
        if limit:    params["limit"] = limit
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", "/places/nearby", params=params)

    def places_categories(self) -> dict:
        """List all place categories. GET /places/categories"""
        return self._request("GET", "/places/categories")

    def places_random(self, country: str = None, category: str = None, limit: int = 1,
                      lang: str = None, include_other_names: bool = False,
                      include: str = None) -> dict:
        """Random places. GET /places/random"""
        params = {"limit": limit}
        if country:  params["country"] = country
        if category: params["category"] = category
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", "/places/random", params=params)

    def places_stats(self, country: str = None) -> dict:
        """Places counts. GET /places/stats"""
        params = {}
        if country: params["country"] = country
        return self._request("GET", "/places/stats", params=params)

    def places_brands(self, country: str = None) -> dict:
        """List brand-tagged places. GET /places/brands"""
        params = {}
        if country: params["country"] = country
        return self._request("GET", "/places/brands", params=params)

    def places_chain(self, brand: str, country: str = None,
                     lang: str = None, include_other_names: bool = False,
                     include: str = None) -> dict:
        """All locations of a brand/chain. GET /places/chain"""
        params = {"brand": brand}
        if country: params["country"] = country
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", "/places/chain", params=params)

    def places_count(self, country: str = None, category: str = None) -> dict:
        """Count places matching filter. GET /places/count"""
        params = {}
        if country:  params["country"] = country
        if category: params["category"] = category
        return self._request("GET", "/places/count", params=params)

    def places_similar(self, place_id: str, limit: int = None,
                       lang: str = None, include_other_names: bool = False,
                       include: str = None) -> dict:
        """Places similar to a given one. GET /places/similar"""
        params = {"id": place_id}
        if limit: params["limit"] = limit
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", "/places/similar", params=params)

    def places_batch(self, coordinates: List[Union[Tuple[float, float], dict]],
                     radius_m: int = 200, category: str = None,
                     lang: str = None, include_other_names: bool = False,
                     include: str = None) -> dict:
        """Batch nearby-places lookup. POST /places/batch"""
        if len(coordinates) > 10000:
            raise InvalidRequestError("Max 10,000 per batch")
        coords = [
            {"lat": c[0], "lng": c[1]} if isinstance(c, tuple) else c
            for c in coordinates
        ]
        body = {"coordinates": coords, "radius": radius_m}
        if category: body["category"] = category
        # lang / include go on the query string (not body) per Go handler contract
        params = {}
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("POST", "/places/batch", params=params, json=body)

    def place_by_id(self, place_id: str, lang: str = None,
                    include_other_names: bool = False, include: str = None) -> dict:
        """Single place by id. GET /places/by-id/{id} (customer URL).

        The customer-facing Laravel proxy nests this under `/places/by-id/{id}`
        even though the underlying Go service uses `/places/{id}` — SDK MUST
        target the customer path. (Bug fix 1.5.1; was broken in 1.5.0 and
        earlier.)
        """
        params = {}
        self._merge_places_i18n(params, lang, include_other_names, include)
        return self._request("GET", f"/places/by-id/{place_id}", params=params)

    def _merge_places_i18n(self, params: dict, lang, include_other_names, include) -> None:
        """Internal: attach Sprint 2.1b lang / include params to a places request."""
        if lang:
            params["lang"] = lang
        if include:
            params["include"] = include
        elif include_other_names:
            params["include"] = "other_names"

    # ─────────────────────────────────────────────────────────
    # Divisions (Sprint 1 — postcode boundary)
    # ─────────────────────────────────────────────────────────

    def divisions_search(self, query: str = None, country: str = None,
                         subtype: str = None, limit: int = None) -> dict:
        """Search administrative divisions. GET /divisions"""
        params = {}
        if query:   params["q"] = query
        if country: params["country"] = country
        if subtype: params["subtype"] = subtype
        if limit:   params["limit"] = limit
        return self._request("GET", "/divisions", params=params)

    def divisions_contains(self, lat: float, lng: float) -> dict:
        """Point-in-polygon: divisions containing a point. GET /divisions/contains"""
        return self._request("GET", "/divisions/contains", params={"lat": lat, "lng": lng})

    def divisions_by_postcode(self, code: str, country: str,
                              include: str = None, precision: str = None,
                              lang: str = None) -> dict:
        """
        Postcode → boundary (bbox + optional polygon + population + wikidata).
        GET /divisions/by-postcode

        Args:
            code: Postcode in any common format (e.g. "90210", "SW1A 1AA")
            country: ISO 3166-1 alpha-2 code
            include: Comma list — `geometry`, `meta`, `other_names`
                (Sprint 2.1 — attaches Overture name translations).
            precision: "low" (default-ish), "med", or "full"
            lang: BCP-47 language tag — replaces `name` with the localized
                Overture translation when available (Sprint 2.1).

        Example:
            r = client.divisions_by_postcode("90210", "US", include="geometry")
            print(r["result"]["population"], r["result"]["bbox"])
            r = client.divisions_by_postcode("SW1A 1AA", "GB", lang="ja")
            print(r["result"]["name"])  # "ロンドン" instead of "London"
        """
        params = {"code": code, "country": country}
        if include:   params["include"] = include
        if precision: params["precision"] = precision
        if lang:      params["lang"] = lang
        return self._request("GET", "/divisions/by-postcode", params=params)

    def divisions_subtypes(self) -> dict:
        """List available division subtypes. GET /divisions/subtypes"""
        return self._request("GET", "/divisions/subtypes")

    def divisions_countries(self) -> dict:
        """List countries with division coverage. GET /divisions/countries"""
        return self._request("GET", "/divisions/countries")

    def divisions_stats(self, country: str = None) -> dict:
        """Division counts. GET /divisions/stats"""
        params = {}
        if country: params["country"] = country
        return self._request("GET", "/divisions/stats", params=params)

    def divisions_random(self, country: str = None, subtype: str = None, limit: int = 1) -> dict:
        """Random divisions. GET /divisions/random"""
        params = {"limit": limit}
        if country: params["country"] = country
        if subtype: params["subtype"] = subtype
        return self._request("GET", "/divisions/random", params=params)

    def division_hierarchy(self, division_id: str) -> dict:
        """
        Children of a division (immediate sub-divisions).
        GET /divisions/hierarchy/{id}

        Note: this returns CHILDREN. For the walk-UP "part-of" chain
        (input → parent → root) use ``division_ancestors()`` instead. Kept
        under the original name for backward compatibility.
        """
        return self._request("GET", f"/divisions/hierarchy/{division_id}")

    def division_by_id(self, division_id: str, lang: str = None,
                       include: str = None, precision: str = None) -> dict:
        """Single division by id. GET /divisions/by-id/{id} (customer URL).

        Customer Laravel proxy nests this under /by-id/{id} — same naming
        pattern as /places/by-id/{id} (matches the customer URL truth, not
        the Go-internal flatter /divisions/{id} path). SDK 1.6.0 corrected
        this; was 404'ing in 1.5.x.
        """
        params = {}
        if lang:      params["lang"] = lang
        if include:   params["include"] = include
        if precision: params["precision"] = precision
        return self._request("GET", f"/divisions/by-id/{division_id}", params=params)

    # ─────────────────────────────────────────────────────────
    # Boundaries (Sprint 1.8 — ancestors / children / consolidated)
    # ─────────────────────────────────────────────────────────

    def division_ancestors(
        self,
        division_id: str,
        include: str = None,
        precision: str = None,
        max_depth: int = None,
        lang: str = None,
    ) -> dict:
        """
        Walk-up "part-of" chain: input division → parent → grandparent → root.

        GET /divisions/ancestors/{id}

        Args:
            division_id: Overture ID of the leaf division.
            include: ``"geometry"`` to include each level's polygon.
            precision: ``"low"``, ``"med"`` (default), or ``"full"``. Only meaningful
                when include=geometry.
            max_depth: Hard cap on chain length (default 8, max 12).

        Returns:
            ``{"id": "...", "depth": N, "results": [<DivisionResult>, ...]}``

        Example:
            chain = client.division_ancestors(beverly_hills_id, include="geometry")
            for level in chain["results"]:
                print(level["subtype"], level["name"])
        """
        params = {}
        if include:   params["include"] = include
        if precision: params["precision"] = precision
        if max_depth: params["max_depth"] = max_depth
        if lang:      params["lang"] = lang
        return self._request("GET", f"/divisions/ancestors/{division_id}", params=params)

    def division_children(
        self,
        division_id: str,
        include: str = None,
        precision: str = None,
        subtype: str = None,
        limit: int = None,
        lang: str = None,
    ) -> dict:
        """
        Immediate sub-divisions of a division (clearer-named alias of
        ``division_hierarchy`` plus optional polygon enrichment).

        GET /divisions/children/{id}

        Args:
            division_id: Overture ID of the parent division.
            include: ``"geometry"`` to include each child's polygon.
            precision: ``"low"`` | ``"med"`` (default) | ``"full"``.
            subtype: Filter children by admin subtype (e.g. "county", "locality").
            limit: Max children to return (default 100, max 500).

        Returns:
            ``{"parent_id": "...", "count": N, "results": [<DivisionResult>, ...]}``
        """
        params = {}
        if include:   params["include"] = include
        if precision: params["precision"] = precision
        if subtype:   params["subtype"] = subtype
        if limit:     params["limit"] = limit
        if lang:      params["lang"] = lang
        return self._request("GET", f"/divisions/children/{division_id}", params=params)

    def division_consolidated(
        self,
        division_id: str,
        include: str = None,
        precision: str = None,
        lang: str = None,
    ) -> dict:
        """
        Consolidated entity lookup. Resolves either canonical OR member id —
        e.g. any of NYC's 5 borough ids returns the canonical "New York City"
        record plus all members.

        GET /divisions/consolidated/{id}

        Args:
            division_id: Overture ID of the canonical or any member division.
            include: ``"geometry"`` for the canonical's outline polygon.
            precision: ``"low"`` | ``"med"`` (default) | ``"full"``.

        Returns:
            ``{"canonical": <DivisionResult>, "members": [...],
               "matched_as": "canonical" | "member", "source": "wikidata-p150"}``

        Raises:
            APIError(404) when the id is not part of any consolidated entity.
        """
        params = {}
        if include:   params["include"] = include
        if precision: params["precision"] = precision
        if lang:      params["lang"] = lang
        return self._request("GET", f"/divisions/consolidated/{division_id}", params=params)

    # ─────────────────────────────────────────────────────────
    # IP geolocation (Sprint 2.7)
    #
    # MaxMind GeoLite2 .mmdb lookup with our county overlay.
    # Bundled into every plan (including Free); no separate billing.
    # ─────────────────────────────────────────────────────────

    def ip(self, ip: str) -> dict:
        """
        IP → geolocation. Returns country, region, city, postcode, location,
        timezone, ISP, and (for residential IPs) county + locality + confidence.

        Args:
            ip: IPv4 or IPv6 address (e.g. "8.8.8.8")

        Returns:
            Canonical /v1/ip response dict.

        Example:
            r = client.ip("8.8.8.8")
            print(r["country"]["code"], r.get("county", {}).get("name"), r["confidence"])
        """
        if not ip or not isinstance(ip, str):
            raise InvalidRequestError("ip must be a non-empty string")
        return self._request("GET", "/ip", params={"ip": ip})

    def ip_me(self) -> dict:
        """
        Like ``ip()``, but uses the requester's IP (the one Laravel sees).
        Useful from server contexts where you want "where is the caller".

        Returns:
            Canonical /v1/ip response dict.
        """
        return self._request("GET", "/ip/me")

    def ip_batch(self, ips: List[str]) -> dict:
        """
        Batch IP lookup. Up to 1000 IPs per call.

        Args:
            ips: list of IPs

        Returns:
            ``{"results": [...]}``
        """
        if not isinstance(ips, list) or len(ips) == 0:
            raise InvalidRequestError("ips must be a non-empty list")
        if len(ips) > 1000:
            raise InvalidRequestError("ip_batch supports at most 1000 IPs per call")
        return self._request("POST", "/ip/batch", json={"ips": ips})

    # ─────────────────────────────────────────────────────────
    # Coverage
    # ─────────────────────────────────────────────────────────

    def coverage(self) -> dict:
        """Live tier-by-country coverage matrix. GET /coverage"""
        return self._request("GET", "/coverage")

    def coverage_stats(self) -> dict:
        """Aggregate coverage totals. GET /coverage-stats"""
        return self._request("GET", "/coverage-stats")

    # ─────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────

    def timezone(self, lat: float, lng: float) -> dict:
        """Timezone at a coordinate. GET /timezone"""
        return self._request("GET", "/timezone", params={"lat": lat, "lng": lng})

    def distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
        """Great-circle distance between two coordinates. GET /distance"""
        return self._request("GET", "/distance",
                             params={"lat1": lat1, "lng1": lng1, "lat2": lat2, "lng2": lng2})

    def health(self) -> dict:
        """Service health check. GET /health"""
        return self._request("GET", "/health")

    # ─────────────────────────────────────────────────────────
    # Routing (Sprint 2.4) — Pro and Unlimited plans only.
    # Seven methods proxy to a Valhalla service behind csv2geo.com.
    # Contract spec: docs/sprint-2.4-routing-endpoints.md.
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _format_waypoints(waypoints) -> str:
        """Internal: accept list of (lat,lng) tuples OR a pre-formatted string."""
        if isinstance(waypoints, str):
            return waypoints
        if not isinstance(waypoints, (list, tuple)) or len(waypoints) < 1:
            raise InvalidRequestError("waypoints must be a list of (lat, lng) tuples")
        parts = []
        for i, pt in enumerate(waypoints):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise InvalidRequestError(f"waypoint {i} must be a (lat, lng) tuple")
            parts.append(f"{pt[0]},{pt[1]}")
        return "|".join(parts)

    def route(self, waypoints, mode: str = "drive", lang: str = None,
              units: str = None, avoid: str = None, alternatives: int = None,
              instructions: bool = False, departure_time: str = None,
              truck_height: float = None, truck_weight: float = None,
              truck_length: float = None, truck_width: float = None,
              truck_hazmat: bool = None, costing_options: str = None,
              format: str = None) -> dict:
        """Point-to-point routing. GET /routing.

        Args:
            waypoints: list of (lat, lng) tuples (2-25 points) OR a pre-formatted
                       "lat1,lng1|lat2,lng2" string.
            mode: drive | truck | walk | bike | motorcycle
            lang: ISO 639-1 for turn-by-turn instructions (default en)
            units: "metric" (default) or "imperial"
            avoid: csv of features to skip — "highways,tolls,ferries"
            alternatives: 0-3 alternative routes (default 0)
            instructions: True to include the turn-by-turn step list
            departure_time: ISO 8601 timestamp for time-aware routing
            truck_height/weight/length/width: meters/kg (truck mode only)
            truck_hazmat: True to enable HAZMAT restrictions for truck routing
            costing_options: JSON string of advanced Valhalla costing overrides
            format: "geojson" (default), "polyline", or "both"
        """
        params = {"waypoints": self._format_waypoints(waypoints), "mode": mode}
        for k, v in [("lang", lang), ("units", units), ("avoid", avoid),
                     ("alternatives", alternatives), ("departure_time", departure_time),
                     ("truck_height", truck_height), ("truck_weight", truck_weight),
                     ("truck_length", truck_length), ("truck_width", truck_width),
                     ("costing_options", costing_options), ("format", format)]:
            if v is not None:
                params[k] = v
        if instructions:
            params["instructions"] = "true"
        if truck_hazmat:
            params["truck_hazmat"] = "true"
        return self._request("GET", "/routing", params=params)

    def isoline(self, lat: float, lng: float, mode: str, ranges,
                type: str = "time", denoise: float = None,
                format: str = None) -> dict:
        """Reachability polygon(s). GET /isoline.

        Args:
            lat, lng: origin point
            mode: drive | truck | walk | bike | motorcycle
            ranges: list of ints (seconds for type=time, meters for type=distance),
                    OR a csv string. Max 3 values per request.
            type: "time" (default) or "distance"
            denoise: 0-1 polygon smoothing factor (default 0.5)
            format: "geojson" (default)
        """
        if isinstance(ranges, (list, tuple)):
            ranges_str = ",".join(str(int(r)) for r in ranges)
        else:
            ranges_str = str(ranges)
        params = {"lat": lat, "lng": lng, "mode": mode, "type": type, "ranges": ranges_str}
        if denoise is not None: params["denoise"] = denoise
        if format is not None:  params["format"]  = format
        return self._request("GET", "/isoline", params=params)

    def route_matrix(self, sources, targets, mode: str,
                     units: str = None, include=None,
                     truck_height: float = None, truck_weight: float = None,
                     truck_length: float = None, truck_width: float = None,
                     truck_hazmat: bool = None) -> dict:
        """N×M distance/time matrix. POST /route-matrix.

        Args:
            sources: list of {"lat", "lng"} dicts OR (lat, lng) tuples (1-100)
            targets: same shape (1-100). N×M cap at 10,000 cells.
            mode: drive | truck | walk | bike | motorcycle
            units: "metric" (default) or "imperial"
            include: ["distances", "durations"] (default both)
            truck_*: same as route()
        """
        def _norm(points):
            out = []
            for i, p in enumerate(points):
                if isinstance(p, dict):
                    out.append({"lat": p["lat"], "lng": p.get("lng", p.get("lon"))})
                elif isinstance(p, (list, tuple)) and len(p) == 2:
                    out.append({"lat": p[0], "lng": p[1]})
                else:
                    raise InvalidRequestError(f"point {i} must be a dict or (lat, lng) tuple")
            return out
        body = {"sources": _norm(sources), "targets": _norm(targets), "mode": mode}
        if units:   body["units"] = units
        if include: body["include"] = list(include)
        for k, v in [("truck_height", truck_height), ("truck_weight", truck_weight),
                     ("truck_length", truck_length), ("truck_width", truck_width)]:
            if v is not None: body[k] = v
        if truck_hazmat is not None: body["truck_hazmat"] = bool(truck_hazmat)
        return self._request("POST", "/route-matrix", json=body)

    def map_match(self, trace, mode: str, gps_accuracy_m: float = None,
                  include=None) -> dict:
        """Snap a GPS trace to roads. POST /map-match.

        Args:
            trace: list of dicts (lat, lng, optional time ISO 8601, accuracy_m)
                   OR (lat, lng) tuples. 2-1000 points.
            mode: drive | truck | walk | bike | motorcycle
            gps_accuracy_m: overall noise level if per-point accuracy_m absent
            include: optional extras — "geometry" (default), "instructions", "matched_points"
        """
        norm = []
        for i, p in enumerate(trace):
            if isinstance(p, dict):
                norm.append({k: p[k] for k in ("lat", "lng", "time", "accuracy_m") if k in p})
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                norm.append({"lat": p[0], "lng": p[1]})
            else:
                raise InvalidRequestError(f"trace point {i} must be a dict or (lat, lng) tuple")
        body = {"trace": norm, "mode": mode}
        if gps_accuracy_m is not None: body["gps_accuracy_m"] = gps_accuracy_m
        if include is not None:        body["include"] = list(include)
        return self._request("POST", "/map-match", json=body)

    def optimize_route(self, waypoints, mode: str, roundtrip: bool = False,
                       lang: str = None, units: str = None,
                       format: str = None,
                       truck_height: float = None, truck_weight: float = None,
                       truck_length: float = None, truck_width: float = None,
                       truck_hazmat: bool = None) -> dict:
        """TSP-style stop ordering. GET /optimize_route.

        Args:
            waypoints: 2-20 (lat, lng) tuples — origin first, then stops
            mode: drive | truck | walk | bike | motorcycle
            roundtrip: True to return to origin after last stop
            lang / units / format / truck_*: same as route()
        """
        params = {"waypoints": self._format_waypoints(waypoints), "mode": mode}
        if roundtrip:                  params["roundtrip"] = "true"
        for k, v in [("lang", lang), ("units", units), ("format", format),
                     ("truck_height", truck_height), ("truck_weight", truck_weight),
                     ("truck_length", truck_length), ("truck_width", truck_width)]:
            if v is not None: params[k] = v
        if truck_hazmat: params["truck_hazmat"] = "true"
        return self._request("GET", "/optimize_route", params=params)

    def locate(self, lat: float, lng: float, mode: str = "drive",
               radius_m: int = None) -> dict:
        """Snap a single point to nearest road. GET /locate.

        Args:
            lat, lng: query point
            mode: filter to roads valid for this mode (default drive)
            radius_m: search radius in meters (default 500, max 5000)
        """
        params = {"lat": lat, "lng": lng, "mode": mode}
        if radius_m is not None: params["radius_m"] = radius_m
        return self._request("GET", "/locate", params=params)

    def elevation(self, points, units: str = None, format: str = None) -> dict:
        """Per-point elevation. GET /elevation.

        Args:
            points: list of (lat, lng) tuples (1-500) OR pre-formatted string
            units: "metric" (default — meters) or "imperial" (feet)
            format: "array" (default) or "geojson" (LineString w/ z-coord)
        """
        params = {"points": self._format_waypoints(points)}
        if units is not None:  params["units"]  = units
        if format is not None: params["format"] = format
        return self._request("GET", "/elevation", params=params)

    # ─────────────────────────────────────────────────────────
    # Async batch wrapper (Sprint 2.5)
    # ─────────────────────────────────────────────────────────

    def batch_create(self, api: str, inputs: List[dict], params: dict = None) -> dict:
        """Create an async batch job that fans `inputs` out across a single
        wrapped endpoint.

        Args:
            api: wrapped endpoint, e.g. "/v1/geocode" (accepts "geocode" too)
            inputs: list of {"id": optional_str, "params": {…}} dicts
            params: optional shared params merged into every input

        Returns:
            dict with keys: id, status_url, status, total_inputs, created_at

        Example:
            job = client.batch_create(
                "/v1/geocode",
                inputs=[
                    {"id": "a", "params": {"q": "90210", "country": "US"}},
                    {"id": "b", "params": {"q": "10001", "country": "US"}},
                ],
                params={"limit": "1"},
            )
            done = client.batch_wait(job["id"])
            for r in done["results"]:
                print(r["input_id"], r["status"])
        """
        body = {"api": api, "inputs": inputs}
        if params:
            body["params"] = params
        return self._request("POST", "/batch", json=body)

    def batch_get(self, job_id: str, compat: str = None) -> dict:
        """Poll a batch job. Returns 202-shaped body while pending/running;
        200-shaped body (with `results`) when completed/failed/cancelled.

        Args:
            job_id: id returned by batch_create()
            compat: pass "geoapify" to return the flat-array shape Geoapify's
                    batch endpoint uses (drop-in SDK compatibility).
        """
        params = {}
        if compat:
            params["compat"] = compat
        return self._request("GET", f"/batch/{job_id}", params=params)

    def batch_cancel(self, job_id: str) -> dict:
        """Cancel a pending or running batch job. Returns 404 if the job is
        already in a terminal state."""
        return self._request("DELETE", f"/batch/{job_id}")

    def batch_wait(self, job_id: str, poll_interval: float = 2.0,
                   timeout: float = 600.0) -> dict:
        """Poll batch_get() until the job reaches a terminal state, then
        return the final response. Convenience wrapper around batch_get()
        for callers that don't want to manage a polling loop themselves.

        Raises APIError(code="batch_wait_timeout") if `timeout` elapses
        before the job terminates.
        """
        start = time.time()
        terminal = ("completed", "failed", "cancelled")
        while True:
            result = self.batch_get(job_id)
            if result.get("status") in terminal:
                return result
            if time.time() - start > timeout:
                raise APIError(
                    f"batch_wait timed out after {timeout}s; job is {result.get('status')!r} "
                    f"with {result.get('completed_inputs')}/{result.get('total_inputs')} done",
                    code="batch_wait_timeout",
                )
            time.sleep(poll_interval)

    # ─────────────────────────────────────────────────────────
    # Marker Icon PNG generator (Sprint 2.6)
    # ─────────────────────────────────────────────────────────

    def icon(
        self,
        icon: str,
        color: str = None,
        size: str = "medium",
        type: str = "awesome",
        no_white_circle: bool = False,
        scale_factor: int = 1,
    ) -> bytes:
        """Generate a marker pin PNG. GET /icon.

        Args:
            icon: Icon name from the catalog (call ``icon_catalog()`` to list).
            color: Pin body color, hex string (e.g. ``"#52b74c"`` or ``"52b74c"``).
                   Defaults to red.
            size: ``"small"`` / ``"medium"`` / ``"large"`` / ``"x-large"``.
            type: Icon family. Only ``"awesome"`` is supported in v1.
            no_white_circle: If True, glyph sits directly on the pin body.
            scale_factor: 1, 2, or 4 — retina multiplier.

        Returns:
            Raw PNG bytes — write to a file or stream as-is.

        Example:
            png = client.icon("tree", color="#52b74c", size="x-large", scale_factor=2)
            with open("pin.png", "wb") as f:
                f.write(png)
        """
        params = {
            "icon": icon,
            "size": size,
            "type": type,
            "scaleFactor": scale_factor,
        }
        if color is not None:
            params["color"] = color
        if no_white_circle:
            params["noWhiteCircle"] = "true"

        # icon returns image/png on success — bypass _handle_response so we
        # don't try to JSON-decode binary data.
        response = self._session.get(
            f"{self.base_url}/icon",
            params=params,
            timeout=self.timeout,
        )
        if 200 <= response.status_code < 300:
            return response.content
        # Error path mirrors _handle_response.
        try:
            error_data = response.json().get("error", {})
            code = error_data.get("code", "unknown")
            message = error_data.get("message", "Unknown error")
            status = error_data.get("status", response.status_code)
        except (ValueError, KeyError):
            code = "unknown"
            message = response.text or "Unknown error"
            status = response.status_code
        if response.status_code == 400:
            raise InvalidRequestError(message, code=code, status=status)
        raise APIError(message, code=code, status=status)

    def icon_catalog(self) -> dict:
        """List available icon names. GET /icon/catalog.

        Returns:
            dict with keys ``type``, ``version``, ``count``, ``icons`` (list of names).
        """
        return self._request("GET", "/icon/catalog")

    # ───────────────────────── Vector map tiles ─────────────────────────
    # Sprint 3.0 — vector tile serving. The tile DATA endpoint costs 0.25
    # credits/tile; the style + asset endpoints are free. Note: tiles are
    # VECTOR (Mapbox Vector Tile / .pbf) — there is no retina/@2x variant
    # the way raster tiles have; pixel density is a client-render concern.

    def tile_url(self, z: int, x: int, y: int, source: str = "planet") -> str:
        """Build the URL for a single vector tile. Does NOT make a request.

        Useful for wiring tiles into a non-MapLibre map library (Leaflet
        with a vector plugin, OpenLayers, etc.). For MapLibre GL JS, prefer
        ``style_url()`` — the style document already references tiles.

        Args:
            z, x, y: Tile coordinates (z = zoom 0-14, x/y = column/row).
            source: pmtiles archive name. Only ``"planet"`` is provisioned.

        Returns:
            Absolute tile URL with the api_key query parameter. Fetching it
            costs 0.25 credits per tile.

        Example:
            url = client.tile_url(10, 301, 384)
            # https://csv2geo.com/api/v1/tile/planet/10/301/384.pbf?api_key=...
        """
        for name, val in (("z", z), ("x", x), ("y", y)):
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        return f"{self.base_url}/tile/{source}/{z}/{x}/{y}.pbf?api_key={self.api_key}"

    def style_url(self, name: str = "csv2geo-bright") -> str:
        """Build the URL for a MapLibre style document. Does NOT make a request.

        Hand the returned string straight to MapLibre GL JS:
            ``new maplibregl.Map({ style: client.style_url("dark-matter") })``

        Args:
            name: ``"csv2geo-bright"`` / ``"positron"`` / ``"dark-matter"``.

        Returns:
            Absolute style URL with the api_key query parameter.
        """
        return f"{self.base_url}/tile/styles/{name}.json?api_key={self.api_key}"

    def tile_styles(self) -> dict:
        """List available map styles. GET /tile/styles. Free.

        Returns:
            dict with key ``styles`` — a list of dicts, each with
            ``name``, ``display``, ``description``, ``preview``, ``url``.
        """
        return self._request("GET", "/tile/styles")

    def tile_style(self, name: str = "csv2geo-bright") -> dict:
        """Fetch a full MapLibre style document. GET /tile/styles/{name}.json. Free.

        The returned style has the api_key and customer URL already
        substituted into its tile / sprite / glyph references.

        Args:
            name: ``"csv2geo-bright"`` / ``"positron"`` / ``"dark-matter"``.

        Returns:
            The MapLibre GL style document as a dict.
        """
        return self._request("GET", f"/tile/styles/{name}.json")

    # ───────────────────────── Static maps ──────────────────────────
    # Sprint 3.1 — server-side rendered map images (PNG/JPEG/WebP). A
    # render costs 1 credit. static_map_url() only builds the URL — drop
    # it straight into an <img> tag; static_map() builds the URL and
    # fetches the image bytes.

    STATIC_MAP_STYLES = (
        "csv2geo-bright", "csv2geo-dark", "csv2geo-slate", "maptiler-basic",
        "positron", "fiord-color", "osm-liberty", "toner", "dark-matter",
    )

    @staticmethod
    def _static_map_marker(m) -> str:
        """Normalize one marker to the 'lat,lng[,color]' wire form."""
        if isinstance(m, str):
            return m
        if isinstance(m, (list, tuple)) and len(m) in (2, 3):
            return ",".join(str(x) for x in m)
        raise ValueError(
            "each marker must be 'lat,lng[,color]' or a (lat, lng[, color]) tuple"
        )

    @staticmethod
    def _static_map_path(p) -> str:
        """Normalize a path (string or dict) to the pipe-delimited wire form."""
        if isinstance(p, str):
            return p
        if isinstance(p, dict):
            segs = []
            if p.get("color"):
                segs.append(f"color:{p['color']}")
            if p.get("width"):
                segs.append(f"width:{p['width']}")
            if p.get("fill"):
                segs.append(f"fill:{p['fill']}")
            pts = p.get("points") or []
            if len(pts) < 2:
                raise ValueError("path needs at least 2 points")
            for pt in pts:
                if not (isinstance(pt, (list, tuple)) and len(pt) == 2):
                    raise ValueError("each path point must be a (lat, lng) pair")
                segs.append(f"{pt[0]},{pt[1]}")
            return "|".join(segs)
        raise ValueError("path must be a string or a dict with a 'points' list")

    def static_map_url(self, center=None, zoom=None, *, style="csv2geo-bright",
                       width=600, height=400, fmt="png", scale=1,
                       markers=None, path=None) -> str:
        """Build a static map image URL. Does NOT make a request.

        Drop the returned string straight into an HTML ``<img src>`` —
        each fetch renders the image server-side and costs 1 credit.

        Args:
            center: ``(lat, lng)`` map center. Omit (with ``zoom``) to
                    auto-fit the viewport around the markers/path.
            zoom: Zoom level 0-22. Required when ``center`` is given.
            style: One of ``Client.STATIC_MAP_STYLES`` (9 styles).
            width, height: Image size in pixels (1-1280).
            fmt: ``"png"`` / ``"jpg"`` / ``"webp"``. WebP is ~60% smaller.
            scale: ``1`` standard or ``2`` retina (@2x).
            markers: Iterable of markers, each a ``(lat, lng)`` /
                     ``(lat, lng, color)`` tuple or a ``"lat,lng[,color]"``
                     string. Colors: red, blue, green, orange, purple,
                     black, gray.
            path: A polyline — either a pre-formatted string, or a dict
                  ``{"points": [(lat,lng), ...], "color": "0969da",
                  "width": 4, "fill": "..."}``.

        Returns:
            Absolute static map URL with the api_key query parameter.

        Example:
            url = client.static_map_url(
                (40.7484, -73.9857), 14,
                markers=[(40.7484, -73.9857, "red")],
                fmt="webp",
            )
            # <img src="{url}">
        """
        from urllib.parse import urlencode

        if style not in self.STATIC_MAP_STYLES:
            raise ValueError(
                f"style must be one of: {', '.join(self.STATIC_MAP_STYLES)}"
            )
        if fmt not in ("png", "jpg", "jpeg", "webp"):
            raise ValueError("fmt must be png, jpg or webp")
        if scale not in (1, 2):
            raise ValueError("scale must be 1 or 2")

        params = {
            "style": style,
            "width": width,
            "height": height,
            "format": fmt,
            "scale": scale,
            "api_key": self.api_key,
        }
        if center is not None:
            if not (isinstance(center, (list, tuple)) and len(center) == 2):
                raise ValueError("center must be a (lat, lng) pair")
            params["center"] = f"{center[0]},{center[1]}"
        if zoom is not None:
            params["zoom"] = zoom
        if markers:
            params["markers"] = "|".join(self._static_map_marker(m) for m in markers)
        if path is not None:
            params["path"] = self._static_map_path(path)

        return f"{self.base_url}/staticmap?{urlencode(params)}"

    def static_map(self, center=None, zoom=None, **kwargs) -> bytes:
        """Render a static map and return the raw image bytes. Costs 1 credit.

        Accepts the same arguments as :meth:`static_map_url`. Use this when
        you want to save or process the image; use ``static_map_url()`` when
        you just need a URL to embed.

        Returns:
            Raw image bytes (PNG/JPEG/WebP per ``fmt``).

        Example:
            png = client.static_map((40.7484, -73.9857), 14)
            with open("map.png", "wb") as f:
                f.write(png)
        """
        url = self.static_map_url(center, zoom, **kwargs)
        response = self._session.get(url, timeout=self.timeout)
        if 200 <= response.status_code < 300:
            return response.content
        try:
            error_data = response.json().get("error", {})
            code = error_data.get("code", "unknown")
            message = error_data.get("message", "Unknown error")
            status = error_data.get("status", response.status_code)
        except (ValueError, KeyError):
            code = "unknown"
            message = response.text or "Unknown error"
            status = response.status_code
        if response.status_code == 400:
            raise InvalidRequestError(message, code=code, status=status)
        if response.status_code == 401:
            raise AuthenticationError(message, code=code, status=status)
        raise APIError(message, code=code, status=status)

    # ─────────────────────────────────────────────────────────

    def close(self):
        """Close the client session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
