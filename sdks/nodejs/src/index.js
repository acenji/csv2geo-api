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

  // ─────────────────────────────────────────────────────────
  // Address Tools
  // ─────────────────────────────────────────────────────────

  /** Validate an address. GET /validate */
  async validate(address, options = {}) {
    const params = { q: address };
    if (options.country) params.country = options.country;
    return this._request('GET', '/validate', params);
  }

  /** Validate up to 10,000 addresses. POST /validate */
  async validateBatch(addresses) {
    if (addresses.length > 10000) throw new InvalidRequestError('Max 10,000 per batch');
    return this._request('POST', '/validate', {}, { addresses });
  }

  /** Address autocomplete suggestions. GET /autocomplete */
  async autocomplete(query, options = {}) {
    const params = { q: query };
    if (options.country) params.country = options.country;
    if (options.limit)   params.limit   = options.limit;
    return this._request('GET', '/autocomplete', params);
  }

  /** Parse a free-form address into components. GET /parse */
  async parse(address) {
    return this._request('GET', '/parse', { q: address });
  }

  /** Parse up to 10,000 addresses. POST /parse */
  async parseBatch(addresses) {
    if (addresses.length > 10000) throw new InvalidRequestError('Max 10,000 per batch');
    return this._request('POST', '/parse', {}, { addresses });
  }

  /** Standardize an address. GET /standardize */
  async standardize(address) {
    return this._request('GET', '/standardize', { q: address });
  }

  /** Score similarity between two addresses. GET /addresses/compare */
  async compareAddresses(address1, address2) {
    return this._request('GET', '/addresses/compare', { a: address1, b: address2 });
  }

  // ─────────────────────────────────────────────────────────
  // Address inspection
  // ─────────────────────────────────────────────────────────

  /** Find addresses within radius of a coordinate. GET /addresses/nearby */
  async addressesNearby(lat, lng, options = {}) {
    const params = { lat, lng, radius: options.radius || 200 };
    if (options.limit) params.limit = options.limit;
    return this._request('GET', '/addresses/nearby', params);
  }

  /** Get all addresses on a street. GET /addresses/street */
  async addressesStreet(country, city, street) {
    return this._request('GET', '/addresses/street', { country, city, street });
  }

  /** Address counts. GET /addresses/stats */
  async addressesStats(country) {
    const params = {};
    if (country) params.country = country;
    return this._request('GET', '/addresses/stats', params);
  }

  /** Random sample of addresses. GET /addresses/random */
  async addressesRandom(options = {}) {
    const params = { limit: options.limit || 1 };
    if (options.country) params.country = options.country;
    return this._request('GET', '/addresses/random', params);
  }

  /** Interpolate a coordinate from address-range data. GET /addresses/interpolate */
  async addressesInterpolate(country, city, street, houseNumber) {
    return this._request('GET', '/addresses/interpolate',
      { country, city, street, house_number: houseNumber });
  }

  /** Find the intersection of two streets. GET /addresses/crossstreet */
  async addressesCrossstreet(country, city, streetA, streetB) {
    return this._request('GET', '/addresses/crossstreet',
      { country, city, street_a: streetA, street_b: streetB });
  }

  // ─────────────────────────────────────────────────────────
  // Places
  // ─────────────────────────────────────────────────────────

  /** Search places (POIs). GET /places */
  async places(options = {}) {
    const params = {};
    if (options.q || options.query) params.q = options.q || options.query;
    if (options.country)            params.country = options.country;
    if (options.category)           params.category = options.category;
    if (options.limit)              params.limit = options.limit;
    return this._request('GET', '/places', params);
  }

  /** Places within radius of a coordinate. GET /places/nearby */
  async placesNearby(lat, lng, options = {}) {
    const params = { lat, lng, radius: options.radius || 200 };
    if (options.category) params.category = options.category;
    if (options.limit)    params.limit = options.limit;
    return this._request('GET', '/places/nearby', params);
  }

  /** List all place categories. GET /places/categories */
  async placesCategories() {
    return this._request('GET', '/places/categories');
  }

  /** Random places. GET /places/random */
  async placesRandom(options = {}) {
    const params = { limit: options.limit || 1 };
    if (options.country)  params.country = options.country;
    if (options.category) params.category = options.category;
    return this._request('GET', '/places/random', params);
  }

  /** Places counts. GET /places/stats */
  async placesStats(country) {
    const params = {};
    if (country) params.country = country;
    return this._request('GET', '/places/stats', params);
  }

  /** List brand-tagged places. GET /places/brands */
  async placesBrands(country) {
    const params = {};
    if (country) params.country = country;
    return this._request('GET', '/places/brands', params);
  }

  /** All locations of a brand/chain. GET /places/chain */
  async placesChain(brand, country) {
    const params = { brand };
    if (country) params.country = country;
    return this._request('GET', '/places/chain', params);
  }

  /** Count places matching filter. GET /places/count */
  async placesCount(options = {}) {
    const params = {};
    if (options.country)  params.country = options.country;
    if (options.category) params.category = options.category;
    return this._request('GET', '/places/count', params);
  }

  /** Places similar to a given one. GET /places/similar */
  async placesSimilar(placeId, options = {}) {
    const params = { id: placeId };
    if (options.limit) params.limit = options.limit;
    return this._request('GET', '/places/similar', params);
  }

  /** Batch nearby-places lookup. POST /places/batch */
  async placesBatch(coordinates, options = {}) {
    if (coordinates.length > 10000) throw new InvalidRequestError('Max 10,000 per batch');
    const body = { coordinates, radius: options.radius || 200 };
    if (options.category) body.category = options.category;
    return this._request('POST', '/places/batch', {}, body);
  }

  /** Single place by id. GET /places/{id} */
  async placeById(placeId) {
    return this._request('GET', `/places/${encodeURIComponent(placeId)}`);
  }

  // ─────────────────────────────────────────────────────────
  // Divisions (Sprint 1 — postcode boundary)
  // ─────────────────────────────────────────────────────────

  /** Search administrative divisions. GET /divisions */
  async divisionsSearch(options = {}) {
    const params = {};
    if (options.q || options.query) params.q = options.q || options.query;
    if (options.country)            params.country = options.country;
    if (options.subtype)            params.subtype = options.subtype;
    if (options.limit)              params.limit = options.limit;
    return this._request('GET', '/divisions', params);
  }

  /** Point-in-polygon: divisions containing a point. GET /divisions/contains */
  async divisionsContains(lat, lng) {
    return this._request('GET', '/divisions/contains', { lat, lng });
  }

  /**
   * Postcode → boundary (bbox + optional polygon + population + wikidata).
   * GET /divisions/by-postcode
   *
   * @param {string} code - Postcode (e.g. "90210", "SW1A 1AA")
   * @param {string} country - ISO 3166-1 alpha-2
   * @param {Object} [options]
   * @param {string} [options.include] - "geometry" to include polygon
   * @param {string} [options.precision] - "simplified" (default) or "full"
   *
   * @example
   *   const r = await client.divisionsByPostcode('90210', 'US', { include: 'geometry' });
   *   console.log(r.result.population, r.result.bbox);
   */
  async divisionsByPostcode(code, country, options = {}) {
    const params = { code, country };
    if (options.include)   params.include = options.include;
    if (options.precision) params.precision = options.precision;
    return this._request('GET', '/divisions/by-postcode', params);
  }

  /** List available division subtypes. GET /divisions/subtypes */
  async divisionsSubtypes() {
    return this._request('GET', '/divisions/subtypes');
  }

  /** List countries with division coverage. GET /divisions/countries */
  async divisionsCountries() {
    return this._request('GET', '/divisions/countries');
  }

  /** Division counts. GET /divisions/stats */
  async divisionsStats(country) {
    const params = {};
    if (country) params.country = country;
    return this._request('GET', '/divisions/stats', params);
  }

  /** Random divisions. GET /divisions/random */
  async divisionsRandom(options = {}) {
    const params = { limit: options.limit || 1 };
    if (options.country) params.country = options.country;
    if (options.subtype) params.subtype = options.subtype;
    return this._request('GET', '/divisions/random', params);
  }

  /** Full parent/child chain for a division. GET /divisions/hierarchy/{id} */
  async divisionHierarchy(divisionId) {
    return this._request('GET', `/divisions/hierarchy/${encodeURIComponent(divisionId)}`);
  }

  /** Single division by id. GET /divisions/{id} */
  async divisionById(divisionId) {
    return this._request('GET', `/divisions/${encodeURIComponent(divisionId)}`);
  }

  // ─────────────────────────────────────────────────────────
  // Coverage
  // ─────────────────────────────────────────────────────────

  /** Live tier-by-country coverage matrix. GET /coverage */
  async coverage() {
    return this._request('GET', '/coverage');
  }

  /** Aggregate coverage totals. GET /coverage-stats */
  async coverageStats() {
    return this._request('GET', '/coverage-stats');
  }

  // ─────────────────────────────────────────────────────────
  // Utilities
  // ─────────────────────────────────────────────────────────

  /** Timezone at a coordinate. GET /timezone */
  async timezone(lat, lng) {
    return this._request('GET', '/timezone', { lat, lng });
  }

  /** Great-circle distance between two coordinates. GET /distance */
  async distance(lat1, lng1, lat2, lng2) {
    return this._request('GET', '/distance', { lat1, lng1, lat2, lng2 });
  }

  /** Service health check. GET /health */
  async health() {
    return this._request('GET', '/health');
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
