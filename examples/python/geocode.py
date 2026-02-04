"""
CSV2GEO API - Python Geocoding Example
"""
import requests

API_KEY = "YOUR_API_KEY"
BASE_URL = "https://api.csv2geo.com/v1"


def geocode(address: str) -> dict:
    """
    Forward geocode an address to coordinates.

    Args:
        address: The address to geocode

    Returns:
        dict: Geocoding result with lat/lng
    """
    response = requests.get(
        f"{BASE_URL}/geocode",
        params={
            "q": address,
            "api_key": API_KEY
        }
    )
    response.raise_for_status()
    return response.json()


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Reverse geocode coordinates to an address.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        dict: Address result
    """
    response = requests.get(
        f"{BASE_URL}/reverse",
        params={
            "lat": lat,
            "lng": lng,
            "api_key": API_KEY
        }
    )
    response.raise_for_status()
    return response.json()


def batch_geocode(addresses: list[str]) -> dict:
    """
    Batch geocode multiple addresses.

    Args:
        addresses: List of addresses (max 10,000)

    Returns:
        dict: Batch geocoding results
    """
    response = requests.post(
        f"{BASE_URL}/geocode",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"addresses": addresses}
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Example: Forward geocoding
    result = geocode("1600 Pennsylvania Ave, Washington DC")
    print("Forward Geocoding:")
    print(f"  Address: {result['results'][0]['formatted_address']}")
    print(f"  Lat: {result['results'][0]['location']['lat']}")
    print(f"  Lng: {result['results'][0]['location']['lng']}")

    # Example: Reverse geocoding
    result = reverse_geocode(38.8977, -77.0365)
    print("\nReverse Geocoding:")
    print(f"  Address: {result['results'][0]['formatted_address']}")

    # Example: Batch geocoding
    addresses = [
        "1600 Pennsylvania Ave, Washington DC",
        "350 Fifth Avenue, New York, NY",
        "1 Infinite Loop, Cupertino, CA"
    ]
    result = batch_geocode(addresses)
    print(f"\nBatch Geocoding: {len(result['results'])} addresses processed")
