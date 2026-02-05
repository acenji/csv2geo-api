# CSV2GEO Python SDK

[![PyPI version](https://img.shields.io/pypi/v/csv2geo.svg)](https://pypi.org/project/csv2geo/)
[![Python versions](https://img.shields.io/pypi/pyversions/csv2geo.svg)](https://pypi.org/project/csv2geo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Official Python SDK for the [CSV2GEO Geocoding API](https://csv2geo.com) - fast, accurate geocoding powered by 446M+ addresses worldwide.

## Installation

```bash
pip install csv2geo
```

## Quick Start

```python
from csv2geo import Client

# Initialize with your API key
client = Client("your_api_key")

# Forward geocoding (address → coordinates)
result = client.geocode("1600 Pennsylvania Ave, Washington DC")
if result:
    print(f"Lat: {result.lat}, Lng: {result.lng}")
    print(f"Address: {result.formatted_address}")

# Reverse geocoding (coordinates → address)
result = client.reverse(38.8977, -77.0365)
if result:
    print(f"Address: {result.formatted_address}")
```

## Features

- **Forward geocoding** - Convert addresses to coordinates
- **Reverse geocoding** - Convert coordinates to addresses
- **Batch processing** - Geocode up to 10,000 addresses per request
- **Auto-retry** - Automatic retry on rate limits
- **Type hints** - Full type annotations for IDE support

## API Reference

### Initialize Client

```python
from csv2geo import Client

client = Client(
    api_key="your_api_key",
    base_url="https://api.csv2geo.com/v1",  # optional
    timeout=30,  # optional, seconds
    auto_retry=True,  # optional, retry on rate limit
)
```

### Forward Geocoding

```python
# Simple - returns best match or None
result = client.geocode("1600 Pennsylvania Ave, Washington DC")

# With country filter
result = client.geocode("123 Main St", country="US")

# Full response with all matches
response = client.geocode_full("1600 Pennsylvania Ave")
for result in response.results:
    print(f"{result.formatted_address}: {result.accuracy_score}")
```

### Reverse Geocoding

```python
# Simple - returns best match or None
result = client.reverse(38.8977, -77.0365)

# Full response with all matches
response = client.reverse_full(38.8977, -77.0365)
```

### Batch Geocoding

```python
# Geocode multiple addresses (up to 10,000)
addresses = [
    "1600 Pennsylvania Ave, Washington DC",
    "350 Fifth Avenue, New York, NY",
    "1 Infinite Loop, Cupertino, CA",
]

results = client.geocode_batch(addresses)
for response in results:
    if response.best:
        print(f"{response.query}: {response.best.lat}, {response.best.lng}")
    else:
        print(f"{response.query}: Not found")
```

### Batch Reverse Geocoding

```python
# Reverse geocode multiple coordinates
coordinates = [
    (38.8977, -77.0365),
    (40.7484, -73.9857),
]

results = client.reverse_batch(coordinates)
for response in results:
    if response.best:
        print(response.best.formatted_address)
```

### GeocodeResult Object

```python
result = client.geocode("1600 Pennsylvania Ave, Washington DC")

# Coordinates
result.lat           # 38.8977
result.lng           # -77.0365
result.location      # Location(lat=38.8977, lng=-77.0365)

# Address
result.formatted_address  # "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC 20500, US"
result.accuracy           # "rooftop"
result.accuracy_score     # 1.0

# Components
result.components.house_number  # "1600"
result.components.street        # "PENNSYLVANIA AVE NW"
result.components.city          # "WASHINGTON"
result.components.state         # "DC"
result.components.postcode      # "20500"
result.components.country       # "US"
```

## Error Handling

```python
from csv2geo import Client, AuthenticationError, RateLimitError, InvalidRequestError

client = Client("your_api_key")

try:
    result = client.geocode("123 Main St")
except AuthenticationError as e:
    print(f"Invalid API key: {e.message}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except InvalidRequestError as e:
    print(f"Invalid request: {e.message}")
```

## Rate Limits

The client tracks rate limit headers automatically:

```python
client.geocode("123 Main St")

print(client.rate_limit)            # Max requests per minute
print(client.rate_limit_remaining)  # Requests remaining
print(client.rate_limit_reset)      # Unix timestamp when limit resets
```

With `auto_retry=True` (default), the client automatically waits and retries when rate limited.

## Context Manager

```python
with Client("your_api_key") as client:
    result = client.geocode("123 Main St")
    print(result.lat, result.lng)
# Session automatically closed
```

## Get Your API Key

Sign up at [csv2geo.com](https://csv2geo.com) to get your API key.

## Documentation

- [API Documentation](https://acenji.github.io/csv2geo-api/docs/)
- [OpenAPI Specification](https://github.com/acenji/csv2geo-api/blob/main/openapi.yaml)

## License

MIT License - see [LICENSE](https://github.com/acenji/csv2geo-api/blob/main/LICENSE) for details.
