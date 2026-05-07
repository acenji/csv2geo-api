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
