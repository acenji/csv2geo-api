# Changelog

All notable changes to the CSV2GEO API are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The CSV2GEO API service is versioned by URL path (`/v1/…`); this file tracks new endpoints, response-shape additions, and breaking changes.

## [Sprint ele-on-places] — 2026-05-24 — Inline `ele` on Places (`?include=elevation`)

### Added
- `GET /v1/places`, `/v1/places/nearby`, `/v1/places/by-id/{id}`, `/v1/places/random`, `/v1/places/chain`, `/v1/places/batch`, `/v1/places/similar` accept `?include=elevation`. When set, each Place result gains an `ele` field (metres above sea level). Composable with the existing `?include=other_names` — pass `?include=other_names,elevation` to get both.
- Source: Valhalla `/height` against a global Tilezen 30 m DEM. Loaded onto both Seattle (primary) and arbnode (HA backup) — arbnode previously had ZERO elevation tiles, so this ship also closes a pre-existing HA gap on `/v1/elevation` itself.
- **One batched Valhalla call per result page**, not N per result. Valhalla caps `/height` at 500 points; a Places page is far smaller, so the extra cost is one internal round-trip rather than per-result.
- **Fail-soft:** if Valhalla is unavailable, the Places response still returns 200 — `ele` is simply omitted from each result. Customer never sees a 5xx because elevation enrichment failed.
- **Opt-in by design:** no per-call cost when callers don't pass `?include=elevation`. The Places handler skips the Valhalla round-trip entirely.
- `ele` returns `null` for any coordinate whose DEM tile isn't on the serving node — distinct from a real 0 m elevation. (Real 0 m is encoded as the integer 0.)

### Closed last Geoapify field-level parity gap
- `geoapify-vs-csv2geo-comparison.md` §2 `ele` row flipped ❌→✅.
- Headline count moves to 74 ✅.
- The only remaining ❌ items are the satellite tile **basemap** (Sprint 3.0.5, gated on storage expansion — per-address aerial is shipped via `/v1/property/image`) and the two deliberate Geometry-API skips.

### Python SDK 1.16.0
- No new method or kwarg — `?include=elevation` flows through the existing `include="..."` string. Tests `tests/test_places_elevation.py` (7 cases) lock the wire contract: a customer passing `include="elevation"` or `include="other_names,elevation"` gets that exact string on the URL the server sees, and defaults still send no `include` param.

### Node SDK 1.16.0
- Same approach: `client.places({ include: "elevation" })` flows through. Tests `test/places-elevation.test.js` (6 cases) mirror the Python coverage.

### OpenAPI
- `ele` documented on the `PlaceResult` schema (nullable, optional).
- `?include` param description on every Places endpoint updated to list `elevation` as a recognised value alongside `other_names`.

### Notes
- The new `ele` field exists in 5+ Places result paths (Search, Nearby, GetByID, Random, Chain, Batch, Similar) — all enriched consistently when `?include=elevation` is set.
- Customers integrating across both SDKs: kwarg-style `include="elevation"` (Python) and option-style `{ include: "elevation" }` (Node) match the existing place i18n pattern.

## [Sprint property-image] — 2026-05-23 — Per-address property aerial (`/v1/property/image`)

### Added
- New endpoint `GET /v1/property/image` returns a 600×600 PNG/JPEG/WebP aerial of any US property by address or coordinates.
- Two input shapes: `q=<address>` (geocoded internally — no extra charge) OR `lat=<n>&lng=<n>` (direct).
- `size` parameter — bbox edge length in meters, default 350 (~typical residential lot), max 2000.
- `format` parameter — `png` (default), `jpg`, `webp`.
- US-only coverage gate (CONUS + Alaska + Hawaii) — non-US coords return 400 `out_of_coverage` with the offending coordinate named.
- Source: USGS NAIP via `imagery.nationalmap.gov` ImageServer. Public-domain, no API key required, ~0.6 m typical resolution. We host zero imagery; per-request proxy with 30-day immutable `Cache-Control` so Cloudflare absorbs repeats per unique address.

