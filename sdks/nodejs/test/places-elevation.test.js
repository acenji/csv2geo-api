// Sprint ele-on-places 2026-05-24 — unit tests asserting that
// include=elevation reaches the wire on every Places-family method.
//
// Mirror of Python tests/test_places_elevation.py. No network. Locks the
// SDK ↔ API contract: a customer who passes include: "elevation" (or
// "other_names,elevation") gets that exact string forwarded.

const test = require('node:test');
const assert = require('node:assert');
const { Client } = require('../src/index');

function makeStubClient() {
  const c = new Client('dummy_unit_test');
  c.captured = [];
  c._request = async function (method, path, params, body) {
    c.captured.push({ method, path, params, body });
    return { results: [], meta: { version: '1.0.0' } };
  };
  return c;
}

// ─────────────────────────────────────────────────────────
// include="elevation" alone
// ─────────────────────────────────────────────────────────

// Node SDK uses the options-object shape:
//   client.places({ query, country, category, limit, lang, include, ... })
//   client.placesNearby(lat, lng, { radius, category, limit, lang, include, ... })
// (NOT positional like the Python SDK — different language ergonomics).

test('places(): forwards include=elevation', async () => {
  const c = makeStubClient();
  await c.places({ query: 'cafe', country: 'US', include: 'elevation' });
  assert.strictEqual(c.captured[0].params.include, 'elevation');
});

test('placesNearby(): forwards include=elevation', async () => {
  const c = makeStubClient();
  await c.placesNearby(38.8977, -77.0365, { radius: 300, include: 'elevation' });
  assert.strictEqual(c.captured[0].params.include, 'elevation');
});

// ─────────────────────────────────────────────────────────
// include="other_names,elevation" composition
// ─────────────────────────────────────────────────────────

test('places(): composes other_names + elevation', async () => {
  const c = makeStubClient();
  await c.places({ query: 'cafe', country: 'US', include: 'other_names,elevation' });
  assert.strictEqual(c.captured[0].params.include, 'other_names,elevation');
});

test('places(): explicit include overrides includeOtherNames bool', async () => {
  // Existing convention — explicit include= wins. Same with elevation in the mix.
  const c = makeStubClient();
  await c.places({ query: 'cafe', country: 'US', includeOtherNames: true, include: 'other_names,elevation' });
  assert.strictEqual(c.captured[0].params.include, 'other_names,elevation');
});

// ─────────────────────────────────────────────────────────
// Default behaviour — no include param when not requested.
// Lock against future regression that would silently turn on elevation
// for everyone (and the per-call Valhalla round-trip cost).
// ─────────────────────────────────────────────────────────

test('places(): default has no include param', async () => {
  const c = makeStubClient();
  await c.places({ query: 'cafe', country: 'US' });
  assert.strictEqual(c.captured[0].params.include, undefined);
});

test('placesNearby(): default has no include param', async () => {
  const c = makeStubClient();
  await c.placesNearby(38.8977, -77.0365, { radius: 300 });
  assert.strictEqual(c.captured[0].params.include, undefined);
});
