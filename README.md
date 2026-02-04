# CSV2GEO API

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green.svg)](openapi.yaml)

Official API documentation, SDKs, and examples for [CSV2GEO](https://csv2geo.com) - the batch geocoding service.

## Features

- **Forward Geocoding** - Convert addresses to latitude/longitude coordinates
- **Reverse Geocoding** - Convert coordinates to human-readable addresses
- **Batch Processing** - Geocode thousands of addresses in a single request
- **Global Coverage** - 446M+ addresses worldwide
- **High Accuracy** - Rooftop-level precision

## Quick Start

### Get Your API Key

Sign up at [csv2geo.com](https://csv2geo.com) to get your API key.

### Make Your First Request

```bash
curl "https://api.csv2geo.com/v1/geocode?q=1600+Pennsylvania+Ave,+Washington+DC&api_key=YOUR_API_KEY"
```

### Response

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

## Documentation

### Interactive API Docs (Scalar)

View the full interactive API documentation:

```bash
# Clone and run locally
git clone https://github.com/acenji/csv2geo-api.git
cd csv2geo-api
npm run dev
# Open http://localhost:3000/docs/
```

Or view the OpenAPI spec directly: [openapi.yaml](openapi.yaml)

### Resources
- [Code Examples](examples/) - Python, Node.js, PHP, Go, cURL
- [OpenAPI Spec](openapi.yaml) - Import into Postman or any API tool

## SDKs

| Language | Package | Install |
|----------|---------|---------|
| Python | [csv2geo](sdks/python/) | `pip install csv2geo` |
| Node.js | [csv2geo](sdks/nodejs/) | `npm install csv2geo` |
| PHP | [csv2geo](sdks/php/) | `composer require csv2geo/csv2geo` |
| Go | [csv2geo](sdks/go/) | `go get github.com/acenji/csv2geo-go` |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/geocode` | Forward geocode a single address |
| POST | `/v1/geocode` | Batch forward geocode (up to 10,000) |
| GET | `/v1/reverse` | Reverse geocode a single coordinate |
| POST | `/v1/reverse` | Batch reverse geocode (up to 10,000) |

## Rate Limits

| Tier | Requests/sec | Batch Size |
|------|--------------|------------|
| Free | 1 | 100 |
| Starter | 10 | 1,000 |
| Growth | 50 | 5,000 |
| Pro | 100 | 10,000 |

## OpenAPI Specification

The complete API is documented in [openapi.yaml](openapi.yaml). You can:

- View it in [Swagger Editor](https://editor.swagger.io)
- Import it into Postman
- Generate client SDKs using [OpenAPI Generator](https://openapi-generator.tech)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/acenji/csv2geo-api/issues)
- **Email**: admin@csv2geo.com
- **Documentation**: [docs.csv2geo.com](https://docs.csv2geo.com)

## About

CSV2GEO is a product of [Scale Campaign](https://scalecampaign.com). This API documentation and SDKs are open source under the MIT license.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
