# csv2geo-sdk (Node.js SDK) — Changelog

All notable changes to the Node SDK are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the package is published to npm as [`csv2geo-sdk`](https://www.npmjs.com/package/csv2geo-sdk).

## [1.11.0] — 2026-05-20 — Vector map tiles (Sprint 3.0)

### Added — 4 vector tile methods

CSV2GEO now serves vector map tiles and ready-made MapLibre GL styles.

- `tileURL(z, x, y, source = 'planet')` — build the URL for a single vector tile (`.pbf`). Pure URL builder, makes no HTTP call. For wiring tiles into Leaflet/OpenLayers; MapLibre users want `styleURL()` instead. Fetching a tile costs 0.25 credits.
- `styleURL(name = 'csv2geo-bright')` — build the URL for a MapLibre style document; pass straight to `new maplibregl.Map({ style: ... })`. Pure URL builder. Free.
- `tileStyles()` — `GET /tile/styles`; lists the 3 available styles (`csv2geo-bright`, `positron`, `dark-matter`) with descriptions and preview URLs. Free.
- `tileStyle(name = 'csv2geo-bright')` — `GET /tile/styles/{name}.json`; fetches a full MapLibre style document with the api_key and customer URL pre-substituted. Free.

New exported TypeScript types: `TileStyleName`, `TileStyleCatalogEntry`, `TileStylesResponse`.

Tiles are **vector** (Mapbox Vector Tile / `.pbf`) — there is no retina/`@2x` variant; pixel density is a client-side render concern.

## [1.8.1] — 2026-05-13 — UA-drift hotfix

### Fixed
- `Client` User-Agent header was hardcoded as `csv2geo-node/1.4.0` and
  stayed that way through every release from 1.5.0 onward. Now reads from
  `../package.json` at module load via
  `require('../package.json').version`, so any future bump auto-updates
  the UA. CI's anti-drift test enforces this going forward. Customers
  using 1.8.0 are sending traffic identified as `csv2geo-node/1.4.0`
  until they upgrade — recommend `npm install csv2geo-sdk@latest`.

## [1.8.0] — 2026-05-13 — Routing API (Sprint 2.4)

### Added — 7 new routing methods (Pro and Unlimited plans only)

All seven methods proxy to a self-hosted Valhalla engine. They require the `routing` permission on the API key AND a Pro or Unlimited subscription. Free/Growth keys receive `403 plan_permission_denied`.

- `route(waypoints, opts)` — turn-by-turn routing through 2-25 waypoints; supports time-aware routing (`departureTime`), up to 3 alternatives, and per-mode truck attributes (`truckHeight`, `truckWeight`, `truckLength`, `truckWidth`, `truckHazmat`).
- `isoline({ lat, lng, mode, ranges, type, denoise, format })` — reachability polygon(s); 1-3 ranges per call, time (≤3600 s) or distance (≤50 000 m).
- `routeMatrix({ sources, targets, mode, units, include, truck* })` — N×M distance/time matrix up to 10 000 cells.
- `mapMatch({ trace, mode, gpsAccuracyM, include })` — snap GPS trace (2-1000 points) to the road network.
- `optimizeRoute(waypoints, opts)` — TSP-style stop ordering up to 20 waypoints.
- `locate(lat, lng, opts)` — snap a single point to the nearest road; returns way_id, road class, surface, speed limit.
- `elevation(points, opts)` — per-point elevation (Copernicus DEM tile install pending on geocoder; calls return `503 elevation_data_unavailable` until provisioned).

### Added — TypeScript definitions

Full type coverage for all 7 methods in `src/index.d.ts`, including `RoutingMode`, `RouteOptions`, `RouteResponse`, `IsolineArgs`, `RouteMatrixArgs`/`RouteMatrixResponse`, `MapMatchArgs`/`MapMatchResponse`, `OptimizeRouteOptions`/`OptimizeRouteResponse`, `LocateOptions`/`LocateResponse`, `ElevationOptions`/`ElevationResponse`.

### Example

```javascript
const { Client } = require('csv2geo-sdk');
const client = new Client('geo_live_...');

const result = await client.route(
  [[40.7128, -74.006], [34.0522, -118.2437]],
  { mode: 'drive', units: 'metric' }
);
console.log(result.results[0].summary);  // distance_m, duration_s, has_ferry, ...
```

## [1.6.0] — 2026-05-09 — Customer-URL gap closed + SDK signature corrections

### Fixed (the customer-URL gap — Sprint A)
- 22 SDK methods that previously 404'd from the default base URL
  (`https://csv2geo.com/api/v1`) now resolve correctly. The Laravel
  proxy at csv2geo.com gained matching routes for every Go service
  endpoint: `validate` (GET+POST), `parse` (GET+POST), `standardize`,
  `addressesCompare`, `addressesNearby`, `addressesStreet`,
  `addressesStats`, `addressesRandom`, `addressesInterpolate`,
  `addressesCrossstreet`, `divisionsSearch`, `divisionContains`,
  `divisionsSubtypes`, `divisionsCountries`, `divisionsStats`,
  `divisionsRandom`, `divisionHierarchy`, `divisionById`,
  `timezone`, `distance`. All smoke-tested with a real `geo_live_*`
  key against `csv2geo.com/api/v1` per the API shipping protocol.
- `divisionById(id)` now calls `/divisions/by-id/{id}` (customer URL,
  matches the same `by-id` nesting as `placeById`). Was calling the
  Go-internal `/divisions/{id}` which 404'd on customer URL.

### Changed (breaking — but methods were broken before, so no real impact)
- `addressesInterpolate(query, country = 'US')` — corrected signature.
  Previously took `(country, city, street, houseNumber)` which the Go
  service silently ignored. Now takes a single free-form `query` (parsed
  internally) plus optional `country`.
- `addressesCrossstreet(lat, lng, options = {})` — corrected signature.
  Previously took `(country, city, streetA, streetB)` which was the
  wrong shape entirely. Now takes a coordinate; options accepts
  `{ radius, country, city }`.

### Compatibility
- Customers still on 1.5.x: `placeById` is unchanged and works.
  Address tools and division extras start working as soon as you upgrade
  (they didn't work before regardless of version).
- Two breaking signature changes (`addressesInterpolate`,
  `addressesCrossstreet`) but those methods 404'd in 1.5.x and earlier
  so no production code depended on them.

## [1.5.1] — 2026-05-07 — Fix `placeById` customer URL path

### Fixed
- `placeById(placeId)` was calling `/places/{id}` (the Go service path) but the customer-facing Laravel proxy at `csv2geo.com/api/v1` nests this under `/places/by-id/{id}`. Returns now go through `/places/by-id/{id}` and resolve correctly. Pre-existing bug — present in 1.5.0 and earlier; affects every install that called `placeById` against the default base URL.
- Smoke-tested against `https://csv2geo.com/api/v1/places/by-id/{id}` with a real `geo_live_*` key before publish per the [API shipping protocol](https://github.com/csv2geo/overture-geocoder/blob/main/docs/API-SHIPPING-PROTOCOL.md).

### Compatibility
- Pure bug fix. No method signature change. All 1.5.0 callers benefit immediately.

## [1.5.0] — 2026-05-07 — Multi-language place names

### Added
- `lang` option on all places methods that emit a `PlaceResult` — `places`, `placesNearby`, `placesRandom`, `placesChain`, `placesSimilar`, `placesBatch`, and `placeById`. Same BCP-47 semantics as 1.4.0 divisions: `{lang: 'ja'}` swaps `name` for the Overture `names.rules` translation when present (e.g. `CoCo Ichibanya` → `CoCo壱番屋`, `Shell` → `شل`), with base-language fallback.
- `includeOtherNames: true` option (or `include: 'other_names'`) attaches the full translation map under `other_names` on each returned place. 234,440 places across 17 languages have a translation map today (sourced from Overture `names.rules`).

### Compatibility
- Pure additive — all 1.4.0 callers work unchanged.

## [1.4.0] — 2026-05-07 — Multi-language division names

### Added
- `lang` option on all four boundary methods (`divisionsByPostcode`, `divisionAncestors`, `divisionChildren`, `divisionConsolidated`). Pass a BCP-47 tag (`'de'`, `'ja'`, `'zh-Hant'`, `'pt-BR'`) and the `name` field on every returned division is replaced with the Overture `names.common[lang]` translation. Falls back to base language (`'pt'` for `'pt-BR'`) then to primary.
- `include: 'other_names'` (composable, e.g. `include: 'geometry,other_names'`) — attaches the full `other_names` map (~78 langs avg for top-level divisions). Source: Overture `names.common`.

### Changed
- `User-Agent` header bumped to `csv2geo-node/1.4.0`.

### Compatibility
- Pure additive — all 1.3.0 callers work unchanged.

## [1.3.0] — 2026-05-12 — Boundaries API

### Added
- `client.divisionAncestors(divisionId, options?)` — walk-up "part-of" chain. Options: `{ include, precision, maxDepth }`. Each level returns name, subtype, country, region, population, Wikidata, `parent_division_id`; optional polygon per level when `include: 'geometry'`.
- `client.divisionChildren(divisionId, options?)` — immediate sub-divisions. Options: `{ include, precision, subtype, limit }`. Polygons inline when geometry requested.
- `client.divisionConsolidated(divisionId, options?)` — resolves canonical OR member id into the canonical record + members. Options: `{ include, precision }`.
- JSDoc `@param`/`@returns`/`@example` annotations on all 3 new methods (TypeScript users get inferred types via `allowJs`).

### Changed
- `client.divisionHierarchy()` JSDoc clarified — it returns CHILDREN (not ancestors). New `divisionAncestors()` is the walk-up function. Old method is unchanged for backward compatibility.
- `User-Agent` header bumped to `csv2geo-node/1.3.0`.
- Package description now mentions "boundaries (postcode → polygon, ancestors walk-up, children walk-down, consolidated cities)".

### Compatibility
- All Sprint 1.8 features go through the existing `Client` — no breaking changes. Existing 1.2.0 callers can upgrade with no code changes.

## [1.2.0] — 2026-05-05 — IP Geolocation

### Added
- `client.ip(ip)` — single IP geolocation lookup.
- `client.ipMe()` — geolocate the requester.
- `client.ipBatch(ips)` — up to 1000 IPs per call.

## [1.1.0] — 2026-05-02 — Postcode Boundary

### Added
- `client.divisionsByPostcode(code, country, options?)` — postcode → boundary in one call.
- `client.divisionsSearch`, `divisionsContains`, `divisionsSubtypes`, `divisionsCountries`, `divisionsStats`, `divisionsRandom`, `divisionHierarchy`, `divisionById`.
- Places sub-endpoints: `places`, `placesNearby`, `placeById`, `placesCategories`, `placesStats`, `placesBrands`, `placesChain`, `placesCount`, `placesSimilar`, `placesRandom`, `placesBatch`.

## [1.0.0] — 2026-04-XX — Initial release

### Added
- Forward and reverse geocoding (single + batch).
- Address tools: validate, autocomplete, parse, standardize, compare.
- Address inspection: nearby, street, stats, random, interpolate, crossstreet.
- Coverage and utilities: timezone, distance, health.
- Auto-retry on 429, rate-limit header tracking, structured error classes (`AuthenticationError`, `RateLimitError`, `InvalidRequestError`, `PermissionError`, `ApiError`).
