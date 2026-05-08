# csv2geo (Python SDK) — Changelog

All notable changes to the Python SDK are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the package is published to PyPI as [`csv2geo`](https://pypi.org/project/csv2geo/).

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
