// Sprint property-image 2026-05-23 — unit tests for propertyImage /
// propertyImageURL.
//
// Mirror of Python tests/test_property_image.py. No network. Locks the
// SDK ↔ API contract by asserting on the exact URL the SDK would emit.
// Pairs with the Go-side property_image_test.go and the Laravel proxy
// tests for end-to-end coverage.

const test = require('node:test');
const assert = require('node:assert');
const { Client, InvalidRequestError } = require('../src/index');

function newClient() {
  return new Client('dummy_key_for_unit_test');
}

// ─────────────────────────────────────────────────────────
// propertyImageURL — pure URL construction.
// ─────────────────────────────────────────────────────────

test('propertyImageURL: q form emits q param', () => {
  const url = newClient().propertyImageURL({ q: '3168 Beckie Dr SW, Wyoming, MI 49418' });
  const u = new URL(url);
  assert.strictEqual(u.searchParams.get('q'), '3168 Beckie Dr SW, Wyoming, MI 49418');
  assert.strictEqual(u.searchParams.get('lat'), null);
  assert.strictEqual(u.searchParams.get('lng'), null);
});

test('propertyImageURL: lat+lng form emits both', () => {
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419 });
  const u = new URL(url);
  assert.strictEqual(u.searchParams.get('lat'), '42.86753');
  assert.strictEqual(u.searchParams.get('lng'), '-85.7419');
  assert.strictEqual(u.searchParams.get('q'), null);
});

test('propertyImageURL: size forwarded', () => {
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419, size: 1000 });
  assert.match(url, /size=1000/);
});

test('propertyImageURL: size omitted when not set', () => {
  // Server defaults to 350 — SDK MUST NOT inject one of its own so
  // a future server default change doesn't require an SDK bump.
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419 });
  assert.doesNotMatch(url, /size=/);
});

test('propertyImageURL: format forwarded', () => {
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419, format: 'jpg' });
  assert.match(url, /format=jpg/);
});

test('propertyImageURL: api_key always present', () => {
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419 });
  assert.match(url, /api_key=dummy_key_for_unit_test/);
});

test('propertyImageURL: path is /property/image (NOT /icon or other)', () => {
  // Customer URL: csv2geo.com/api/v1/property/image — not a Go internal
  // path. Lock against the path regressing.
  const url = newClient().propertyImageURL({ lat: 42.86753, lng: -85.7419 });
  const path = new URL(url).pathname;
  assert.ok(path.endsWith('/property/image'), `path = ${path}`);
});

// ─────────────────────────────────────────────────────────
// Validation — local guards before sending to the server.
// ─────────────────────────────────────────────────────────

test('propertyImageURL: missing both q and lat+lng throws locally', () => {
  assert.throws(
    () => newClient().propertyImageURL({}),
    InvalidRequestError,
  );
});

test('propertyImageURL: only lat throws', () => {
  assert.throws(
    () => newClient().propertyImageURL({ lat: 42.86753 }),
    InvalidRequestError,
  );
});

test('propertyImageURL: only lng throws', () => {
  assert.throws(
    () => newClient().propertyImageURL({ lng: -85.7419 }),
    InvalidRequestError,
  );
});

test('propertyImageURL: q alone is fine (server geocodes)', () => {
  const url = newClient().propertyImageURL({ q: 'White House, Washington DC' });
  assert.match(url, /q=White\+House/);
});

test('propertyImageURL: lat 0 lng 0 treated as a real coord pair (not falsy)', () => {
  // (0, 0) is in the Gulf of Guinea — not in US — but the URL builder
  // should NOT reject it locally as "missing"; the server's out_of_coverage
  // check is the right place to fail. This tests the falsy-coord trap.
  const url = newClient().propertyImageURL({ lat: 0, lng: 0 });
  assert.match(url, /lat=0/);
  assert.match(url, /lng=0/);
});
