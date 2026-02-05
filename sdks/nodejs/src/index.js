/**
 * CSV2GEO Node.js SDK
 *
 * Fast, accurate geocoding powered by 446M+ addresses worldwide.
 *
 * @example
 * const { Client } = require('csv2geo');
 *
 * const client = new Client('your_api_key');
 * const result = await client.geocode('1600 Pennsylvania Ave, Washington DC');
 * console.log(result.lat, result.lng);
 */

const {
  CSV2GEOError,
  AuthenticationError,
  RateLimitError,
  InvalidRequestError,
  PermissionError,
  APIError,
} = require('./errors');

const DEFAULT_BASE_URL = 'https://api.csv2geo.com/v1';
const DEFAULT_TIMEOUT = 30000;
const MAX_RETRIES = 3;

/**
 * CSV2GEO API Client
 */
class Client {
  /**
   * Create a new CSV2GEO client
   * @param {string} apiKey - Your CSV2GEO API key
   * @param {Object} [options] - Configuration options
   * @param {string} [options.baseUrl] - API base URL
   * @param {number} [options.timeout] - Request timeout in milliseconds
   * @param {boolean} [options.autoRetry] - Auto-retry on rate limit (default: true)
   */
  constructor(apiKey, options = {}) {
    if (!apiKey) {
      throw new Error('API key is required');
    }

    this.apiKey = apiKey;
    this.baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, '');
    this.timeout = options.timeout || DEFAULT_TIMEOUT;
    this.autoRetry = options.autoRetry !== false;

