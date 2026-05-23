// Sprint reverse-scoring 2026-05-23 — unit tests for the new `radius` option
// on reverse(), reverseFull(), and reverseBatch().
//
// Mirror of Python tests/test_reverse_radius.py. No network. Monkey-patches
// client._request to capture (method, path, params, body) and asserts that
// `radius` is present / absent / forwarded with the correct value depending
// on how the SDK is called.
//
// Server-side enforcement (clamp to 1500, default 100, malformed → default)
// is covered by overture-geocoder's TestParseReverseRadius. These tests
// cover only the SDK-side contract.

const test = require('node:test');
const assert = require('node:assert');
const { Client } = require('../src/index');

function makeStubClient() {
  const c = new Client({ apiKey: 'dummy_unit_test' });
  c.captured = [];
  c._request = async function (method, path, params, body) {
    c.captured.push({ method, path, params, body });
    return { results: [], meta: { version: '1.0.0' } };
  };
  return c;
}

// ─────────────────────────────────────────────────────────
// reverse() — single coord, GET
// ─────────────────────────────────────────────────────────

test('reverse() omits radius by default', async () => {
  const c = makeStubClient();
  await c.reverse(38.8977, -77.0365);
  assert.strictEqual(c.captured[0].params.radius, undefined);
});

test('reverse() forwards radius when set', async () => {
  const c = makeStubClient();
  await c.reverse(46.49125, -120.395, { radius: 1000 });
  assert.strictEqual(c.captured[0].params.radius, 1000);
});

test('reverse() forwards minimum radius', async () => {
  const c = makeStubClient();
  await c.reverse(38.8977, -77.0365, { radius: 1 });
  assert.strictEqual(c.captured[0].params.radius, 1);
});

test('reverse() forwards radius at max', async () => {
  const c = makeStubClient();
  await c.reverse(38.8977, -77.0365, { radius: 1500 });
  assert.strictEqual(c.captured[0].params.radius, 1500);
});

test('reverse() forwards out-of-range radius unchanged (server clamps)', async () => {
  const c = makeStubClient();
  await c.reverse(38.8977, -77.0365, { radius: 9999 });
  assert.strictEqual(c.captured[0].params.radius, 9999);
});

test('reverse() treats radius=0 as a real value (server falls back to default)', async () => {
  // Important: `if (options.radius != null)` is the gate — `0` IS forwarded.
  // Server-side ParseReverseRadius falls back to default for 0/negative;
  // SDK doesn't second-guess that.
  const c = makeStubClient();
  await c.reverse(38.8977, -77.0365, { radius: 0 });
  assert.strictEqual(c.captured[0].params.radius, 0);
});

// ─────────────────────────────────────────────────────────
// reverseFull() — single coord, GET, returns full response
// ─────────────────────────────────────────────────────────

test('reverseFull() omits radius by default', async () => {
  const c = makeStubClient();
  await c.reverseFull(38.8977, -77.0365);
  assert.strictEqual(c.captured[0].params.radius, undefined);
});

test('reverseFull() forwards radius when set', async () => {
  const c = makeStubClient();
  await c.reverseFull(46.49125, -120.395, { radius: 500 });
  assert.strictEqual(c.captured[0].params.radius, 500);
});

// ─────────────────────────────────────────────────────────
// reverseBatch() — POST with body
// ─────────────────────────────────────────────────────────

test('reverseBatch() omits radius by default', async () => {
  const c = makeStubClient();
  await c.reverseBatch([
    { lat: 38.8977, lng: -77.0365 },
    { lat: 40.7484, lng: -73.9857 },
  ]);
  const call = c.captured[0];
  assert.strictEqual(call.method, 'POST');
  assert.strictEqual(call.path, '/reverse');
  assert.strictEqual(call.params.radius, undefined);
});

test('reverseBatch() forwards radius as a query-string param (server reads c.Query)', async () => {
  const c = makeStubClient();
  await c.reverseBatch(
    [{ lat: 38.8977, lng: -77.0365 }, { lat: 40.7484, lng: -73.9857 }],
    { radius: 1000 },
  );
  const call = c.captured[0];
  assert.strictEqual(call.params.radius, 1000);
  // Coordinates still go in the JSON body, not in params.
  assert.deepStrictEqual(call.body, {
    coordinates: [
      { lat: 38.8977, lng: -77.0365 },
      { lat: 40.7484, lng: -73.9857 },
    ],
  });
});

test('reverseBatch() radius combines with lang', async () => {
  const c = makeStubClient();
  await c.reverseBatch(
    [{ lat: 38.8977, lng: -77.0365 }],
    { lang: 'de', radius: 500 },
  );
  const params = c.captured[0].params;
  assert.strictEqual(params.radius, 500);
  assert.strictEqual(params.lang, 'de');
});
