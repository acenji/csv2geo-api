#!/bin/bash
# CSV2GEO API - Forward Geocoding Example
# Replace YOUR_API_KEY with your actual API key

API_KEY="YOUR_API_KEY"
ADDRESS="1600 Pennsylvania Ave, Washington DC"

# URL encode the address
ENCODED_ADDRESS=$(echo "$ADDRESS" | sed 's/ /+/g')

# Make the request
curl -s "https://api.csv2geo.com/v1/geocode?q=${ENCODED_ADDRESS}&api_key=${API_KEY}" | json_pp
