/**
 * CSV2GEO API - Node.js Geocoding Example
 */

const API_KEY = 'YOUR_API_KEY';
const BASE_URL = 'https://api.csv2geo.com/v1';

/**
 * Forward geocode an address to coordinates
 * @param {string} address - The address to geocode
 * @returns {Promise<object>} Geocoding result
 */
async function geocode(address) {
  const params = new URLSearchParams({
    q: address,
    api_key: API_KEY
  });

  const response = await fetch(`${BASE_URL}/geocode?${params}`);

  if (!response.ok) {
    throw new Error(`Geocoding failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Reverse geocode coordinates to an address
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {Promise<object>} Address result
 */
async function reverseGeocode(lat, lng) {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lng: lng.toString(),
    api_key: API_KEY
  });

  const response = await fetch(`${BASE_URL}/reverse?${params}`);

  if (!response.ok) {
    throw new Error(`Reverse geocoding failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Batch geocode multiple addresses
 * @param {string[]} addresses - Array of addresses (max 10,000)
 * @returns {Promise<object>} Batch results
 */
async function batchGeocode(addresses) {
  const response = await fetch(`${BASE_URL}/geocode`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`
    },
    body: JSON.stringify({ addresses })
  });

  if (!response.ok) {
    throw new Error(`Batch geocoding failed: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
async function main() {
  try {
    // Forward geocoding
    console.log('Forward Geocoding:');
    const result = await geocode('1600 Pennsylvania Ave, Washington DC');
    console.log(`  Address: ${result.results[0].formatted_address}`);
    console.log(`  Lat: ${result.results[0].location.lat}`);
    console.log(`  Lng: ${result.results[0].location.lng}`);

    // Reverse geocoding
    console.log('\nReverse Geocoding:');
    const reverseResult = await reverseGeocode(38.8977, -77.0365);
    console.log(`  Address: ${reverseResult.results[0].formatted_address}`);

    // Batch geocoding
    const addresses = [
      '1600 Pennsylvania Ave, Washington DC',
      '350 Fifth Avenue, New York, NY',
      '1 Infinite Loop, Cupertino, CA'
    ];
    const batchResult = await batchGeocode(addresses);
    console.log(`\nBatch Geocoding: ${batchResult.results.length} addresses processed`);

  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