    // Rate limit tracking
    this.rateLimit = null;
    this.rateLimitRemaining = null;
    this.rateLimitReset = null;
  }

  /**
   * Make an API request
   * @private
   */
  async _request(method, endpoint, params = {}, body = null, retryCount = 0) {
    const url = new URL(`${this.baseUrl}${endpoint}`);

    // Add query parameters
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const fetchOptions = {
        method,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'User-Agent': 'csv2geo-node/1.0.0',
        },
        signal: controller.signal,
      };

      if (body) {
        fetchOptions.body = JSON.stringify(body);
      }

      const response = await fetch(url.toString(), fetchOptions);
      clearTimeout(timeoutId);

      // Update rate limit info
      this.rateLimit = response.headers.get('X-RateLimit-Limit');
      this.rateLimitRemaining = response.headers.get('X-RateLimit-Remaining');
      this.rateLimitReset = response.headers.get('X-RateLimit-Reset');

      const data = await response.json();

      if (response.ok) {
        return data;
      }

      // Handle errors
      const error = data.error || {};
      const code = error.code || 'unknown';
      const message = error.message || 'Unknown error';
      const status = error.status || response.status;

      if (response.status === 401) {
        throw new AuthenticationError(message, code, status);
      } else if (response.status === 403) {
        throw new PermissionError(message, code, status);
      } else if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After') || '60', 10);
        const rateLimitError = new RateLimitError(message, code, status, retryAfter);

        if (this.autoRetry && retryCount < MAX_RETRIES) {
          await this._sleep(Math.min(retryAfter * 1000, 60000));
          return this._request(method, endpoint, params, body, retryCount + 1);
        }
        throw rateLimitError;
      } else if (response.status === 400) {
        throw new InvalidRequestError(message, code, status);
      } else {
        throw new APIError(message, code, status);
      }
    } catch (err) {
      clearTimeout(timeoutId);

      if (err.name === 'AbortError') {
        throw new APIError('Request timed out', 'timeout');
      }
      if (err instanceof CSV2GEOError) {
        throw err;
      }
      throw new APIError(err.message, 'network_error');
    }
  }

  /**
   * Sleep helper
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Geocode a single address
   * @param {string} address - The address to geocode
   * @param {Object} [options] - Options
   * @param {string} [options.country] - Limit to specific country (ISO 3166-1 alpha-2)
   * @returns {Promise<GeocodeResult|null>} Best result or null if not found
   *
   * @example
   * const result = await client.geocode('1600 Pennsylvania Ave, Washington DC');
   * if (result) {
   *   console.log(result.lat, result.lng);
   * }
   */
  async geocode(address, options = {}) {
    const params = { q: address };
    if (options.country) params.country = options.country;

    const data = await this._request('GET', '/geocode', params);
    const results = data.results || [];
    return results.length > 0 ? this._parseResult(results[0]) : null;
  }

  /**
   * Geocode with full response
   * @param {string} address - The address to geocode
   * @param {Object} [options] - Options
   * @returns {Promise<GeocodeResponse>} Full response with all results
   */
  async geocodeFull(address, options = {}) {
    const params = { q: address };
    if (options.country) params.country = options.country;

    const data = await this._request('GET', '/geocode', params);
    return {
      query: data.query,
      results: (data.results || []).map(r => this._parseResult(r)),
    };
  }

  /**
   * Reverse geocode coordinates
   * @param {number} lat - Latitude
   * @param {number} lng - Longitude
   * @returns {Promise<GeocodeResult|null>} Best result or null if not found
   *
   * @example
   * const result = await client.reverse(38.8977, -77.0365);
   * if (result) {
   *   console.log(result.formattedAddress);
   * }
   */
  async reverse(lat, lng) {
    const data = await this._request('GET', '/reverse', { lat, lng });
    const results = data.results || [];
    return results.length > 0 ? this._parseResult(results[0]) : null;
  }

  /**
   * Reverse geocode with full response
   * @param {number} lat - Latitude
   * @param {number} lng - Longitude
   * @returns {Promise<GeocodeResponse>} Full response with all results
   */
  async reverseFull(lat, lng) {
    const data = await this._request('GET', '/reverse', { lat, lng });
    return {
      query: data.query,
      results: (data.results || []).map(r => this._parseResult(r)),
    };
  }

  /**
   * Batch geocode multiple addresses
   * @param {string[]} addresses - Array of addresses (max 10,000)
   * @returns {Promise<GeocodeResponse[]>} Array of responses
   *
   * @example
   * const results = await client.geocodeBatch([
   *   '1600 Pennsylvania Ave, Washington DC',
   *   '350 Fifth Avenue, New York, NY',
   * ]);
   */
  async geocodeBatch(addresses) {
    if (addresses.length > 10000) {
      throw new InvalidRequestError('Maximum 10,000 addresses per batch request');
    }

    const data = await this._request('POST', '/geocode', {}, { addresses });
    return (data.results || []).map(r => ({
      query: r.query,
      results: (r.results || []).map(res => this._parseResult(res)),
    }));
  }

  /**
   * Batch reverse geocode multiple coordinates
   * @param {Array<{lat: number, lng: number}>} coordinates - Array of coordinates (max 10,000)
   * @returns {Promise<GeocodeResponse[]>} Array of responses
   *
   * @example
   * const results = await client.reverseBatch([
   *   { lat: 38.8977, lng: -77.0365 },
   *   { lat: 40.7484, lng: -73.9857 },
   * ]);
   */
  async reverseBatch(coordinates) {
    if (coordinates.length > 10000) {
      throw new InvalidRequestError('Maximum 10,000 coordinates per batch request');
    }

    const data = await this._request('POST', '/reverse', {}, { coordinates });
    return (data.results || []).map(r => ({
      query: r.query,
      results: (r.results || []).map(res => this._parseResult(res)),
    }));
  }

  /**
   * Parse API result into GeocodeResult
   * @private
   */
  _parseResult(data) {
    const location = data.location || {};
    return {
      formattedAddress: data.formatted_address,
      lat: location.lat,
      lng: location.lng,
      accuracy: data.accuracy,
      accuracyScore: data.accuracy_score,
      components: {
        houseNumber: data.components?.house_number,
        street: data.components?.street,
        unit: data.components?.unit,
        city: data.components?.city,
        state: data.components?.state,
        postcode: data.components?.postcode,
        country: data.components?.country,
      },
    };
  }
}

module.exports = {
  Client,
  CSV2GEOError,
  AuthenticationError,
  RateLimitError,
  InvalidRequestError,
  PermissionError,
  APIError,
};
