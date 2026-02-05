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

    DEFAULT_BASE_URL = "https://api.csv2geo.com/v1"
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
            base_url: API base URL (default: https://api.csv2geo.com/v1)
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
            "User-Agent": "csv2geo-python/1.0.0",
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

    def close(self):
        """Close the client session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