### Python SDK 1.15.0
- `client.property_image(q=, lat=, lng=, size=, fmt=)` — fetches bytes (1 credit per call).
- `client.property_image_url(...)` — builds the URL without fetching (no credit charged).
- Same kwargs both methods. Local validation rejects calls missing both `q` and `lat`+`lng` before sending.

### Node SDK 1.15.0
- `client.propertyImage({ q, lat, lng, size, format })` — same shape.
- `client.propertyImageURL({ ... })` — URL builder.
- New `PropertyImageOptions` TypeScript interface.

### OpenAPI
- New `/property/image` path in all 3 spec files (`csv2geo-api/openapi.yaml`, `csv2geo/public/api-static/openapi.yaml`, `csv2geo/public/api-collections/openapi.yaml`) — byte-identical per Protocol F6.

### Notes
- 1 credit per call (`config/credit_costs.php` → `property_image`).
- Cold-call latency dominated by USGS round-trip (~1-2 s typical, 30 s max).
- Use cases: real-estate listings, insurance underwriting, appraisal, property research, computer-vision input for roof/pool/solar detection.
- Verified live 2026-05-23 against Wyoming MI (3168 Beckie Dr SW), White House DC. 8/8 customer-URL smoke probes pass.

## [Sprint staticmap-pin-labels] — 2026-05-23 — Per-pin labels on `/v1/staticmap`

### Added
- `GET /v1/staticmap` accepts an optional **label slot** on each marker (1–4 ASCII alphanumeric chars rendered inside the pin head). Two equivalent syntaxes — pick either:
  - **Positional**: `markers=lat,lng,color,label` (back-compat with the existing positional shape; named palette colors only)
  - **Keyed**: `markers=lat,lng,color:red,label:7` (order-independent; also accepts hex colors like `color:#ff8800`)
