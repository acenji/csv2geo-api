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

// ── Routing (Sprint 2.4) — Pro and Unlimited plans ────────────────────

export type RoutingMode = 'drive' | 'truck' | 'walk' | 'bike' | 'motorcycle';
export type RoutingFormat = 'geojson' | 'polyline' | 'both';

export interface RouteOptions {
  mode?: RoutingMode;
  lang?: string;
  units?: 'metric' | 'imperial';
  avoid?: string;
  alternatives?: 0 | 1 | 2 | 3;
  instructions?: boolean;
  departureTime?: string;
  truckHeight?: number;
  truckWeight?: number;
  truckLength?: number;
  truckWidth?: number;
  truckHazmat?: boolean;
  costingOptions?: string;
  format?: RoutingFormat;
}

export interface RouteSummary {
  distance_m: number;
  duration_s: number;
  has_toll?: boolean;
  has_ferry?: boolean;
  has_highway?: boolean;
}

export interface RouteLeg {
  from_waypoint_index: number;
  to_waypoint_index: number;
  distance_m: number;
  duration_s: number;
}

export interface RouteStep {
  distance_m: number;
  duration_s: number;
  instruction: string;
  maneuver: string;
  way_name?: string;
}

export interface RouteResult {
  mode: RoutingMode;
  summary: RouteSummary;
  geometry?: { type: 'LineString'; coordinates: number[][] };
  polyline?: string;
  polyline_precision?: number;
  legs?: RouteLeg[];
  steps?: RouteStep[];
}

export interface RouteResponse {
  results: RouteResult[];
  meta: { version: string; timestamp: string };
}

export interface IsolineArgs {
  lat: number;
  lng: number;
  mode: RoutingMode;
  ranges: number[] | string;
  type?: 'time' | 'distance';
  denoise?: number;
  format?: 'geojson';
}

export interface IsolineResult {
  range: number;
  geometry: { type: 'Polygon'; coordinates: number[][][] };
}

export interface IsolineResponse {
  query: { lat: number; lng: number; mode: string; type: string; ranges: number[] };
  results: IsolineResult[];
  meta: { version: string; timestamp: string };
}

export interface RouteMatrixArgs {
  sources: Array<Coordinate | [number, number]>;
  targets: Array<Coordinate | [number, number]>;
  mode: RoutingMode;
  units?: 'metric' | 'imperial';
  include?: Array<'distances' | 'durations'>;
  truckHeight?: number;
  truckWeight?: number;
  truckLength?: number;
  truckWidth?: number;
  truckHazmat?: boolean;
}

export interface RouteMatrixResponse {
  results: {
    distances_m?: (number | null)[][];
    durations_s?: (number | null)[][];
  };
  meta: { version: string; timestamp: string };
}

export interface MapMatchPoint {
  lat: number;
  lng: number;
  time?: string;
  accuracy_m?: number;
  accuracyM?: number;
}

export interface MapMatchArgs {
  trace: Array<MapMatchPoint | [number, number]>;
  mode: RoutingMode;
  gpsAccuracyM?: number;
  include?: string[];
}

export interface MapMatchResponse {
  results: {
    geometry: { type: 'LineString'; coordinates: number[][] };
    distance_m: number;
    duration_s: number;
    matched_points?: Array<{
      original_index: number;
      snapped_lat: number;
      snapped_lng: number;
      edge_id?: number;
    }>;
  };
  meta: { version: string; timestamp: string };
}

export interface OptimizeRouteOptions {
  mode?: RoutingMode;
  roundtrip?: boolean;
  lang?: string;
  units?: 'metric' | 'imperial';
  format?: RoutingFormat;
  truckHeight?: number;
  truckWeight?: number;
  truckLength?: number;
  truckWidth?: number;
  truckHazmat?: boolean;
}

export interface OptimizeRouteResponse {
  results: {
    optimal_order: number[];
    summary: { distance_m: number; duration_s: number };
    geometry?: { type: 'LineString'; coordinates: number[][] };
    polyline?: string;
    polyline_precision?: number;
    ordered_waypoints: Array<{ index: number; lat: number; lng: number }>;
  };
  meta: { version: string; timestamp: string };
}

export interface LocateOptions {
  mode?: RoutingMode;
  radiusM?: number;
}

export interface LocateResponse {
  query: { lat: number; lng: number; mode: string };
  result: {
    snapped_lat: number;
    snapped_lng: number;
    distance_m: number;
    edge?: {
      name?: string;
      way_id?: number;
      speed_limit_kmh?: number;
      surface?: string;
      road_class?: string;
      forward?: boolean;
    };
    heading?: number;
    side_of_street?: string;
  };
  meta: { version: string; timestamp: string };
}

