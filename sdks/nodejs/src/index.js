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

const DEFAULT_BASE_URL = 'https://csv2geo.com/api/v1';
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
          'User-Agent': 'csv2geo-node/1.4.0',
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
    this._mergeI18n(params, options);  // lang / include / includeOtherNames

    const data = await this._request('GET', '/geocode', params);
    const results = data.results || [];
    return results.length > 0 ? this._parseResult(results[0]) : null;
  }

  /**
   * Geocode with full response
   * @param {string} address - The address to geocode
   * @param {Object} [options] - Options { country, lang, include, includeOtherNames }
   * @returns {Promise<GeocodeResponse>} Full response with all results
   */
  async geocodeFull(address, options = {}) {
    const params = { q: address };
    if (options.country) params.country = options.country;
    this._mergeI18n(params, options);

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
   * @param {Object} [options] - Options { lang, include, includeOtherNames }
   * @returns {Promise<GeocodeResult|null>} Best result or null if not found
   *
   * @example
   * const result = await client.reverse(48.2082, 16.3738, { lang: 'de', includeOtherNames: true });
   * // result.components.country === 'Österreich'
   * // result.other_names.country.fr === 'Autriche'
   */
  async reverse(lat, lng, options = {}) {
    const params = { lat, lng };
    this._mergeI18n(params, options);
    const data = await this._request('GET', '/reverse', params);
    const results = data.results || [];
    return results.length > 0 ? this._parseResult(results[0]) : null;
  }

  /**
   * Reverse geocode with full response
   * @param {number} lat - Latitude
   * @param {number} lng - Longitude
   * @param {Object} [options] - Options { lang, include, includeOtherNames }
   * @returns {Promise<GeocodeResponse>} Full response with all results
   */
  async reverseFull(lat, lng, options = {}) {
    const params = { lat, lng };
    this._mergeI18n(params, options);
    const data = await this._request('GET', '/reverse', params);
    return {
      query: data.query,
      results: (data.results || []).map(r => this._parseResult(r)),
    };
  }

  /**
   * Batch geocode multiple addresses
   * @param {string[]} addresses - Array of addresses (max 10,000)
   * @param {Object} [options] - Options { lang, include, includeOtherNames }
   * @returns {Promise<GeocodeResponse[]>} Array of responses
   *
   * @example
   * const results = await client.geocodeBatch(
   *   ['1600 Pennsylvania Ave NW Washington DC', 'Champs-Élysées Paris'],
   *   { lang: 'de', includeOtherNames: true }
   * );
   */
  async geocodeBatch(addresses, options = {}) {
    if (addresses.length > 10000) {
      throw new InvalidRequestError('Maximum 10,000 addresses per batch request');
    }

    const params = {};
    this._mergeI18n(params, options);
    const data = await this._request('POST', '/geocode', params, { addresses });
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
  async reverseBatch(coordinates, options = {}) {
    if (coordinates.length > 10000) {
      throw new InvalidRequestError('Maximum 10,000 coordinates per batch request');
    }

    const params = {};
    this._mergeI18n(params, options);
    const data = await this._request('POST', '/reverse', params, { coordinates });
    return (data.results || []).map(r => ({
      query: r.query,
      results: (r.results || []).map(res => this._parseResult(res)),
    }));
  }

  /**
   * Internal: merge ?lang= / ?include= / ?include=other_names from options
   * into a params object. Called by every geocode/reverse method.
   */
  _mergeI18n(params, options) {
    if (options.lang) params.lang = options.lang;
    if (options.include) {
      params.include = options.include;
    } else if (options.includeOtherNames) {
      params.include = 'other_names';
    }
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

  /** Interpolate a coordinate from address-range data. GET /addresses/interpolate
   *  Go takes a single free-form `q` (parsed internally) +
   *  optional `country`. SDK 1.6.0 fixed the previous (country, city, street,
   *  houseNumber) signature which was silently ignored by the Go service. */
  async addressesInterpolate(query, country = 'US') {
    return this._request('GET', '/addresses/interpolate', { q: query, country });
  }

  /** Find the cross-street nearest to a coordinate. GET /addresses/crossstreet
   *  Go takes (lat, lng) and finds nearest intersecting streets. SDK 1.6.0
   *  fixed the previous (country, city, streetA, streetB) signature — wrong
   *  shape entirely. */
  async addressesCrossstreet(lat, lng, options = {}) {
    const params = { lat, lng };
    if (options.radius)  params.radius  = options.radius;
    if (options.country) params.country = options.country;
    if (options.city)    params.city    = options.city;
    return this._request('GET', '/addresses/crossstreet', params);
  }

  // ─────────────────────────────────────────────────────────
  // Places
  // ─────────────────────────────────────────────────────────

  /** Search places (POIs). GET /places
   *  options: { q, country, category, limit, lang, includeOtherNames, include } */
  async places(options = {}) {
    const params = {};
    if (options.q || options.query) params.q = options.q || options.query;
    if (options.country)            params.country = options.country;
    if (options.category)           params.category = options.category;
    if (options.limit)              params.limit = options.limit;
    this._mergePlacesI18n(params, options);
    return this._request('GET', '/places', params);
  }

  /** Places within radius of a coordinate. GET /places/nearby
   *  options: { radius, category, limit, lang, includeOtherNames, include } */
  async placesNearby(lat, lng, options = {}) {
    const params = { lat, lng, radius: options.radius || 200 };
    if (options.category) params.category = options.category;
    if (options.limit)    params.limit = options.limit;
    this._mergePlacesI18n(params, options);
    return this._request('GET', '/places/nearby', params);
  }

  /** List all place categories. GET /places/categories */
  async placesCategories() {
    return this._request('GET', '/places/categories');
  }

  /** Random places. GET /places/random
   *  options: { country, category, limit, lang, includeOtherNames, include } */
  async placesRandom(options = {}) {
    const params = { limit: options.limit || 1 };
    if (options.country)  params.country = options.country;
    if (options.category) params.category = options.category;
    this._mergePlacesI18n(params, options);
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

  /** All locations of a brand/chain. GET /places/chain
   *  options: { country, lang, includeOtherNames, include } */
  async placesChain(brand, country, options = {}) {
    const params = { brand };
    if (country) params.country = country;
    this._mergePlacesI18n(params, options);
    return this._request('GET', '/places/chain', params);
  }

  /** Count places matching filter. GET /places/count */
  async placesCount(options = {}) {
    const params = {};
    if (options.country)  params.country = options.country;
    if (options.category) params.category = options.category;
    return this._request('GET', '/places/count', params);
  }

  /** Places similar to a given one. GET /places/similar
   *  options: { limit, lang, includeOtherNames, include } */
  async placesSimilar(placeId, options = {}) {
    const params = { id: placeId };
    if (options.limit) params.limit = options.limit;
    this._mergePlacesI18n(params, options);
    return this._request('GET', '/places/similar', params);
  }

  /** Batch nearby-places lookup. POST /places/batch
   *  options: { radius, category, lang, includeOtherNames, include } */
  async placesBatch(coordinates, options = {}) {
    if (coordinates.length > 10000) throw new InvalidRequestError('Max 10,000 per batch');
    const body = { coordinates, radius: options.radius || 200 };
    if (options.category) body.category = options.category;
    // lang / include are forwarded via query string (not body)
    const queryParams = {};
    this._mergePlacesI18n(queryParams, options);
    return this._request('POST', '/places/batch', queryParams, body);
  }

  /** Single place by id. GET /places/by-id/{id} (customer URL).
   *  The customer-facing Laravel proxy nests this under /places/by-id/{id}
   *  even though the underlying Go service uses /places/{id} — SDK MUST
   *  target the customer path. (Bug fix 1.5.1; was broken in 1.5.0 and
   *  earlier.)
   *  options: { lang, includeOtherNames, include } */
  async placeById(placeId, options = {}) {
    const params = {};
    this._mergePlacesI18n(params, options);
    return this._request('GET', `/places/by-id/${encodeURIComponent(placeId)}`, params);
  }

  /** Internal: merge ?lang= and ?include=other_names options into params.
   *  Sprint 2.1b — translations on places (234K places, 17 langs from Overture). */
  _mergePlacesI18n(params, options) {
    if (options.lang) params.lang = options.lang;
    if (options.include) {
      params.include = options.include;
    } else if (options.includeOtherNames) {
      params.include = 'other_names';
    }
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
    if (options.lang)      params.lang = options.lang;
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

  /**
   * Children of a division (immediate sub-divisions). GET /divisions/hierarchy/{id}
   *
   * Note: returns CHILDREN, not ancestors. For walk-UP "part-of" chain, use
   * `divisionAncestors()`. Kept under the original name for backward compatibility.
   */
  async divisionHierarchy(divisionId) {
    return this._request('GET', `/divisions/hierarchy/${encodeURIComponent(divisionId)}`);
  }

  /** Single division by id. GET /divisions/by-id/{id} (customer URL).
   *  Customer Laravel proxy nests this under /by-id/{id} — same naming
   *  pattern as /places/by-id/{id} (matches the customer URL truth, not
   *  the Go-internal flatter /divisions/{id} path). SDK 1.6.0 corrected
   *  this; was 404'ing in 1.5.x.
   *  options: { lang, include, precision } */
  async divisionById(divisionId, options = {}) {
    const params = {};
    if (options.lang)      params.lang      = options.lang;
    if (options.include)   params.include   = options.include;
    if (options.precision) params.precision = options.precision;
    return this._request('GET', `/divisions/by-id/${encodeURIComponent(divisionId)}`, params);
  }

  // ─────────────────────────────────────────────────────────
  // Boundaries (Sprint 1.8)
  // ─────────────────────────────────────────────────────────

  /**
   * Walk-up "part-of" chain: input → parent → root.
   * GET /divisions/ancestors/{id}
   *
   * @param {string} divisionId - Overture ID of the leaf division.
   * @param {object} [options]
   * @param {string} [options.include] - "geometry" to include each level's polygon.
   * @param {string} [options.precision] - "low" | "med" (default) | "full".
   * @param {number} [options.maxDepth] - Hard cap (default 8, max 12).
   * @returns {Promise<{id: string, depth: number, results: object[]}>}
   *
   * @example
   *   const chain = await client.divisionAncestors(beverlyHillsId, { include: 'geometry' });
   *   chain.results.forEach(level => console.log(level.subtype, level.name));
   */
  async divisionAncestors(divisionId, options = {}) {
    const params = {};
    if (options.include)   params.include   = options.include;
    if (options.precision) params.precision = options.precision;
    if (options.maxDepth)  params.max_depth = options.maxDepth;
    if (options.lang)      params.lang      = options.lang;
    return this._request('GET', `/divisions/ancestors/${encodeURIComponent(divisionId)}`, params);
  }

  /**
   * Immediate sub-divisions of a division (clearer-named alias of
   * divisionHierarchy plus optional polygon enrichment).
   * GET /divisions/children/{id}
   *
   * @param {string} divisionId
   * @param {object} [options]
   * @param {string} [options.include]   - "geometry" to include polygons.
   * @param {string} [options.precision] - "low" | "med" (default) | "full".
   * @param {string} [options.subtype]   - Filter by admin subtype.
   * @param {number} [options.limit]     - Max children (default 100, max 500).
   */
  async divisionChildren(divisionId, options = {}) {
    const params = {};
    if (options.include)   params.include   = options.include;
    if (options.precision) params.precision = options.precision;
    if (options.subtype)   params.subtype   = options.subtype;
    if (options.limit)     params.limit     = options.limit;
    if (options.lang)      params.lang      = options.lang;
    return this._request('GET', `/divisions/children/${encodeURIComponent(divisionId)}`, params);
  }

  /**
   * Consolidated entity lookup. Resolves canonical OR member id — e.g. any of
   * NYC's 5 borough ids returns the canonical "New York City" record + members.
   * GET /divisions/consolidated/{id}
   *
   * @param {string} divisionId
   * @param {object} [options]
   * @param {string} [options.include]   - "geometry" for canonical's outline.
   * @param {string} [options.precision] - "low" | "med" (default) | "full".
   * @returns {Promise<{canonical: object, members: object[], matched_as: string, source: string}>}
   *
   * @throws ApiError(404) when the id is not part of any consolidated entity.
   */
  async divisionConsolidated(divisionId, options = {}) {
    const params = {};
    if (options.include)   params.include   = options.include;
    if (options.precision) params.precision = options.precision;
    if (options.lang)      params.lang      = options.lang;
    return this._request('GET', `/divisions/consolidated/${encodeURIComponent(divisionId)}`, params);
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
      // Sprint 2.1d — pass-through per-admin-level translation maps when
      // ?include=other_names. Empty object if not requested.
      other_names: data.other_names || {},
    };
  }

  // ─────────────────────────────────────────────────────────
  // IP geolocation (Sprint 2.7)
  //
  // MaxMind GeoLite2 .mmdb lookup with our county overlay.
  // Bundled into every plan (including Free); no separate billing.
  // ─────────────────────────────────────────────────────────

  /**
   * IP → geolocation. Returns country, region, city, postcode, location,
   * timezone, ISP, and (for residential IPs) county + locality + confidence.
   *
   * @param {string} ip - IPv4 or IPv6 address (e.g. "8.8.8.8")
   * @returns {Promise<Object>} canonical /v1/ip response shape
   * @example
   *   const r = await client.ip('8.8.8.8');
   *   console.log(r.country.code, r.county?.name, r.confidence);
   */
  async ip(ip) {
    if (!ip || typeof ip !== 'string') {
      throw new InvalidRequestError('ip must be a non-empty string');
    }
    return this._request('GET', '/ip', { ip });
  }

  /**
   * Like {@link ip}, but uses the requester's IP (the one Laravel sees).
   * Useful from browser/server contexts where you want "where is the caller".
   *
   * @returns {Promise<Object>} canonical /v1/ip response shape
   */
  async ipMe() {
    return this._request('GET', '/ip/me');
  }

  /**
   * Batch IP lookup. Up to 1000 IPs per call.
   *
   * @param {string[]} ips - array of IPs
   * @returns {Promise<{results: Object[]}>}
   */
  async ipBatch(ips) {
    if (!Array.isArray(ips) || ips.length === 0) {
      throw new InvalidRequestError('ips must be a non-empty array');
    }
    if (ips.length > 1000) {
      throw new InvalidRequestError('ipBatch supports at most 1000 IPs per call');
    }
    return this._request('POST', '/ip/batch', {}, { ips });
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