- Used for numbered route-stop pins — the canonical example is printed walklist PDFs where the canvasser carries a numbered table and needs the map pins to match row numbers.
- Hex color support (`#rgb` / `#rrggbb`) in the keyed form only — positional stays named-palette to keep parsing unambiguous on the wire. Escape `#` as `%23` in query strings.
- `GET /v1/icon` gained a new `type=pin&label=<text>` mode mirroring the staticmap label semantics. The staticmap proxy uses this internally over loopback so labelled-pin PNGs are deterministic and Cloudflare-cacheable per (color, label, size).
- Embedded Noto Sans Bold font in the Go binary for the label-text render path (Font Awesome's glyph table has no ASCII digits/letters). SIL OFL 1.1 — `api/internal/handlers/assets/NotoSans-OFL.txt`. Adds ~620 KB to the binary.

### Changed
- The `markers` parameter description now documents both syntaxes. Back-compat is total — every existing `markers=lat,lng,color` request returns the same image as before.

### Python SDK 1.14.0
- `client.static_map_url(markers=[{"lat": ..., "lng": ..., "color": ..., "label": ...}, ...])` — the marker builder now accepts dict shapes alongside the existing tuple/string forms. When `label` or a hex color is present, the wire form auto-switches to keyed; otherwise stays positional for back-compat.
- 4-element tuples `(lat, lng, color, label)` also accepted for terse positional construction.

### Node SDK 1.14.0
- `client.staticMapURL({ markers: [{ lat, lng, color, label }, ...] })` — same marker-shape extension. New `StaticMapMarkerObject` exported type.
- 4-element tuples `[lat, lng, color, label]` accepted positionally.
- Existing `StaticMapMarker` type union extended to include the new object form and 4-tuple.

### Notes
- The staticmap pipeline is Laravel → tileserver-gl → Go `/v1/icon`. Architecture decision: the Laravel proxy emits a `marker=lng,lat|http://172.17.0.1:8080/v1/icon?type=pin&color=&label=&...` URL per labelled pin; tileserver-gl (which runs in Docker, hence the bridge-gateway IP) fetches the labelled PNG over loopback and composites it into the basemap. Configurable via `STATICMAP_ICON_BASE_URL`.
- Designed and shipped on 2026-05-23 in response to WalkLists' migration off Mapbox; their canonical use case (numbered walking-route pins) is the primary integration target.

## [1.13.1] — 2026-05-23 — Python `__version__` hotfix + Node parity bump

### Python SDK 1.13.1
- **Fix:** `csv2geo.__version__` was hard-coded to `"1.12.0"` in `csv2geo/__init__.py` and was not bumped alongside `pyproject.toml` during the 1.13.0 ship. `importlib.metadata.version("csv2geo")` and PyPI's metadata both correctly reported `1.13.0`, but `print(csv2geo.__version__)` returned the stale value. Cosmetic only — no functional impact, the `radius=` kwarg and distance-aware bands all work as documented.
- **Test guard added:** `test_dunder_version_matches_pyproject` in `tests/test_default_url.py` reads `pyproject.toml` directly and asserts `csv2geo.__version__` matches. Run `pip install -e .` before pytest so `importlib.metadata` picks up the source tree.

### Node SDK 1.13.1
- Version-parity bump only — the Node 1.13.0 ship did not have the equivalent bug. Bumped to keep cross-language SDK versions aligned, which is the convention every prior sprint has followed.

## [Sprint reverse-scoring] — 2026-05-23 — Distance-aware reverse accuracy + `?radius=`

### Added
- `GET /v1/reverse` and `POST /v1/reverse` accept a new `?radius=<meters>` query parameter (integer, 1–1500, clamped to 1500, malformed/zero/negative falls back to default). Allows opting into a wider nearest-address search for rural / agricultural coordinates where no address point exists within the default 100 m cap.
- Reverse responses now return distance-aware `accuracy` and `accuracy_score`. Bands:
  - `rooftop` (≤30 m) → `accuracy_score: 1.0`
  - `building` (30–200 m) → `0.9`
  - `street` (200–500 m) → `0.7`
  - `postcode` (500–1500 m) → `0.5`
  - `city` (>1500 m) → `0.3`
- New public help page at https://help.csv2geo.com/guide/accuracy-scoring documenting the full forward + reverse scoring methodology, source attribution (which results we score vs which carry supplier confidence), and recommended customer thresholds.

### Changed
- **Default search radius is unchanged at 100 m** — callers who don't pass `?radius=` see no change in coverage.
- **But** reverse `accuracy_score` for an in-cap hit is no longer always `1.0`. A reverse hit at 50 m (which previously returned `accuracy: "rooftop", accuracy_score: 1.0`) now returns `accuracy: "building", accuracy_score: 0.9`. This corrects a long-standing over-claim where any hit within the 100 m cap was reported as rooftop precision regardless of actual offset.
- New `accuracy` enum values: `building`, `street`, `postcode`, `city`. The existing values (`rooftop`, `interpolated`, `centroid`, `approximate`, `postcode`) are unchanged.

### Python SDK 1.13.0
- `client.reverse(lat, lng, radius=)`, `client.reverse_full(lat, lng, radius=)`, `client.reverse_batch(coords, radius=)` — new `radius` keyword argument forwarded to the API. Default behaviour unchanged when `radius` is omitted.

### Node SDK 1.13.0
- `client.reverse(lat, lng, { radius })`, `client.reverseFull(lat, lng, { radius })`, `client.reverseBatch(coords, { radius })` — new `radius` option in the existing options object. New TypeScript `ReverseOptions` interface; the reverse method signatures now accept it.

### Notes
- This change applies ONLY to our Overture-sourced reverse results. HERE and Google fallback paths do not apply to reverse — they're forward-only — so supplier confidence values are unaffected.
- Historical task data (results stored in `csv2geo_tasks.user_*` collections from before 2026-05-23) is NOT backfilled. Re-running a task generates fresh scores; downloading an existing task surfaces whatever was scored at processing time.

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
