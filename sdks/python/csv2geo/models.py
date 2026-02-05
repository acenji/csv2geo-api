"""Data models for CSV2GEO API responses."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Location:
    """Geographic coordinates."""
    lat: float
    lng: float

    def __str__(self) -> str:
        return f"{self.lat}, {self.lng}"

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lng": self.lng}


@dataclass
class AddressComponents:
    """Parsed address components."""
    house_number: Optional[str] = None
    street: Optional[str] = None
    unit: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "AddressComponents":
        return cls(
            house_number=data.get("house_number"),
            street=data.get("street"),
            unit=data.get("unit"),
            city=data.get("city"),
            state=data.get("state"),
            postcode=data.get("postcode"),
            country=data.get("country"),
        )


@dataclass
class GeocodeResult:
    """A single geocoding result."""
    formatted_address: str
    lat: float
    lng: float
    accuracy: str
    accuracy_score: float
    components: AddressComponents

    @property
    def location(self) -> Location:
        """Get location as a Location object."""
        return Location(lat=self.lat, lng=self.lng)

    @classmethod
    def from_dict(cls, data: dict) -> "GeocodeResult":
        location = data.get("location", {})
        return cls(
            formatted_address=data.get("formatted_address", ""),
            lat=location.get("lat", 0.0),
            lng=location.get("lng", 0.0),
            accuracy=data.get("accuracy", ""),
            accuracy_score=data.get("accuracy_score", 0.0),
            components=AddressComponents.from_dict(data.get("components", {})),
        )

    def to_dict(self) -> dict:
        return {
            "formatted_address": self.formatted_address,
            "location": {"lat": self.lat, "lng": self.lng},
            "accuracy": self.accuracy,
            "accuracy_score": self.accuracy_score,
        }


@dataclass
class GeocodeResponse:
    """Response from a geocode request."""
    query: str
    results: List[GeocodeResult]

    @property
    def best(self) -> Optional[GeocodeResult]:
        """Get the best (first) result, or None if no results."""
        return self.results[0] if self.results else None

    @classmethod
    def from_dict(cls, data: dict) -> "GeocodeResponse":
        results = [
            GeocodeResult.from_dict(r)
            for r in data.get("results", [])
        ]
        return cls(
            query=data.get("query", ""),
            results=results,
        )


@dataclass
class BatchGeocodeResponse:
    """Response from a batch geocode request."""
    results: List[GeocodeResponse]
    total: int
    successful: int
    failed: int

    @classmethod
    def from_dict(cls, data: dict) -> "BatchGeocodeResponse":
        meta = data.get("meta", {})
        results = [
            GeocodeResponse.from_dict(r)
            for r in data.get("results", [])
        ]
        return cls(
            results=results,
            total=meta.get("total", len(results)),
            successful=meta.get("successful", len(results)),
            failed=meta.get("failed", 0),
        )
