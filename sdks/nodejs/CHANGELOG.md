# csv2geo-sdk (Node.js SDK) — Changelog

All notable changes to the Node SDK are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the package is published to npm as [`csv2geo-sdk`](https://www.npmjs.com/package/csv2geo-sdk).

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
