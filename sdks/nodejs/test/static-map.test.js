// Unit tests for the static map URL builder (Sprint 3.1).
//
// These do NOT hit the network. staticMapURL() builds a URL string with
// real translation logic — marker/path normalization, lat,lng wire
// format, viewport selection — so the logic is locked here.

const test = require('node:test');
const assert = require('node:assert');

const { Client, InvalidRequestError } = require('../src/index');

function client() {
  return new Client('geo_live_unit_test_key');
}

// Parsed query of a static map URL, values already URL-decoded.
function query(url) {
  const u = new URL(url);
  assert.ok(u.pathname.endsWith('/staticmap'), `unexpected path: ${u.pathname}`);
  const q = {};
  for (const [k, v] of u.searchParams.entries()) q[k] = v;
  return q;
}

test('basic center + zoom URL', () => {
  const q = query(client().staticMapURL({ center: [40.5, -73.5], zoom: 12 }));
  assert.strictEqual(q.center, '40.5,-73.5');
  assert.strictEqual(q.zoom, '12');
  assert.strictEqual(q.style, 'csv2geo-bright');
  assert.strictEqual(q.api_key, 'geo_live_unit_test_key');
});

test('defaults are applied', () => {
  const q = query(client().staticMapURL({ center: [0, 0], zoom: 3 }));
  assert.strictEqual(q.width, '600');
  assert.strictEqual(q.height, '400');
  assert.strictEqual(q.format, 'png');
  assert.strictEqual(q.scale, '1');
});

test('size, format and scale pass through', () => {
  const q = query(client().staticMapURL({
    center: [1, 2], zoom: 5, width: 800, height: 300, format: 'webp', scale: 2,
  }));
  assert.strictEqual(q.width, '800');
  assert.strictEqual(q.height, '300');
  assert.strictEqual(q.format, 'webp');
  assert.strictEqual(q.scale, '2');
});

test('marker tuple becomes lat,lng,color', () => {
  const q = query(client().staticMapURL({
    center: [40.5, -73.5], zoom: 12, markers: [[40.5, -73.5, 'green']],
  }));
  assert.strictEqual(q.markers, '40.5,-73.5,green');
});

test('multiple markers joined with a pipe', () => {
  const q = query(client().staticMapURL({
    center: [37, -100], zoom: 4, markers: [[40.5, -73.5], [34.05, -118.2, 'blue']],
  }));
  assert.strictEqual(q.markers, '40.5,-73.5|34.05,-118.2,blue');
});

test('marker string passes through', () => {
  const q = query(client().staticMapURL({
    center: [1, 2], zoom: 5, markers: ['40.5,-73.5,red'],
  }));
  assert.strictEqual(q.markers, '40.5,-73.5,red');
});

test('path object becomes the wire form', () => {
  const q = query(client().staticMapURL({
    center: [40.5, -73.5], zoom: 12,
    path: { color: 'ff0000', width: 6, points: [[40.5, -73.5], [40.6, -73.6]] },
  }));
  assert.strictEqual(q.path, 'color:ff0000|width:6|40.5,-73.5|40.6,-73.6');
});

test('path string passes through', () => {
  const q = query(client().staticMapURL({
    center: [1, 2], zoom: 5, path: 'width:3|1,2|3,4',
  }));
  assert.strictEqual(q.path, 'width:3|1,2|3,4');
});

test('auto-fit omits center and zoom', () => {
  const q = query(client().staticMapURL({ markers: [[40.5, -73.5], [34.05, -118.2]] }));
  assert.strictEqual(q.center, undefined);
  assert.strictEqual(q.zoom, undefined);
  assert.strictEqual(q.markers, '40.5,-73.5|34.05,-118.2');
});

test('invalid style throws', () => {
  assert.throws(() => client().staticMapURL({ style: 'satellite', center: [1, 2], zoom: 5 }),
    InvalidRequestError);
});

test('invalid format throws', () => {
  assert.throws(() => client().staticMapURL({ format: 'gif', center: [1, 2], zoom: 5 }),
    InvalidRequestError);
});

test('invalid scale throws', () => {
  assert.throws(() => client().staticMapURL({ scale: 3, center: [1, 2], zoom: 5 }),
    InvalidRequestError);
});

test('bad center throws', () => {
  assert.throws(() => client().staticMapURL({ center: [1, 2, 3], zoom: 5 }),
    InvalidRequestError);
});

test('bad marker throws', () => {
  assert.throws(() => client().staticMapURL({ center: [1, 2], zoom: 5, markers: [[1]] }),
    InvalidRequestError);
});

test('path with one point throws', () => {
  assert.throws(() => client().staticMapURL({ center: [1, 2], zoom: 5, path: { points: [[1, 2]] } }),
    InvalidRequestError);
});
