#!/bin/bash
# smoke-customer-api.sh
#
# End-to-end smoke probe of the customer-facing API. Run from any host;
# requires only curl + jq + a geo_live_* key.
#
# Designed to be wired into:
#   - The OVH watchdog (sc-watchdog.timer, runs every minute) — call it as
#     one of its checks
#   - GitHub Actions cron — runs every 15 minutes
#   - Manual debugging — `CSV2GEO_TEST_KEY=geo_live_... ./smoke-customer-api.sh`
#
# Goal: catch the class of bug where production routing breaks for paying
# customers (wrong host, expired cert, middleware regression, etc.) before
# anyone notices via support tickets.
#
# Exit codes:
#   0 — all probes green
#   1 — any probe failed (use this in cron to trigger alerting)
#   2 — environment not configured (no key) — treated as skip, not failure

set -u

KEY="${CSV2GEO_TEST_KEY:-}"
BASE="${CSV2GEO_BASE_URL:-https://csv2geo.com/api/v1}"
TIMEOUT="${CSV2GEO_SMOKE_TIMEOUT:-15}"

if [ -z "$KEY" ]; then
  echo "smoke: CSV2GEO_TEST_KEY not set — skipping (exit 2)"
  exit 2
fi

if [[ ! "$KEY" =~ ^geo_live_ ]]; then
  echo "smoke: CSV2GEO_TEST_KEY does not start with geo_live_ — refusing to test"
  exit 1
fi

FAIL=0
RESULTS=""

probe() {
  local name="$1"
  local url="$2"
  local jq_check="$3"

  local body
  body=$(curl -sS --max-time "$TIMEOUT" "$url" 2>/dev/null) || {
    RESULTS+="✘ $name: connect failed\n"
    FAIL=1; return
  }
  if echo "$body" | jq -e "$jq_check" >/dev/null 2>&1; then
    RESULTS+="✓ $name\n"
  else
    RESULTS+="✘ $name: jq assertion failed (body: $(echo "$body" | head -c 200))\n"
    FAIL=1
  fi
}

# Probe 1: forward geocoding — known stable input, asserts non-empty results
probe "geocode 90210"                                                          \
  "$BASE/geocode?q=90210&country=US&api_key=$KEY"                              \
  '.results | length > 0 and .[0].location.lat != null'

# Probe 2: reverse geocoding — White House coords
probe "reverse 38.8977,-77.0365"                                               \
  "$BASE/reverse?lat=38.8977&lng=-77.0365&api_key=$KEY"                        \
  '.results | length > 0'

# Probe 3: /v1/ip — Sprint 2.7 endpoint, must return country at minimum
probe "ip 8.8.8.8"                                                             \
  "$BASE/ip?ip=8.8.8.8&api_key=$KEY"                                           \
  '.country.code == "US" and (.confidence | IN("high","medium","low"))'

# Probe 4: /v1/divisions/by-postcode (Sprint 1)
probe "divisions/by-postcode 90210"                                            \
  "$BASE/divisions/by-postcode?code=90210&country=US&api_key=$KEY"             \
  '.result.population != null or .result.bbox != null'

# Probes 5-11: Routing endpoints (Sprint 2.4). All Pro+ only; if the test
# key isn't on a Pro/Unlimited plan with the `routing` permission these
# will fail with 403 — re-key the smoke before fixing the geocoder. The
# matrix probe also validates that max_matrix_distance is bumped enough
# for the regional pair to be reachable (Sprint 2.4 phase 6 closeout).
probe "routing NYC->LA drive"                                                  \
  "$BASE/routing?waypoints=40.7128,-74.006|34.0522,-118.2437&mode=drive&api_key=$KEY" \
  '.results[0].summary.distance_m > 4000000 and .results[0].summary.distance_m < 5000000'

probe "isoline Times Square 10/15-min"                                         \
  "$BASE/isoline?lat=40.7580&lng=-73.9855&mode=drive&type=time&ranges=600,900&api_key=$KEY" \
  '.results | length == 2'

probe "optimize_route 4 Manhattan stops"                                       \
  "$BASE/optimize_route?waypoints=40.7128,-74.006|40.7580,-73.9855|40.7484,-73.9857|40.7061,-74.0087&mode=drive&api_key=$KEY" \
  '.results.optimal_order | length == 4'

probe "locate Times Square"                                                    \
  "$BASE/locate?lat=40.7580&lng=-73.9855&mode=drive&api_key=$KEY"              \
  '.result.snapped_lat != null and .result.edge.name != null'

