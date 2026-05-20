# csv2geo (Python SDK) — Changelog

All notable changes to the Python SDK are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the package is published to PyPI as [`csv2geo`](https://pypi.org/project/csv2geo/).

## [1.11.0] — 2026-05-20 — Vector map tiles (Sprint 3.0)

### Added — 4 vector tile methods

CSV2GEO now serves vector map tiles and ready-made MapLibre GL styles.

- `tile_url(z, x, y, source="planet")` — build the URL for a single vector tile (`.pbf`). Pure URL builder, makes no HTTP call. For wiring tiles into Leaflet/OpenLayers; MapLibre users want `style_url()` instead. Fetching a tile costs 0.25 credits.
- `style_url(name="csv2geo-bright")` — build the URL for a MapLibre style document; hand it straight to `maplibregl.Map({ style: ... })`. Pure URL builder. Free.
- `tile_styles()` — `GET /tile/styles`; lists the 3 available styles (`csv2geo-bright`, `positron`, `dark-matter`) with descriptions and preview URLs. Free.
- `tile_style(name="csv2geo-bright")` — `GET /tile/styles/{name}.json`; fetches a full MapLibre style document with the api_key and customer URL pre-substituted. Free.

Tiles are **vector** (Mapbox Vector Tile / `.pbf`) — there is no retina/`@2x` variant; pixel density is a client-side render concern.

## [1.8.1] — 2026-05-13 — UA-drift hotfix

### Fixed
- `Client` User-Agent header was hardcoded as `csv2geo-python/1.4.0` and
  stayed that way through every release from 1.5.0 onward. Now reads from
  the installed package metadata via `importlib.metadata.version("csv2geo")`,
  so any future version bump auto-updates the UA. CI's anti-drift test
  enforces this going forward. Customers using 1.8.0 are sending traffic
  identified as `csv2geo-python/1.4.0` until they upgrade — recommend
  `pip install -U csv2geo` to get accurate access-log attribution.

## [1.8.0] — 2026-05-13 — Routing API (Sprint 2.4)

### Added — 7 new routing methods (Pro and Unlimited plans only)

All seven methods proxy to a self-hosted Valhalla engine. They require the `routing` permission on the API key AND a Pro or Unlimited subscription. Free/Growth keys receive `403 plan_permission_denied`.

- `route(waypoints, mode, lang, units, avoid, alternatives, instructions, departure_time, truck_*, costing_options, format)` — turn-by-turn routing through 2-25 waypoints; supports time-aware routing (`departure_time`), up to 3 alternatives, and per-mode truck attributes (height, weight, length, width, hazmat).
- `isoline(lat, lng, mode, ranges, type, denoise, format)` — reachability polygon(s); 1-3 ranges per call, time (≤3600 s) or distance (≤50 000 m).
- `route_matrix(sources, targets, mode, units, include, truck_*)` — N×M distance/time matrix up to 10 000 cells.
- `map_match(trace, mode, gps_accuracy_m, include)` — snap GPS trace (2-1000 points) to the road network.
- `optimize_route(waypoints, mode, roundtrip, lang, units, format, truck_*)` — TSP-style stop ordering up to 20 waypoints.
- `locate(lat, lng, mode, radius_m)` — snap a single point to the nearest road; returns way_id, road class, surface, speed limit.
- `elevation(points, units, format)` — per-point elevation (Copernicus DEM tile install pending on geocoder; calls return `503 elevation_data_unavailable` until provisioned).

### Example

```python
from csv2geo import Client
client = Client("geo_live_...")

result = client.route(
    waypoints=[(40.7128, -74.006), (34.0522, -118.2437)],
    mode="drive",
    units="metric",
)
print(result["results"][0]["summary"])  # distance_m, duration_s, has_ferry, ...
```

## [1.6.0] — 2026-05-09 — Customer-URL gap closed + SDK signature corrections

### Fixed (the customer-URL gap — Sprint A)
- 22 SDK methods that previously 404'd from the default base URL
  (`https://csv2geo.com/api/v1`) now resolve correctly. The Laravel
  proxy at csv2geo.com gained matching routes for every Go service
  endpoint: `validate` (GET+POST), `parse` (GET+POST), `standardize`,
  `addresses_compare`, `addresses_nearby`, `addresses_street`,
  `addresses_stats`, `addresses_random`, `addresses_interpolate`,
  `addresses_crossstreet`, `divisions_search`, `division_contains`,
  `divisions_subtypes`, `divisions_countries`, `divisions_stats`,
  `divisions_random`, `division_hierarchy`, `division_by_id`,
  `timezone`, `distance`. All smoke-tested with a real `geo_live_*`
  key against `csv2geo.com/api/v1` per the API shipping protocol.
- `division_by_id(id)` now calls `/divisions/by-id/{id}` (customer URL,
  matches the same `by-id` nesting as `place_by_id`). Was calling the
  Go-internal `/divisions/{id}` which 404'd on customer URL.

### Changed (breaking — but methods were broken before, so no real impact)
- `addresses_interpolate(query, country='US')` — corrected signature.
  Previously took `(country, city, street, house_number)` which the Go
  service silently ignored. Now takes a single free-form `query` (parsed
  internally) plus optional `country`.
- `addresses_crossstreet(lat, lng, radius=100, country=None, city=None)`
  — corrected signature. Previously took `(country, city, street_a,
  street_b)` which was the wrong shape entirely. Now takes a coordinate
  and finds the nearest cross-street.

### Compatibility
- Customers still on 1.5.x: `place_by_id` is unchanged and works.
  Address tools and division extras start working as soon as you upgrade
  (they didn't work before regardless of version).
- Two breaking signature changes (`addresses_interpolate`,
  `addresses_crossstreet`) but those methods 404'd in 1.5.x and earlier
  so no production code depended on them.

## [1.5.1] — 2026-05-07 — Fix `place_by_id` customer URL path

### Fixed
- `place_by_id(place_id)` was calling `/places/{id}` (the Go service path) but the customer-facing Laravel proxy at `csv2geo.com/api/v1` nests this under `/places/by-id/{id}`. Returns now go through `/places/by-id/{id}` and resolve correctly. Pre-existing bug — present in 1.5.0 and earlier; affects every install that called `place_by_id` against the default base URL.
- Smoke-tested against `https://csv2geo.com/api/v1/places/by-id/{id}` with a real `geo_live_*` key before publish per the [API shipping protocol](https://github.com/csv2geo/overture-geocoder/blob/main/docs/API-SHIPPING-PROTOCOL.md).

### Compatibility
- Pure bug fix. No method signature change. All 1.5.0 callers benefit immediately.

## [1.5.0] — 2026-05-07 — Multi-language place names

### Added
- `lang=` keyword argument on all places methods that emit a `PlaceResult` — `places`, `places_nearby`, `places_random`, `places_chain`, `places_similar`, `places_batch`, and `place_by_id`. Same BCP-47 semantics as 1.4.0 divisions: `lang="ja"` swaps `name` for the Overture `names.rules` translation when present (e.g. `CoCo Ichibanya` → `CoCo壱番屋`, `Shell` → `شل`), with base-language fallback.
- `include_other_names=True` keyword (or `include="other_names"`) attaches the full translation map under `other_names` on each returned place. 234,440 places across 17 languages have a translation map today (sourced from Overture `names.rules`).

### Changed
- `User-Agent` header bumped to `csv2geo-python/1.5.0`.

### Compatibility
- Pure additive — all 1.4.0 callers work unchanged.

## [1.4.0] — 2026-05-07 — Multi-language division names

### Added
- `lang=` keyword argument on all four boundary methods (`divisions_by_postcode`, `division_ancestors`, `division_children`, `division_consolidated`). Pass a BCP-47 tag (`"de"`, `"ja"`, `"zh-Hant"`, `"pt-BR"`) and the `name` field on every returned division (and parent, and ancestors chain, and consolidated members) is replaced with the matching Overture `names.common[lang]` translation. Falls back to base language (`"pt"` for `"pt-BR"`) then to primary.
- `include="other_names"` (composable with other include flags via comma list, e.g. `include="geometry,other_names"`) — attaches the full `other_names` map (~78 langs avg for top-level divisions) to each returned division. Source: Overture `names.common`.

### Changed
- `User-Agent` header bumped to `csv2geo-python/1.4.0`.

### Compatibility
- Pure additive — all 1.3.0 callers work unchanged.

## [1.3.0] — 2026-05-12 — Boundaries API

### Added
- `Client.division_ancestors(division_id, include=None, precision=None, max_depth=None)` — walk-up "part-of" chain from input → parent → root. Each level includes name, subtype, country, region, population, Wikidata ID, parent_division_id; optional polygon per level when `include="geometry"`.
- `Client.division_children(division_id, include=None, precision=None, subtype=None, limit=None)` — immediate sub-divisions of a parent. Filterable by subtype (e.g. `"county"`, `"locality"`). Returns polygons inline when geometry is requested.
- `Client.division_consolidated(division_id, include=None, precision=None)` — resolves either a canonical or member id (e.g. any of NYC's 5 borough ids) into the canonical record + member list. Sourced from Wikidata P150.

### Changed
- `Client.division_hierarchy()` docstring updated to disambiguate — it returns CHILDREN, not ancestors. New `division_ancestors()` is the walk-up function. The old method is unchanged for backward compatibility.
- `User-Agent` header bumped to `csv2geo-python/1.3.0`.
- Package description now mentions "boundaries (postcode → polygon, ancestors walk-up, children walk-down, consolidated cities)".

### Compatibility
- All Sprint 1.8 features go through the existing `Client` — no breaking changes. Existing 1.2.0 callers can upgrade with no code changes.

## [1.2.0] — 2026-05-05 — IP Geolocation

### Added
- `Client.ip(ip)` — single IP geolocation lookup.
- `Client.ip_me()` — geolocate the requester.
- `Client.ip_batch(ips)` — up to 1000 IPs per call.

## [1.1.0] — 2026-05-02 — Postcode Boundary

### Added
- `Client.divisions_by_postcode(code, country, include=None, precision=None)` — postcode → boundary in one call.
- `Client.divisions_search`, `divisions_contains`, `divisions_subtypes`, `divisions_countries`, `divisions_stats`, `divisions_random`, `division_hierarchy`, `division_by_id` for the rest of the divisions surface.
- 11 places sub-endpoints: `places`, `places_nearby`, `place_by_id`, `places_categories`, `places_stats`, `places_brands`, `places_chain`, `places_count`, `places_similar`, `places_random`, `places_batch`.

## [1.0.0] — 2026-04-XX — Initial release

### Added
- Forward and reverse geocoding (single + batch).
- Address tools: validate, autocomplete, parse, standardize, compare.
- Address inspection: nearby, street, stats, random, interpolate, crossstreet.
- Coverage and utilities: timezone, distance, health.
- Auto-retry on 429 with exponential backoff, rate-limit header tracking, structured exceptions (`AuthenticationError`, `RateLimitError`, `InvalidRequestError`, `PermissionError`, `APIError`).
