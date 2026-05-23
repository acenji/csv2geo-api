// Sprint staticmap-pin-labels 2026-05-23 — unit tests for the marker
// wire-form builder.
//
// Mirror of Python tests/test_static_map_labels.py. No network. Locks
// the SDK ↔ API contract by asserting on the exact wire string the SDK
// would emit. Pairs with the Go-side handler tests and the Laravel
// proxy tests for end-to-end coverage.

const test = require('node:test');
const assert = require('node:assert');
const { Client, InvalidRequestError } = require('../src/index');

// ─────────────────────────────────────────────────────────
// _staticMapMarker — pure unit tests on the helper.
// ─────────────────────────────────────────────────────────

test('_staticMapMarker: string passes through', () => {
  assert.strictEqual(Client._staticMapMarker('47.6,-122.3,red,7'), '47.6,-122.3,red,7');
});

test('_staticMapMarker: 2-tuple lat,lng only', () => {
  assert.strictEqual(Client._staticMapMarker([47.6, -122.3]), '47.6,-122.3');
});

test('_staticMapMarker: 3-tuple with color', () => {
  assert.strictEqual(Client._staticMapMarker([47.6, -122.3, 'red']), '47.6,-122.3,red');
});

test('_staticMapMarker: 4-tuple with label (Sprint staticmap-pin-labels)', () => {
  assert.strictEqual(Client._staticMapMarker([47.6, -122.3, 'red', '7']), '47.6,-122.3,red,7');
});

test('_staticMapMarker: tuple too short rejected', () => {
  assert.throws(() => Client._staticMapMarker([47.6]), InvalidRequestError);
});

test('_staticMapMarker: tuple too long rejected', () => {
  assert.throws(() => Client._staticMapMarker([47.6, -122.3, 'red', '7', 'extra']), InvalidRequestError);
});

test('_staticMapMarker: object lat,lng only → positional', () => {
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3 }),
    '47.6,-122.3',
  );
});

test('_staticMapMarker: object with named color → positional', () => {
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3, color: 'red' }),
    '47.6,-122.3,red',
  );
});

test('_staticMapMarker: object with label → keyed form', () => {
  // Label is present → MUST emit keyed form, because positional form's
  // label slot is only unambiguous after a color and the server parser
  // explicitly rejects positional/keyed mixing.
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3, color: 'red', label: '7' }),
    '47.6,-122.3,color:red,label:7',
  );
});

test('_staticMapMarker: object with hex color → keyed (hex illegal in positional)', () => {
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3, color: '#ff8800' }),
    '47.6,-122.3,color:#ff8800',
  );
});

test('_staticMapMarker: object with hex color and label → keyed', () => {
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3, color: '#ff8800', label: '42' }),
    '47.6,-122.3,color:#ff8800,label:42',
  );
});

test('_staticMapMarker: object with only label → keyed (server picks default color)', () => {
  assert.strictEqual(
    Client._staticMapMarker({ lat: 47.6, lng: -122.3, label: '7' }),
    '47.6,-122.3,label:7',
  );
});

test('_staticMapMarker: object missing lat rejected', () => {
  assert.throws(() => Client._staticMapMarker({ lng: -122.3 }), InvalidRequestError);
});

test('_staticMapMarker: object missing lng rejected', () => {
  assert.throws(() => Client._staticMapMarker({ lat: 47.6 }), InvalidRequestError);
});

test('_staticMapMarker: number rejected', () => {
  assert.throws(() => Client._staticMapMarker(42), InvalidRequestError);
});

// ─────────────────────────────────────────────────────────
// staticMapURL — end-to-end URL construction.
// ─────────────────────────────────────────────────────────

test('staticMapURL: labelled marker round-trips through decoded URL', () => {
  const c = new Client({ apiKey: 'dummy_unit_test' });
  const url = c.staticMapURL({
    center: [47.6, -122.3],
    zoom: 14,
    markers: [{ lat: 47.6062, lng: -122.3321, color: 'red', label: '7' }],
  });
  // urlencode escapes ':' and ',' — decode to compare against the
  // unambiguous wire form we want the server to see.
  const decoded = decodeURIComponent(url);
  assert.match(decoded, /47\.6062,-122\.3321,color:red,label:7/);
});

test('staticMapURL: mixes labelled and unlabelled markers correctly', () => {
  const c = new Client({ apiKey: 'dummy_unit_test' });
  const url = c.staticMapURL({
    center: [47.6, -122.3],
    zoom: 14,
    markers: [
      { lat: 47.6062, lng: -122.3321, color: 'red', label: '1' },
      { lat: 47.6090, lng: -122.3360, color: 'blue' },
    ],
  });
  const decoded = decodeURIComponent(url);
  assert.match(decoded, /\|/, 'pipe separator survives decoding');
  assert.match(decoded, /color:red,label:1/, 'first marker is keyed');
  assert.match(decoded, /47\.609,-122\.336,blue/, 'second marker stays positional');
});

test('staticMapURL: no markers → no markers param', () => {
  const c = new Client({ apiKey: 'dummy_unit_test' });
  const url = c.staticMapURL({ center: [47.6, -122.3], zoom: 14 });
  assert.doesNotMatch(url, /markers=/);
});

test('staticMapURL: hex color uses keyed form (positional would mis-parse)', () => {
  const c = new Client({ apiKey: 'dummy_unit_test' });
  const url = c.staticMapURL({
    center: [47.6, -122.3],
    zoom: 14,
    markers: [{ lat: 47.6, lng: -122.3, color: '#ff8800', label: '42' }],
  });
  const decoded = decodeURIComponent(url);
  assert.match(decoded, /color:#ff8800,label:42/);
});
