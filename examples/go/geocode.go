// CSV2GEO API - Go Geocoding Example
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

const (
	apiKey  = "YOUR_API_KEY"
	baseURL = "https://api.csv2geo.com/v1"
)

// Location represents a geographic coordinate
type Location struct {
	Lat float64 `json:"lat"`
	Lng float64 `json:"lng"`
}

// AddressComponents contains parsed address parts
type AddressComponents struct {
	HouseNumber string `json:"house_number"`
	Street      string `json:"street"`
	City        string `json:"city"`
	State       string `json:"state"`
	Postcode    string `json:"postcode"`
	Country     string `json:"country"`
}

// GeocodeResult represents a single geocoding result
type GeocodeResult struct {
	FormattedAddress string            `json:"formatted_address"`
	Location         Location          `json:"location"`
	Accuracy         string            `json:"accuracy"`
	Components       AddressComponents `json:"components"`
}

// GeocodeResponse is the API response for geocoding
type GeocodeResponse struct {
	Query   string          `json:"query"`
	Results []GeocodeResult `json:"results"`
}

// Geocode converts an address to coordinates
func Geocode(address string) (*GeocodeResponse, error) {
	params := url.Values{}
	params.Add("q", address)
	params.Add("api_key", apiKey)

	resp, err := http.Get(fmt.Sprintf("%s/geocode?%s", baseURL, params.Encode()))
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("geocoding failed: %s", string(body))
	}

	var result GeocodeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ReverseGeocode converts coordinates to an address
func ReverseGeocode(lat, lng float64) (*GeocodeResponse, error) {
	params := url.Values{}
	params.Add("lat", fmt.Sprintf("%f", lat))
	params.Add("lng", fmt.Sprintf("%f", lng))
	params.Add("api_key", apiKey)

	resp, err := http.Get(fmt.Sprintf("%s/reverse?%s", baseURL, params.Encode()))
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("reverse geocoding failed: %s", string(body))
	}

	var result GeocodeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// BatchGeocodeRequest is the request body for batch geocoding
type BatchGeocodeRequest struct {
	Addresses []string `json:"addresses"`
}

// BatchGeocodeResponse is the response for batch geocoding
type BatchGeocodeResponse struct {
	Results []GeocodeResponse `json:"results"`
}

// BatchGeocode geocodes multiple addresses
func BatchGeocode(addresses []string) (*BatchGeocodeResponse, error) {
	reqBody, err := json.Marshal(BatchGeocodeRequest{Addresses: addresses})
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", baseURL+"/geocode", bytes.NewBuffer(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("batch geocoding failed: %s", string(body))
	}

	var result BatchGeocodeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

func main() {
	// Forward geocoding
	fmt.Println("Forward Geocoding:")
	result, err := Geocode("1600 Pennsylvania Ave, Washington DC")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Address: %s\n", result.Results[0].FormattedAddress)
	fmt.Printf("  Lat: %f\n", result.Results[0].Location.Lat)
	fmt.Printf("  Lng: %f\n", result.Results[0].Location.Lng)

	// Reverse geocoding
	fmt.Println("\nReverse Geocoding:")
	reverseResult, err := ReverseGeocode(38.8977, -77.0365)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Address: %s\n", reverseResult.Results[0].FormattedAddress)

	// Batch geocoding
	addresses := []string{
		"1600 Pennsylvania Ave, Washington DC",
		"350 Fifth Avenue, New York, NY",
		"1 Infinite Loop, Cupertino, CA",
	}
	batchResult, err := BatchGeocode(addresses)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("\nBatch Geocoding: %d addresses processed\n", len(batchResult.Results))
}
