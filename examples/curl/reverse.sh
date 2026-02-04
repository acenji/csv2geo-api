#!/bin/bash
# CSV2GEO API - Reverse Geocoding Example
# Replace YOUR_API_KEY with your actual API key

API_KEY="YOUR_API_KEY"
LAT="38.8977"
LNG="-77.0365"

# Make the request
curl -s "https://api.csv2geo.com/v1/reverse?lat=${LAT}&lng=${LNG}&api_key=${API_KEY}" | json_pp
