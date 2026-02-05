"""
CSV2GEO Python SDK

Fast, accurate geocoding powered by 446M+ addresses worldwide.

Usage:
    from csv2geo import Client

    client = Client("your_api_key")
    result = client.geocode("1600 Pennsylvania Ave, Washington DC")
    print(result.lat, result.lng)
"""

from .client import Client
from .models import GeocodeResult, Location, AddressComponents
from .exceptions import (
    CSV2GEOError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    APIError,
)

__version__ = "1.0.0"
__all__ = [
    "Client",
    "GeocodeResult",
    "Location",
    "AddressComponents",
    "CSV2GEOError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "APIError",
]
