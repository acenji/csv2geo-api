<?php
/**
 * CSV2GEO API - PHP Geocoding Example
 */

define('API_KEY', 'YOUR_API_KEY');
define('BASE_URL', 'https://api.csv2geo.com/v1');

/**
 * Forward geocode an address to coordinates
 *
 * @param string $address The address to geocode
 * @return array Geocoding result
 */
function geocode(string $address): array
{
    $params = http_build_query([
        'q' => $address,
        'api_key' => API_KEY
    ]);

    $response = file_get_contents(BASE_URL . "/geocode?{$params}");

    if ($response === false) {
        throw new Exception('Geocoding request failed');
    }

    return json_decode($response, true);
}

/**
 * Reverse geocode coordinates to an address
 *
 * @param float $lat Latitude
 * @param float $lng Longitude
 * @return array Address result
 */
function reverseGeocode(float $lat, float $lng): array
{
    $params = http_build_query([
        'lat' => $lat,
        'lng' => $lng,
        'api_key' => API_KEY
    ]);

    $response = file_get_contents(BASE_URL . "/reverse?{$params}");

    if ($response === false) {
        throw new Exception('Reverse geocoding request failed');
    }

    return json_decode($response, true);
}

/**
 * Batch geocode multiple addresses
 *
 * @param array $addresses Array of addresses (max 10,000)
 * @return array Batch results
 */
function batchGeocode(array $addresses): array
{
    $ch = curl_init(BASE_URL . '/geocode');

    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . API_KEY
        ],
        CURLOPT_POSTFIELDS => json_encode(['addresses' => $addresses])
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200) {
        throw new Exception("Batch geocoding failed with status {$httpCode}");
    }

    return json_decode($response, true);
}

// Example usage
try {
    // Forward geocoding
    echo "Forward Geocoding:\n";
    $result = geocode('1600 Pennsylvania Ave, Washington DC');
    echo "  Address: {$result['results'][0]['formatted_address']}\n";
    echo "  Lat: {$result['results'][0]['location']['lat']}\n";
    echo "  Lng: {$result['results'][0]['location']['lng']}\n";

    // Reverse geocoding
    echo "\nReverse Geocoding:\n";
    $reverseResult = reverseGeocode(38.8977, -77.0365);
    echo "  Address: {$reverseResult['results'][0]['formatted_address']}\n";

    // Batch geocoding
    $addresses = [
        '1600 Pennsylvania Ave, Washington DC',
        '350 Fifth Avenue, New York, NY',
        '1 Infinite Loop, Cupertino, CA'
    ];
    $batchResult = batchGeocode($addresses);
    echo "\nBatch Geocoding: " . count($batchResult['results']) . " addresses processed\n";

} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