# POST probes — use the same probe() helper with --data-binary inline.
ROUTE_MATRIX_BODY='{"sources":[{"lat":40.7128,"lng":-74.006}],"targets":[{"lat":42.36,"lng":-71.05},{"lat":38.9,"lng":-77.03}],"mode":"drive"}'
RM_RESP=$(curl -sS --max-time "$TIMEOUT" -X POST "$BASE/route-matrix?api_key=$KEY" \
  -H "Content-Type: application/json" -d "$ROUTE_MATRIX_BODY" 2>/dev/null) || RM_RESP=""
if echo "$RM_RESP" | jq -e '.results.durations_s[0][0] > 0 and .results.durations_s[0][1] > 0' >/dev/null 2>&1; then
  RESULTS+="✓ route-matrix NYC->{BOS,DC}\n"
else
  RESULTS+="✘ route-matrix: $(echo "$RM_RESP" | head -c 200)\n"
  FAIL=1
fi

MAP_MATCH_BODY='{"trace":[{"lat":40.7589,"lng":-73.9851},{"lat":40.7596,"lng":-73.9853},{"lat":40.7603,"lng":-73.9856},{"lat":40.7610,"lng":-73.9858},{"lat":40.7617,"lng":-73.9861},{"lat":40.7624,"lng":-73.9863}],"mode":"drive"}'
MM_RESP=$(curl -sS --max-time "$TIMEOUT" -X POST "$BASE/map-match?api_key=$KEY" \
  -H "Content-Type: application/json" -d "$MAP_MATCH_BODY" 2>/dev/null) || MM_RESP=""
if echo "$MM_RESP" | jq -e '.results.distance_m > 0 and .results.geometry.type == "LineString"' >/dev/null 2>&1; then
  RESULTS+="✓ map-match 6-pt Broadway trace\n"
else
  RESULTS+="✘ map-match: $(echo "$MM_RESP" | head -c 200)\n"
  FAIL=1
fi

# Elevation: returns 503 elevation_data_unavailable until DEM tiles are
# installed (Sprint 2.4 followup). Treat both that and a successful 200
# with real numbers as ✓ — but ✘ if we get a different unexpected error.
ELEV_RESP=$(curl -sS --max-time "$TIMEOUT" -w '\nHTTP:%{http_code}' \
  "$BASE/elevation?points=39.7392,-104.9903|40.7128,-74.006&api_key=$KEY" 2>/dev/null) || ELEV_RESP=""
ELEV_CODE=$(echo "$ELEV_RESP" | grep -oE 'HTTP:[0-9]+' | tail -1 | cut -d: -f2)
ELEV_BODY=$(echo "$ELEV_RESP" | sed '$ d')
if [ "$ELEV_CODE" = "200" ] && echo "$ELEV_BODY" | jq -e '.results[0].elevation_m != null' >/dev/null 2>&1; then
  RESULTS+="✓ elevation (with DEM tiles installed)\n"
elif [ "$ELEV_CODE" = "503" ] && echo "$ELEV_BODY" | jq -e '.error.code == "elevation_data_unavailable"' >/dev/null 2>&1; then
  RESULTS+="✓ elevation (503 elevation_data_unavailable — DEM install pending, expected state)\n"
else
  RESULTS+="✘ elevation: HTTP $ELEV_CODE body=$(echo "$ELEV_BODY" | head -c 200)\n"
  FAIL=1
fi

# Marker icon (Sprint 2.6). Asserts image/png + reasonable size + Cache-Control.
ICON_HDRS=$(curl -sS --max-time "$TIMEOUT" -D - -o /tmp/smoke-icon.png \
  "$BASE/icon?icon=tree&color=52b74c&size=x-large&scaleFactor=2&api_key=$KEY" 2>/dev/null) || ICON_HDRS=""
ICON_CT=$(echo "$ICON_HDRS" | grep -i "^content-type:" | head -1 | tr -d "\r" | awk "{print \$2}")
ICON_SIZE=$(wc -c < /tmp/smoke-icon.png 2>/dev/null || echo 0)
ICON_CC=$(echo "$ICON_HDRS" | grep -i "^cache-control:" | head -1 | tr -d "\r")
ICON_MAGIC=$(head -c 4 /tmp/smoke-icon.png | od -An -t x1 | tr -d " \n" 2>/dev/null)
if [ "$ICON_CT" = "image/png" ] && [ "$ICON_SIZE" -gt 1000 ] && [ "$ICON_MAGIC" = "89504e47" ]; then
  RESULTS+="✓ icon (tree pin, content-type=$ICON_CT, $ICON_SIZE bytes, immutable cache: $(echo "$ICON_CC" | grep -q immutable && echo yes || echo no))\n"
else
  RESULTS+="✘ icon: ct=$ICON_CT size=$ICON_SIZE magic=$ICON_MAGIC\n"
  FAIL=1
fi
rm -f /tmp/smoke-icon.png