export interface ElevationOptions {
  units?: 'metric' | 'imperial';
  format?: 'array' | 'geojson';
}

export interface ElevationResult {
  lat: number;
  lng: number;
  elevation_m?: number | null;
  elevation_ft?: number | null;
}

export interface ElevationResponse {
  results?: ElevationResult[];
  geometry?: { type: 'LineString'; coordinates: Array<[number, number, number | null]> };
  meta: { version: string; timestamp: string };
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

  // ── Routing (Sprint 2.4) — Pro and Unlimited plans only ──
  //
  // All seven routing methods require a Pro or Unlimited plan; Free/Growth
  // tier keys receive `plan_permission_denied` from the customer URL even
  // if the key has the `routing` permission flag set.

  /**
   * Point-to-point routing through 2-25 waypoints.
   * @param waypoints Array of [lat,lng] tuples OR pre-formatted "lat,lng|lat,lng" string
   * @param opts Optional parameters including mode, truck attrs, alternatives, etc.
   */
  route(
    waypoints: Array<[number, number]> | string,
    opts?: RouteOptions
  ): Promise<RouteResponse>;

  /**
   * Reachability polygon(s) for time or distance. Up to 3 ranges per call.
   */
  isoline(args: IsolineArgs): Promise<IsolineResponse>;

  /**
   * N×M distance/time matrix. Up to 10,000 cells total.
   */
  routeMatrix(args: RouteMatrixArgs): Promise<RouteMatrixResponse>;

  /**
   * Snap a GPS trace (2-1000 points) to the road network.
   */
  mapMatch(args: MapMatchArgs): Promise<MapMatchResponse>;

  /**
   * TSP-style stop ordering for up to 20 waypoints.
   */
  optimizeRoute(
    waypoints: Array<[number, number]> | string,
    opts?: OptimizeRouteOptions
  ): Promise<OptimizeRouteResponse>;

  /**
   * Snap a single point to the nearest road.
   */
  locate(
    lat: number,
    lng: number,
    opts?: LocateOptions
  ): Promise<LocateResponse>;

  /**
   * Per-point elevation. Up to 500 points per call.
   */
  elevation(
    points: Array<[number, number]> | string,
    opts?: ElevationOptions
  ): Promise<ElevationResponse>;

  // ─────────────────────────────────────────────────────────
  // Async batch wrapper (Sprint 2.5)
  // ─────────────────────────────────────────────────────────

  /**
   * Create an async batch job that fans `inputs` out across one wrapped endpoint.
   * Returns immediately with HTTP 202 and a job descriptor.
   */
  batchCreate(
    api: string,
    inputs: Array<{ id?: string; params: Record<string, unknown> }>,
    opts?: { params?: Record<string, unknown> }
  ): Promise<BatchCreateResponse>;

  /**
   * Poll a batch job by id. Returns 202-shaped body while the job is
   * pending or running; 200-shaped body (with `results`) when complete.
   * Pass `opts.compat = 'geoapify'` for the flat-array drop-in shape.
   */
  batchGet(
    jobId: string,
    opts?: { compat?: 'geoapify' }
  ): Promise<BatchGetResponse | BatchGeoapifyResult[]>;

  /** Cancel a pending or running batch job. */
  batchCancel(jobId: string): Promise<{ id: string; status: 'cancelled' }>;

  /**
   * Generate a marker pin PNG. Returns raw bytes (image/png).
   */
  icon(
    icon: string,
    opts?: {
      color?: string;
      size?: 'small' | 'medium' | 'large' | 'x-large';
      type?: 'awesome';
      noWhiteCircle?: boolean;
      scaleFactor?: 1 | 2 | 4;
    }
  ): Promise<Buffer>;

  /** List available marker icon names. */
  iconCatalog(): Promise<{ type: string; version: string; count: number; icons: string[] }>;

  /**
   * Poll batchGet() until the job terminates, then return the final body.
   * Convenience wrapper for callers that don't want their own poll loop.
   */
  batchWait(
    jobId: string,
    opts?: { pollIntervalMs?: number; timeoutMs?: number }
  ): Promise<BatchGetResponse>;
}

export interface BatchCreateResponse {
  id: string;
  status_url: string;
  status: 'pending';
  total_inputs: number;
  created_at: string;
}

export interface BatchResultEntry {
  input_id?: string;
  status: number;
  result?: unknown;
  error?: { code: string; message?: string };
  query?: Record<string, unknown>;
}

export interface BatchGetResponse {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  wrapped_endpoint: string;
  total_inputs: number;
  completed_inputs: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  results?: BatchResultEntry[];
  error?: { code: string; message?: string };
}

export interface BatchGeoapifyResult {
  id?: string;
  query?: Record<string, unknown>;
  result?: unknown;
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
