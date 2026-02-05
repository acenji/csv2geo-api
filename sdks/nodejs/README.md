# CSV2GEO Node.js SDK

[![npm version](https://img.shields.io/npm/v/csv2geo-sdk.svg)](https://www.npmjs.com/package/csv2geo-sdk)
[![Node.js versions](https://img.shields.io/node/v/csv2geo-sdk.svg)](https://www.npmjs.com/package/csv2geo-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Official Node.js SDK for the [CSV2GEO Geocoding API](https://csv2geo.com) - fast, accurate geocoding powered by 446M+ addresses worldwide.

## Installation

```bash
npm install csv2geo-sdk
```

## Quick Start

```javascript
const { Client } = require('csv2geo-sdk');

// Initialize with your API key
const client = new Client('your_api_key');

// Forward geocoding (address → coordinates)
const result = await client.geocode('1600 Pennsylvania Ave, Washington DC');
if (result) {
  console.log(`Lat: ${result.lat}, Lng: ${result.lng}`);
  console.log(`Address: ${result.formattedAddress}`);
}

// Reverse geocoding (coordinates → address)
const result = await client.reverse(38.8977, -77.0365);
if (result) {
  console.log(`Address: ${result.formattedAddress}`);
}
```

## Features

- **Forward geocoding** - Convert addresses to coordinates
- **Reverse geocoding** - Convert coordinates to addresses
- **Batch processing** - Geocode up to 10,000 addresses per request
- **Auto-retry** - Automatic retry on rate limits
- **TypeScript support** - Full type definitions included
- **Zero dependencies** - Uses native `fetch` (Node.js 18+)

## API Reference

### Initialize Client

```javascript
const { Client } = require('csv2geo-sdk');

const client = new Client('your_api_key', {
  baseUrl: 'https://api.csv2geo.com/v1',  // optional
  timeout: 30000,  // optional, milliseconds
  autoRetry: true,  // optional, retry on rate limit
});
```

### Forward Geocoding

```javascript
// Simple - returns best match or null
const result = await client.geocode('1600 Pennsylvania Ave, Washington DC');

// With country filter
const result = await client.geocode('123 Main St', { country: 'US' });

// Full response with all matches
const response = await client.geocodeFull('1600 Pennsylvania Ave');
for (const result of response.results) {
  console.log(`${result.formattedAddress}: ${result.accuracyScore}`);
}
```

### Reverse Geocoding

```javascript
// Simple - returns best match or null
const result = await client.reverse(38.8977, -77.0365);

// Full response with all matches
const response = await client.reverseFull(38.8977, -77.0365);
```

### Batch Geocoding

```javascript
// Geocode multiple addresses (up to 10,000)
const addresses = [
  '1600 Pennsylvania Ave, Washington DC',
  '350 Fifth Avenue, New York, NY',
  '1 Infinite Loop, Cupertino, CA',
];

const results = await client.geocodeBatch(addresses);
for (const response of results) {
  const best = response.results[0];
  if (best) {
    console.log(`${response.query}: ${best.lat}, ${best.lng}`);
  } else {
    console.log(`${response.query}: Not found`);
  }
}
```

### Batch Reverse Geocoding

```javascript
// Reverse geocode multiple coordinates
const coordinates = [
  { lat: 38.8977, lng: -77.0365 },
  { lat: 40.7484, lng: -73.9857 },
];

const results = await client.reverseBatch(coordinates);
for (const response of results) {
  const best = response.results[0];
  if (best) {
    console.log(best.formattedAddress);
  }
}
```

### GeocodeResult Object

```javascript
const result = await client.geocode('1600 Pennsylvania Ave, Washington DC');

// Coordinates
result.lat              // 38.8977
result.lng              // -77.0365

// Address
result.formattedAddress  // "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC 20500, US"
result.accuracy          // "rooftop"
result.accuracyScore     // 1.0

// Components
result.components.houseNumber  // "1600"
result.components.street       // "PENNSYLVANIA AVE NW"
result.components.city         // "WASHINGTON"
result.components.state        // "DC"
result.components.postcode     // "20500"
result.components.country      // "US"
```

## Error Handling

```javascript
const { Client, AuthenticationError, RateLimitError, InvalidRequestError } = require('csv2geo-sdk');

const client = new Client('your_api_key');

try {
  const result = await client.geocode('123 Main St');
} catch (err) {
  if (err instanceof AuthenticationError) {
    console.log(`Invalid API key: ${err.message}`);
  } else if (err instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${err.retryAfter} seconds`);
  } else if (err instanceof InvalidRequestError) {
    console.log(`Invalid request: ${err.message}`);
  }
}
```

## Rate Limits

The client tracks rate limit headers automatically:

```javascript
await client.geocode('123 Main St');

console.log(client.rateLimit);            // Max requests per minute
console.log(client.rateLimitRemaining);   // Requests remaining
console.log(client.rateLimitReset);       // Unix timestamp when limit resets
```

With `autoRetry: true` (default), the client automatically waits and retries when rate limited.

## TypeScript

Full TypeScript support is included:

```typescript
import { Client, GeocodeResult, GeocodeResponse } from 'csv2geo-sdk';

const client = new Client('your_api_key');
const result: GeocodeResult | null = await client.geocode('123 Main St');
```

## Requirements

- Node.js 16+ (uses native `fetch`)

## Get Your API Key

Sign up at [csv2geo.com](https://csv2geo.com) to get your API key.

## Documentation

- [API Documentation](https://acenji.github.io/csv2geo-api/docs/)
- [OpenAPI Specification](https://github.com/acenji/csv2geo-api/blob/main/openapi.yaml)

## License

MIT License - see [LICENSE](https://github.com/acenji/csv2geo-api/blob/main/LICENSE) for details.
