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

# Probe 5: invalid key path — must return invalid_api_key, NOT 404 / cert error.
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
