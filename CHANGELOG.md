# Changelog

All notable changes to the CSV2GEO API are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The CSV2GEO API service is versioned by URL path (`/v1/…`); this file tracks new endpoints, response-shape additions, and breaking changes.

## [Sprint 2.5] — 2026-05-13 — Async batch wrapper

### Added
- `POST /v1/batch` — create an async batch job that fans `inputs` out across one wrapped endpoint. Returns HTTP 202 + `{id, status_url, status, total_inputs, created_at}`. Body: `{api: "/v1/<endpoint>", params: {...shared...}, inputs: [{id?, params}]}`. The `api` field can also be passed as a query parameter for Geoapify drop-in compatibility.
- `GET /v1/batch/{id}` — poll the job. Returns 202 while pending/running, 200 + `{...counters, results: [{input_id, status, result|error, query}]}` when terminal (completed/failed/cancelled). Pass `?compat=geoapify` to flip the completed response to the flat-array shape Geoapify ships.
- `DELETE /v1/batch/{id}` — cancel a pending or running job. Returns 404 if the job is already in a terminal state.
- Wraps 16 single-shot endpoints: `geocode`, `reverse`, `autocomplete`, `validate`, `parse`, `standardize`, `postcode`, `places`, `places/nearby`, `divisions/by-postcode`, `divisions/contains`, `ip`, `routing`, `isoline`, `locate`, `elevation`. Permission required on the API key is the same as the wrapped endpoint (e.g., `routing` for `/v1/batch?api=routing`).
- Per-batch input cap: 5,000 (Free), 50,000 (Starter/Growth/Pro), 1,000,000 (Enterprise). Per-key concurrent jobs cap: 3 / 20 / 100. Job results retained 24 h after terminal state, then auto-purged.
- **Python SDK 1.9.0** — `client.batch_create(api, inputs, params=)`, `client.batch_get(job_id, compat=)`, `client.batch_cancel(job_id)`, `client.batch_wait(job_id, poll_interval=, timeout=)`. The `_handle_response` helper now treats any 2xx as success so callers see the 202 body on create + poll.
- **Node SDK 1.9.0** — `client.batchCreate(api, inputs, opts)`, `client.batchGet(jobId, opts)`, `client.batchCancel(jobId)`, `client.batchWait(jobId, opts)`. Full TypeScript declarations included.

### Why
This was the last 🟡 in our internal Geoapify parity grid (§7 row "Async batch wrapper"). Customers running ≥100K-row offline jobs from CDN/Lambda/CI environments where a 60-second sync HTTP request times out can now use the async flow; SDKs running on `geoapify-python` can repoint base URL and have their existing `batch.create() → poll → results` code work via `?compat=geoapify`.

## [Sprint 1.8] — 2026-05-12 — Boundaries API

### Added
- `GET /v1/divisions/ancestors/{id}` — walks `parent_division_id` from the input UP to the root and returns the ordered chain (input → parent → grandparent → … → country). Cycle detection + `max_depth` cap (default 8, max 12). The "part-of" hierarchy walk in one call.
- `GET /v1/divisions/children/{id}` — clearer-named alias for `/v1/divisions/hierarchy/{id}`. Supports `?include=geometry&precision=…` to inline polygons per child (the Hierarchy alias does not — kept for backward compatibility).
- `GET /v1/divisions/consolidated/{id}` — resolves either a canonical or member id (e.g. any of NYC's 5 borough ids returns the canonical "New York City" record + members). Curated from Wikidata P150.
- `?precision=low|med|full` on every polygon-returning endpoint (`/v1/divisions/by-postcode`, `/v1/divisions/ancestors`, `/v1/divisions/children`, `/v1/divisions/consolidated`). low ≈ 1KB / med ≈ 10KB / full = source resolution. Default = med. Graceful fallback to coarser tier when simplified fields aren't backfilled.
- New MongoDB collection `consolidated_aliases` populated by `scripts/build-consolidated-aliases/build.mjs` (Wikidata SPARQL — 30 well-known consolidated entities globally; extensible by editing the seed list).
- Geoapify drop-in compatibility shim:
  - Request: `text` accepted as alias for `q` on `/v1/geocode` and `/v1/autocomplete`.
  - Request: `lon` accepted as alias for `lng` on `/v1/reverse`.
  - Response: every `GeocodeResult` now includes flat `lat`+`lon` (alongside the canonical nested `location.{lat,lng}`) and `formatted` (alias of `formatted_address`).
  - Response: address `components` block now includes `country_code`, `state_code`, `district`, `suburb`, and `iso3166_2` (auto-computed when both country+state codes present).

### Changed
- `/v1/divisions/hierarchy/{id}` documentation clarified — it returns CHILDREN (entries with `parent_division_id == :id`), not the full bidirectional tree. Naming was confusing; aliased as `/v1/divisions/children/{id}` going forward. Backward-compatible.
- OpenAPI spec at `openapi.yaml` updated with all new paths, params, and response schemas.
- llms.txt updated with new endpoint lines + capability bullets for AI crawlers.

### SDKs
- Python SDK 1.3.0 on PyPI: new methods `division_ancestors`, `division_children`, `division_consolidated` with `include` / `precision` / `max_depth` / `subtype` / `limit` kwargs.
- Node SDK 1.3.0 on npm: equivalent methods (`divisionAncestors`, `divisionChildren`, `divisionConsolidated`) with options-object pattern.

### Performance targets (asserted in `tests/boundaries_bench_test.go`)
| Endpoint | p50 | p95 |
|---|---|---|
| /divisions/by-postcode (no geometry) | 25 ms | 80 ms |
| /divisions/by-postcode (precision=med) | 60 ms | 150 ms |
| /divisions/by-postcode (precision=full) | 100 ms | 250 ms |
| /divisions/ancestors (geometry+med, 5-level) | 80 ms | 200 ms |
| /divisions/children (no geometry) | 50 ms | 120 ms |
| /divisions/consolidated (no geometry) | 40 ms | 100 ms |

## [Sprint 2.7] — 2026-05-05 — IP Geolocation

### Added
- `GET /v1/ip` — IP address → country / region / city / county / ASN with confidence labels.
- `GET /v1/ip/me` — geolocate the requester (X-Forwarded-For aware).
- `POST /v1/ip/batch` — up to 1000 IPs per call.

Bundled into every plan (including Free); no separate SKU.

## [Sprint 1] — 2026-04-30 — Postcode Boundary

### Added
- `GET /v1/divisions/by-postcode?code=…&country=…[&include=geometry][&precision=…]` — one-call postcode → boundary (bbox + optional polygon + population + Wikidata).
- New MongoDB collection `postcode_divisions` populated by `api/scripts/build-postcode-resolver`.
- UK Code-Point integration (1.74M postcodes).

## Earlier history

For changes prior to Sprint 1, see git history. The first public version of the API shipped in Sprint 0 (early 2026) with `/v1/geocode`, `/v1/reverse`, `/v1/places` family, `/v1/divisions`, `/v1/autocomplete`, and `/v1/coverage`.