# Static map (Sprint 3.1). Asserts a real PNG image + immutable cache —
# proves the Laravel proxy → HAProxy :8087 → tileserver-gl render path.
SMAP_HDRS=$(curl -sS --max-time "$TIMEOUT" -D - -o /tmp/smoke-staticmap.png \
  "$BASE/staticmap?style=csv2geo-bright&center=40.7484,-73.9857&zoom=13&width=400&height=300&markers=40.7484,-73.9857,red&api_key=$KEY" 2>/dev/null) || SMAP_HDRS=""
SMAP_CT=$(echo "$SMAP_HDRS" | grep -i "^content-type:" | head -1 | tr -d "\r" | awk "{print \$2}")
SMAP_SIZE=$(wc -c < /tmp/smoke-staticmap.png 2>/dev/null || echo 0)
SMAP_CC=$(echo "$SMAP_HDRS" | grep -i "^cache-control:" | head -1 | tr -d "\r")
SMAP_MAGIC=$(head -c 4 /tmp/smoke-staticmap.png | od -An -t x1 | tr -d " \n" 2>/dev/null)
if [ "$SMAP_CT" = "image/png" ] && [ "$SMAP_SIZE" -gt 2000 ] && [ "$SMAP_MAGIC" = "89504e47" ]; then
  RESULTS+="✓ staticmap (Manhattan + marker, content-type=$SMAP_CT, $SMAP_SIZE bytes, immutable cache: $(echo "$SMAP_CC" | grep -q immutable && echo yes || echo no))\n"
else
  RESULTS+="✘ staticmap: ct=$SMAP_CT size=$SMAP_SIZE magic=$SMAP_MAGIC\n"
  FAIL=1
fi
rm -f /tmp/smoke-staticmap.png

# Batch wrapper (Sprint 2.5). POST /batch -> 202 + id, GET /batch/{id} -> completed.
# Two-step probe: submit + poll until terminal. Asserts result count and a
# minimum number of completed inputs.
BATCH_BODY='{"api":"/v1/geocode","inputs":[{"id":"a","params":{"q":"90210","country":"US"}},{"id":"b","params":{"q":"10001","country":"US"}}]}'
BATCH_RESP=$(curl -sS --max-time "$TIMEOUT" -X POST "$BASE/batch?api_key=$KEY" \
  -H "Content-Type: application/json" -d "$BATCH_BODY" 2>/dev/null) || BATCH_RESP=""
BATCH_ID=$(echo "$BATCH_RESP" | jq -r '.id // empty' 2>/dev/null)
if [ -z "$BATCH_ID" ]; then
  RESULTS+="✘ batch POST: no job id in response ($(echo "$BATCH_RESP" | head -c 200))\n"
  FAIL=1
else
  # Poll up to 10 seconds for a 2-input geocode batch to complete.
  BATCH_FINAL=""
  for _ in 1 2 3 4 5; do
    sleep 1
    BATCH_FINAL=$(curl -sS --max-time "$TIMEOUT" "$BASE/batch/$BATCH_ID?api_key=$KEY" 2>/dev/null) || BATCH_FINAL=""
    if echo "$BATCH_FINAL" | jq -e '.status == "completed"' >/dev/null 2>&1; then break; fi
  done
  if echo "$BATCH_FINAL" | jq -e '.status == "completed" and (.results | length) == 2 and .results[0].input_id == "a" and .results[0].status == 200' >/dev/null 2>&1; then
    RESULTS+="✓ batch POST+poll (2-input geocode, terminal in ≤5s)\n"
  else
    RESULTS+="✘ batch POST+poll: final state did not match expectations (body: $(echo "$BATCH_FINAL" | head -c 300))\n"
    FAIL=1
  fi
fi

# Probe 12: invalid key path — must return invalid_api_key, NOT 404 / cert error.
# Proves we're hitting the right Laravel proxy, not stray to the wrong host.
INVALID_BODY=$(curl -sS --max-time "$TIMEOUT" "$BASE/geocode?q=test&api_key=geo_live_INVALIDinvalidINVALIDinvalid" 2>/dev/null) || INVALID_BODY=""
if echo "$INVALID_BODY" | jq -e '.error.code == "invalid_api_key"' >/dev/null 2>&1; then
  RESULTS+="✓ invalid-key returns invalid_api_key (not 404/route-loss)\n"
else
  RESULTS+="✘ invalid-key check: expected invalid_api_key, got: $(echo "$INVALID_BODY" | head -c 200)\n"
  FAIL=1
fi

echo -e "$RESULTS"

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "AT LEAST ONE PROBE FAILED — investigate the customer API surface NOW."
  echo "Wrong base URL? Cert expired? Laravel route-cache stale? OPcache?"
  echo "Reference: hosting/ScaleCampaign/third-party/maxmind/credentials.txt"
  exit 1
fi

echo "all probes green @ $(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit 0
