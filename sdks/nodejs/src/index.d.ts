/**
 * CSV2GEO Node.js SDK Type Definitions
 */

export interface ClientOptions {
  /** API base URL (default: https://csv2geo.com/api/v1) */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Auto-retry on rate limit (default: true) */
  autoRetry?: boolean;
}

export interface GeocodeOptions {
  /** Limit to specific country (ISO 3166-1 alpha-2) */
  country?: string;
}

export interface AddressComponents {
  houseNumber?: string;
  street?: string;
  unit?: string;
  city?: string;
  state?: string;
  postcode?: string;
  country?: string;
}

export interface GeocodeResult {
  formattedAddress: string;
  lat: number;
  lng: number;
  accuracy: string;
  accuracyScore: number;
  components: AddressComponents;
}

export interface GeocodeResponse {
  query: string | { lat: number; lng: number };
  results: GeocodeResult[];
}

export interface Coordinate {
  lat: number;
  lng: number;
}

export class Client {
  /** Max requests per minute */
  rateLimit: string | null;
  /** Requests remaining in current window */
  rateLimitRemaining: string | null;
  /** Unix timestamp when limit resets */
  rateLimitReset: string | null;

  /**
   * Create a new CSV2GEO client
   * @param apiKey Your CSV2GEO API key
   * @param options Configuration options
   */
  constructor(apiKey: string, options?: ClientOptions);

  /**
   * Geocode a single address
   * @param address The address to geocode
   * @param options Options
   * @returns Best result or null if not found
   */
  geocode(address: string, options?: GeocodeOptions): Promise<GeocodeResult | null>;

  /**
   * Geocode with full response
   * @param address The address to geocode
   * @param options Options
   * @returns Full response with all results
   */
  geocodeFull(address: string, options?: GeocodeOptions): Promise<GeocodeResponse>;

  /**
   * Reverse geocode coordinates
   * @param lat Latitude
   * @param lng Longitude
   * @returns Best result or null if not found
   */
  reverse(lat: number, lng: number): Promise<GeocodeResult | null>;

  /**
   * Reverse geocode with full response
   * @param lat Latitude
   * @param lng Longitude
   * @returns Full response with all results
   */
  reverseFull(lat: number, lng: number): Promise<GeocodeResponse>;

  /**
   * Batch geocode multiple addresses
   * @param addresses Array of addresses (max 10,000)
   * @returns Array of responses
   */
  geocodeBatch(addresses: string[]): Promise<GeocodeResponse[]>;

  /**
   * Batch reverse geocode multiple coordinates
   * @param coordinates Array of coordinates (max 10,000)
   * @returns Array of responses
   */
  reverseBatch(coordinates: Coordinate[]): Promise<GeocodeResponse[]>;

  /**
   * IP geolocation. Returns country/region/city/postcode/location/timezone/ISP,
   * plus county + locality + confidence for residential IPs (Sprint 2.7).
   * @param ip IPv4 or IPv6 string
   */
  ip(ip: string): Promise<IPGeoResponse>;

  /**
   * Like {@link ip}, but uses the requester's IP.
   */
  ipMe(): Promise<IPGeoResponse>;

  /**
   * Batch IP lookup. Up to 1000 IPs per call.
   */
  ipBatch(ips: string[]): Promise<{ results: IPGeoResponse[] }>;
}

export interface IPGeoResponse {
  ip: string;
  country?: { code: string; name?: string; wikidata?: string };
  region?: { code?: string; name?: string };
  city?: { name: string };
  postcode?: string;
  location?: {
    latitude: number;
    longitude: number;
    accuracy_radius_km: number;
  };
  timezone?: string;
  isp?: { asn?: number; name?: string };
  county?: { name: string; subtype?: string; wikidata?: string };
  locality?: { name: string; subtype?: string; wikidata?: string };
  confidence?: 'high' | 'medium' | 'low';
  accuracy_disclaimer?: string;
  source: string;
  db_build_at?: string;
}

export class CSV2GEOError extends Error {
  code: string | null;
  status: number | null;
  constructor(message: string, code?: string | null, status?: number | null);
}

export class AuthenticationError extends CSV2GEOError {}

export class RateLimitError extends CSV2GEOError {
  retryAfter: number | null;
}

export class InvalidRequestError extends CSV2GEOError {}

export class PermissionError extends CSV2GEOError {}

export class APIError extends CSV2GEOError {}
