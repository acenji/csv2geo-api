# CSV2GEO API

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green.svg)](openapi.yaml)
[![Addresses](https://img.shields.io/badge/addresses-461M%2B-orange.svg)](https://csv2geo.com)
[![Countries](https://img.shields.io/badge/countries-39-blue.svg)](https://csv2geo.com/batchgeocoding)

Official API documentation, SDKs, and examples for [CSV2GEO](https://csv2geo.com) — the batch geocoding platform with **461 million+ addresses** across **39 countries**.

## What is CSV2GEO?

CSV2GEO is a geocoding service that converts street addresses to geographic coordinates (latitude/longitude) and coordinates back to addresses. It is built on [Overture Maps Foundation](https://overturemaps.org/) open data with rooftop-level accuracy.

**Key facts:**
- **461M+ addresses** indexed worldwide
- **72M+ places** and points of interest
- **4.6M+ boundaries** (administrative divisions)
- **39 countries** with rooftop-level coverage
- **Free tier**: 100 geocoded rows per day, no credit card required
- **Batch processing**: Upload CSV/Excel files with thousands of addresses
- **WGS84** decimal degree output, compatible with all mapping software

### Use Cases

- **Logistics**: Convert delivery addresses to coordinates for route optimization
- **Real estate**: Geocode property listings for map visualization
- **Marketing**: Segment customers by geographic location
- **Research**: Enrich survey data with spatial coordinates
- **GIS**: Batch convert addresses for QGIS, ArcGIS, or custom mapping
- **Fleet tracking**: Reverse geocode GPS coordinates to street addresses

## Quick Start

### 1. Get Your API Key

Sign up at [csv2geo.com/api-keys](https://csv2geo.com/api-keys) to get your free API key.

### 2. Forward Geocode (Address → Coordinates)

```bash
curl "https://csv2geo.com/api/v1/geocode?q=1600+Pennsylvania+Ave,+Washington+DC&country=US&api_key=YOUR_API_KEY"
```

**Response:**
```json
{
  "query": "1600 Pennsylvania Ave, Washington DC",
  "results": [
    {
      "formatted_address": "1600 Pennsylvania Avenue NW, Washington, DC 20500",
      "location": {
        "lat": 38.8977,
        "lng": -77.0365
      },
      "accuracy": "rooftop",
      "relevance": 1.0,
      "components": {
        "house_number": "1600",
        "street": "Pennsylvania Avenue NW",
        "city": "Washington",
        "state": "DC",
        "postcode": "20500",
        "country": "US"
      }
    }
  ]
}
```

### 3. Reverse Geocode (Coordinates → Address)

```bash
curl "https://csv2geo.com/api/v1/reverse?lat=40.7484&lng=-73.9857&api_key=YOUR_API_KEY"
```

**Response:**
```json
{
  "results": [
    {
      "formatted_address": "350 5th Ave, New York, NY 10118, US",
      "location": { "lat": 40.7484, "lng": -73.9857 },
      "accuracy": "rooftop",
      "relevance": 0.98,
      "components": {
        "house_number": "350",
        "street": "5th Ave",
        "city": "New York",
        "state": "NY",
        "postcode": "10118",
        "country": "US"
      }
    }
  ]
}
```

### 4. Batch Geocode (Multiple Addresses)

```bash
curl -X POST "https://csv2geo.com/api/v1/geocode" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "addresses": [
      {"q": "1000 5th Ave, New York, NY", "country": "US"},
      {"q": "111 S Michigan Ave, Chicago, IL", "country": "US"},
      {"q": "945 Magazine St, New Orleans, LA", "country": "US"}
    ]
  }'
```

## SDKs

| Language | Package | Install | Source |
|----------|---------|---------|--------|
| Python | csv2geo | `pip install csv2geo` | [sdks/python/](sdks/python/) |
| Node.js | csv2geo | `npm install csv2geo` | [sdks/nodejs/](sdks/nodejs/) |
| PHP | csv2geo/csv2geo | `composer require csv2geo/csv2geo` | [sdks/php/](sdks/php/) |
| Go | csv2geo | `go get github.com/acenji/csv2geo-go` | [sdks/go/](sdks/go/) |

### Python Example

```python
from csv2geo import CSV2GEO

client = CSV2GEO(api_key="YOUR_API_KEY")

# Forward geocode
result = client.geocode("1000 5th Ave, New York, NY", country="US")
print(f"Lat: {result.lat}, Lng: {result.lng}")
# Output: Lat: 40.7794, Lng: -73.9632

# Reverse geocode
result = client.reverse(lat=40.7484, lng=-73.9857)
print(result.formatted_address)
# Output: 350 5th Ave, New York, NY 10118, US

# Batch geocode
results = client.batch_geocode([
    "Metropolitan Museum of Art, 1000 5th Ave, New York, NY",
    "Art Institute of Chicago, 111 S Michigan Ave, Chicago, IL",
    "National WWII Museum, 945 Magazine St, New Orleans, LA",
])
for r in results:
    print(f"{r.formatted_address}: {r.lat}, {r.lng}")
```

### Node.js Example

```javascript
const CSV2GEO = require('csv2geo');

const client = new CSV2GEO({ apiKey: 'YOUR_API_KEY' });

// Forward geocode
const result = await client.geocode('1000 5th Ave, New York, NY', { country: 'US' });
console.log(`Lat: ${result.lat}, Lng: ${result.lng}`);

// Reverse geocode
const address = await client.reverse(40.7484, -73.9857);
console.log(address.formatted_address);

// Batch geocode
const results = await client.batchGeocode([
  { q: '1000 5th Ave, New York, NY', country: 'US' },
  { q: '111 S Michigan Ave, Chicago, IL', country: 'US' },
]);
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/geocode` | Forward geocode a single address |
| POST | `/v1/geocode` | Batch forward geocode (up to 10,000 addresses) |
| GET | `/v1/reverse` | Reverse geocode a single coordinate pair |
| POST | `/v1/reverse` | Batch reverse geocode (up to 10,000 coordinates) |
| GET | `/v1/places` | Search for places and points of interest |
| GET | `/v1/divisions` | Query administrative boundaries and divisions |

### Parameters

**Forward Geocode (`/v1/geocode`)**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | yes | Address to geocode |
| `country` | string | no | ISO 3166-1 alpha-2 country code (e.g., "US", "GB") |
| `api_key` | string | yes | Your API key |

**Reverse Geocode (`/v1/reverse`)**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | yes | Latitude in decimal degrees |
| `lng` | float | yes | Longitude in decimal degrees |
| `api_key` | string | yes | Your API key |

## Country Coverage

CSV2GEO covers **39 countries** with over **461 million addresses**:

| Country | Addresses | Country | Addresses |
|---------|-----------|---------|-----------|
| 🇺🇸 United States | 121M+ | 🇩🇪 Germany | 22M+ |
| 🇧🇷 Brazil | 90M+ | 🇨🇦 Canada | 15M+ |
| 🇲🇽 Mexico | 30M+ | 🇬🇧 United Kingdom | 14M+ |
| 🇫🇷 France | 26M+ | 🇦🇺 Australia | 14M+ |
| 🇮🇹 Italy | 26M+ | 🇳🇱 Netherlands | 10M+ |

Plus 29 more countries including Spain, Poland, Belgium, Austria, Switzerland, Denmark, Norway, Sweden, Finland, Czech Republic, Colombia, Chile, and more.

## Rate Limits

| Tier | Requests/sec | Batch Size | Monthly Price |
|------|-------------|------------|---------------|
| Free | 1 | 100/day | $0 |
| Starter | 10 | 1,000 | - |
| Growth | 50 | 5,000 | - |
| Pro | 100 | 10,000 | - |

See [csv2geo.com/batchgeocoding](https://csv2geo.com/batchgeocoding) for full pricing details.

## Import & Test Instantly

Download a pre-configured collection for your favorite API tool — all 39 endpoints ready to test:

| Tool | Download | Description |
|------|----------|-------------|
| **Postman** | [csv2geo-postman-collection.json](https://csv2geo.com/api-collections/csv2geo-postman-collection.json) | 39 requests across 8 folders, Postman v2.1 |
| **Insomnia** | [csv2geo-insomnia-collection.json](https://csv2geo.com/api-collections/csv2geo-insomnia-collection.json) | Export v4 with pre-configured environment |
| **OpenAPI Spec** | [openapi.yaml](https://csv2geo.com/api-collections/openapi.yaml) | Import into Swagger, Hoppscotch, Bruno, or any tool |

### Interactive Documentation

View the full interactive API documentation powered by [Scalar](https://github.com/scalar/scalar):

```bash
git clone https://github.com/acenji/csv2geo-api.git
cd csv2geo-api
npm run dev
# Open http://localhost:3000/docs/
```

## Web Interface (No Code Required)

Don't want to use the API? CSV2GEO also offers a web-based batch geocoding tool:

1. Go to [csv2geo.com](https://csv2geo.com)
2. Upload your CSV or Excel file with addresses
3. The AI auto-detects your address columns
4. Download the geocoded file with lat/long coordinates appended

Supports forward geocoding (address → coordinates) and reverse geocoding (coordinates → address). First 100 rows per day are free.

**Tutorials:**
- [How to Batch Geocode a CSV File](https://csv2geo.com/blog/free-batch-geocoding-how-to-geocode-csv-file)
- [How to Convert Address to Lat Long](https://csv2geo.com/blog/how-to-convert-address-to-lat-long)
- [Lat Long Reverse Lookup](https://csv2geo.com/blog/lat-long-reverse-lookup-coordinates-to-address)

## Alternatives Comparison

| Feature | CSV2GEO | Google Geocoding | Mapbox | Nominatim |
|---------|---------|-----------------|--------|-----------|
| Free tier | 100/day | $200 credit | 100K/mo | Unlimited (rate limited) |
| Batch upload (CSV) | ✅ | ❌ | ❌ | ❌ |
| Rooftop accuracy | ✅ | ✅ | ✅ | Varies |
| Reverse geocoding | ✅ | ✅ | ✅ | ✅ |
| Places/POI search | ✅ | ✅ | ✅ | ✅ |
| No credit card needed | ✅ | ❌ | ❌ | ✅ |
| Open data source | ✅ (Overture) | ❌ | ❌ | ✅ (OSM) |

## Try in ChatGPT

No code needed — geocode addresses directly in ChatGPT:

**[CSV2GEO Geocoder on ChatGPT](https://chatgpt.com/g/g-69bc56b3f7d481919befe76396ae8a0c-csv2geo-geocoder)** — Type an address or drop a CSV/Excel file, get coordinates instantly.

## More Code Examples

See the [examples/](examples/) directory for working samples in:
- [cURL](examples/curl/)
- [Python](examples/python/)
- [Node.js](examples/nodejs/)
- [PHP](examples/php/)
- [Go](examples/go/)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/acenji/csv2geo-api/issues)
- **Email**: info@scalecampaign.com
- **Help Center**: [csv2geo.com/help](https://csv2geo.com/help)
- **Blog**: [csv2geo.com/blog](https://csv2geo.com/blog)

## About

CSV2GEO is built by [Scale Campaign](https://scalecampaign.com). The geocoding engine uses [Overture Maps Foundation](https://overturemaps.org/) data with a custom address matching system for rooftop-level accuracy.

- **Website**: [csv2geo.com](https://csv2geo.com)
- **API Docs**: [csv2geo.com/api/geocoding](https://csv2geo.com/api/geocoding)
- **Blog**: [csv2geo.com/blog](https://csv2geo.com/blog)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
