// Live smoke tests against production.
//
// Skipped by default; runs only when CSV2GEO_TEST_KEY is set in the env
// (developer machine or CI). Catches the class of bug where the SDK
// technically compiles but customers can't actually reach the service
// with their real key.
//
// Run locally:
//   CSV2GEO_TEST_KEY=geo_live_... node --test test/smoke-live.test.js
//
// Run inside CI: store the key in the secret store, expose as env var.

const test = require('node:test');
const assert = require('node:assert');

const { Client } = require('../src/index');

const KEY = process.env.CSV2GEO_TEST_KEY || '';
const HAS_KEY = KEY && KEY.startsWith('geo_live_');

const skipIfNoKey = HAS_KEY
  ? {}
  : { skip: 'CSV2GEO_TEST_KEY not set or not a geo_live_* key' };

test('geocode returns a valid result for a stable query', skipIfNoKey, async () => {
  const c = new Client(KEY);
  const r = await c.geocode('90210');
  assert.ok(r, 'no result returned');
  assert.ok(typeof r.lat === 'number', `lat missing/wrong type: ${r.lat}`);
  assert.ok(typeof r.lng === 'number', `lng missing/wrong type: ${r.lng}`);
  // Beverly Hills, CA — known stable answer
  assert.ok(r.lat > 33 && r.lat < 35, `lat ${r.lat} far off expected`);
  assert.ok(r.lng > -119 && r.lng < -117, `lng ${r.lng} far off expected`);
});

test('reverse-geocode resolves a known coordinate', skipIfNoKey, async () => {
  const c = new Client(KEY);
  const r = await c.reverse(38.8977, -77.0365);
  assert.ok(r, 'no result');
  assert.ok(r.formattedAddress || r.formatted_address, 'no formatted address');
  const addr = r.formattedAddress || r.formatted_address;
  assert.ok(
    addr.includes('Washington') || addr.includes('DC'),
    `unexpected address: ${addr}`
  );
});

test('/v1/ip endpoint returns county overlay for residential IPs', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.ip !== 'function') {
    t.skip('client.ip() not present in this SDK version');
    return;
  }
  const r = await c.ip('8.8.8.8');
  assert.ok(r, 'no result');
  assert.strictEqual(r.country?.code, 'US', 'country wrong');
  assert.ok(
    ['high', 'medium', 'low'].includes(r.confidence),
    `confidence missing/invalid: ${r.confidence}`
  );
});

test('invalid key returns 401 (proves we hit the right host)', skipIfNoKey, async () => {
  // If the SDK accidentally pointed at the wrong host, /v1/geocode wouldn't
  // exist there and we'd get a 404 / connection error rather than a 401.
  // A 401 with invalid_api_key proves we're hitting the right Laravel proxy.
  const c = new Client('geo_live_INVALIDinvalidINVALIDinvalid');
  await assert.rejects(
    async () => await c.geocode('90210'),
    (err) => err.status === 401 || err.code === 'invalid_api_key',
    'expected 401 / invalid_api_key, got something else'
  );
});

// ── Routing (Sprint 2.4) — Pro+ plans only ─────────────────────────────
// Tests skip gracefully when (a) the SDK method doesn't exist, (b) the
// key isn't on a Pro/Unlimited plan, or (c) elevation tiles aren't
// installed yet (a Sprint 2.4 followup).

function skipIfPermissionError(t, err, label) {
  const msg = (err.message || '').toLowerCase();
  const code = err.code || '';
  if (msg.includes('permission') || code === 'plan_permission_denied' || code === 'insufficient_permissions') {
    t.skip(`${label}: key is not Pro+ for routing (${code || msg})`);
    return true;
  }
  return false;
}

test('routing drive NYC->LA', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.route !== 'function') return t.skip('client.route() not in this SDK version');
  try {
    const r = await c.route([[40.7128, -74.006], [34.0522, -118.2437]], { mode: 'drive' });
    const s = r.results[0].summary;
    assert.ok(s.distance_m > 4_000_000 && s.distance_m < 5_000_000,
      `distance ${s.distance_m} out of band 4_000_000–5_000_000`);
    assert.ok(s.duration_s > 100_000 && s.duration_s < 200_000,
      `duration ${s.duration_s} out of band 100_000–200_000`);
  } catch (e) {
    if (skipIfPermissionError(t, e, 'routing')) return;
    throw e;
  }
});

test('routing isoline Times Square', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.isoline !== 'function') return t.skip('client.isoline() not in this SDK version');
  try {
    const r = await c.isoline({ lat: 40.7580, lng: -73.9855, mode: 'drive', ranges: [600, 900] });
    assert.strictEqual(r.results.length, 2);
    for (const entry of r.results) {
      assert.strictEqual(entry.geometry?.type, 'Polygon');
    }
  } catch (e) {
    if (skipIfPermissionError(t, e, 'isoline')) return;
    throw e;
  }
});

test('routing matrix NYC->{BOS, DC}', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.routeMatrix !== 'function') return t.skip('client.routeMatrix() not in this SDK version');
  try {
    const r = await c.routeMatrix({
      sources: [{ lat: 40.7128, lng: -74.006 }],
      targets: [{ lat: 42.36, lng: -71.05 }, { lat: 38.9, lng: -77.03 }],
      mode: 'drive',
    });
    const d = r.results.durations_s;
    assert.ok(d[0][0] > 0, 'NYC->BOS unreachable (matrix cap regression?)');
    assert.ok(d[0][1] > 0, 'NYC->DC unreachable');
  } catch (e) {
    if (skipIfPermissionError(t, e, 'routeMatrix')) return;
    throw e;
  }
});

test('routing locate Times Square', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.locate !== 'function') return t.skip('client.locate() not in this SDK version');
  try {
    const r = await c.locate(40.7580, -73.9855, { mode: 'drive' });
    assert.ok(r.result.snapped_lat != null);
    assert.ok(r.result.snapped_lng != null);
    assert.ok(r.result.edge?.name, 'edge.name missing on a known street');
  } catch (e) {
    if (skipIfPermissionError(t, e, 'locate')) return;
    throw e;
  }
});

test('routing elevation (skip if DEM tiles missing)', skipIfNoKey, async (t) => {
  const c = new Client(KEY);
  if (typeof c.elevation !== 'function') return t.skip('client.elevation() not in this SDK version');
  try {
    const r = await c.elevation([[39.7392, -104.9903], [40.7128, -74.006]]);
    // DEM tiles live → real numbers expected
    assert.ok(r.results[0].elevation_m != null, 'elevation_m null with DEM installed?');
  } catch (e) {
    const msg = (e.message || '').toLowerCase();
    const code = e.code || '';
    if (msg.includes('elevation tiles are not installed') || code === 'elevation_data_unavailable') {
      return t.skip('DEM tiles not yet installed (expected pre-Phase-1c)');
    }
    if (skipIfPermissionError(t, e, 'elevation')) return;
    throw e;
  }
});
