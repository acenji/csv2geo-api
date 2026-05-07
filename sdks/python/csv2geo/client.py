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
            "User-Agent": "csv2geo-python/1.4.0",
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

        if response.status_code == 200:
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
    ) -> Optional[GeocodeResult]:
        """
        Geocode a single address.

        Args:
            address: The address to geocode
            country: Limit results to a specific country (ISO 3166-1 alpha-2)

        Returns:
            GeocodeResult or None if not found

        Example:
            result = client.geocode("1600 Pennsylvania Ave, Washington DC")
            if result:
                print(f"Lat: {result.lat}, Lng: {result.lng}")
        """
        params = {"q": address}
        if country:
            params["country"] = country

        data = self._request("GET", "/geocode", params=params)
        response = GeocodeResponse.from_dict(data)
        return response.best

    def geocode_full(
        self,
        address: str,
        country: str = None,
    ) -> GeocodeResponse:
        """
        Geocode a single address and return full response with all results.

        Args:
            address: The address to geocode
            country: Limit results to a specific country (ISO 3166-1 alpha-2)

        Returns:
            GeocodeResponse with all matching results
        """
        params = {"q": address}
        if country:
            params["country"] = country

        data = self._request("GET", "/geocode", params=params)
        return GeocodeResponse.from_dict(data)

    def reverse(
        self,
        lat: float,
        lng: float,
    ) -> Optional[GeocodeResult]:
        """
        Reverse geocode coordinates to an address.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            GeocodeResult or None if not found

        Example:
            result = client.reverse(38.8977, -77.0365)
            if result:
                print(result.formatted_address)
        """
        params = {"lat": lat, "lng": lng}
        data = self._request("GET", "/reverse", params=params)
        response = GeocodeResponse.from_dict(data)
        return response.best

    def reverse_full(
        self,
        lat: float,
        lng: float,
    ) -> GeocodeResponse:
        """
        Reverse geocode coordinates and return full response.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            GeocodeResponse with all matching results
        """
        params = {"lat": lat, "lng": lng}
        data = self._request("GET", "/reverse", params=params)
        return GeocodeResponse.from_dict(data)

    def geocode_batch(
        self,
        addresses: List[str],
    ) -> List[GeocodeResponse]:
        """
        Geocode multiple addresses in a single request.

        Args:
            addresses: List of addresses to geocode (max 10,000)

        Returns:
            List of GeocodeResponse objects

        Example:
            results = client.geocode_batch([
                "1600 Pennsylvania Ave, Washington DC",
                "350 Fifth Avenue, New York, NY",
            ])
            for r in results:
                if r.best:
                    print(f"{r.query}: {r.best.lat}, {r.best.lng}")
        """
        if len(addresses) > 10000:
            raise InvalidRequestError("Maximum 10,000 addresses per batch request")

        data = self._request("POST", "/geocode", json={"addresses": addresses})
        response = BatchGeocodeResponse.from_dict(data)
        return response.results

    def reverse_batch(
        self,
        coordinates: List[Union[Tuple[float, float], Location, dict]],
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

        data = self._request("POST", "/reverse", json={"coordinates": coords_list})
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

    def addresses_interpolate(self, country: str, city: str, street: str, house_number: str) -> dict:
        """Interpolate a coordinate from address-range data. GET /addresses/interpolate"""
        return self._request("GET", "/addresses/interpolate", params={
            "country": country, "city": city, "street": street, "house_number": house_number,
        })

    def addresses_crossstreet(self, country: str, city: str, street_a: str, street_b: str) -> dict:
        """Find the intersection of two streets. GET /addresses/crossstreet"""
        return self._request("GET", "/addresses/crossstreet", params={
            "country": country, "city": city, "street_a": street_a, "street_b": street_b,
        })

    # ─────────────────────────────────────────────────────────
    # Places
    # ─────────────────────────────────────────────────────────

    def places(self, query: str = None, country: str = None, category: str = None,
               limit: int = None) -> dict:
        """Search places (POIs) by name / category. GET /places"""
        params = {}
        if query:    params["q"] = query
        if country:  params["country"] = country
        if category: params["category"] = category
        if limit:    params["limit"] = limit
        return self._request("GET", "/places", params=params)

    def places_nearby(self, lat: float, lng: float, radius_m: int = 200,
                      category: str = None, limit: int = None) -> dict:
        """Places within radius of a coordinate. GET /places/nearby"""
        params = {"lat": lat, "lng": lng, "radius": radius_m}
        if category: params["category"] = category
        if limit:    params["limit"] = limit
        return self._request("GET", "/places/nearby", params=params)

    def places_categories(self) -> dict:
        """List all place categories. GET /places/categories"""
        return self._request("GET", "/places/categories")

    def places_random(self, country: str = None, category: str = None, limit: int = 1) -> dict:
        """Random places. GET /places/random"""
        params = {"limit": limit}
        if country:  params["country"] = country
        if category: params["category"] = category
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

    def places_chain(self, brand: str, country: str = None) -> dict:
        """All locations of a brand/chain. GET /places/chain"""
        params = {"brand": brand}
        if country: params["country"] = country
        return self._request("GET", "/places/chain", params=params)

    def places_count(self, country: str = None, category: str = None) -> dict:
        """Count places matching filter. GET /places/count"""
        params = {}
        if country:  params["country"] = country
        if category: params["category"] = category
        return self._request("GET", "/places/count", params=params)

    def places_similar(self, place_id: str, limit: int = None) -> dict:
        """Places similar to a given one. GET /places/similar"""
        params = {"id": place_id}
        if limit: params["limit"] = limit
        return self._request("GET", "/places/similar", params=params)

    def places_batch(self, coordinates: List[Union[Tuple[float, float], dict]],
                     radius_m: int = 200, category: str = None) -> dict:
        """Batch nearby-places lookup. POST /places/batch"""
        if len(coordinates) > 10000:
            raise InvalidRequestError("Max 10,000 per batch")
        coords = [
            {"lat": c[0], "lng": c[1]} if isinstance(c, tuple) else c
            for c in coordinates
        ]
        body = {"coordinates": coords, "radius": radius_m}
        if category: body["category"] = category
        return self._request("POST", "/places/batch", json=body)

    def place_by_id(self, place_id: str) -> dict:
        """Single place by id. GET /places/{id}"""
        return self._request("GET", f"/places/{place_id}")

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

    def division_by_id(self, division_id: str) -> dict:
        """Single division by id. GET /divisions/{id}"""
        return self._request("GET", f"/divisions/{division_id}")

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

    def close(self):
        """Close the client session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
