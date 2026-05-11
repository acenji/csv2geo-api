// Sprint 2.4 — unit tests for the 7 routing SDK methods.
//
// No network. Monkey-patches client._request to capture (method, path,
// params, body) and asserts on those. Pairs with the Python SDK test file.

const test = require('node:test');
const assert = require('node:assert');
const { Client, InvalidRequestError } = require('../src/index');

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
// /v1/routing
// ─────────────────────────────────────────────────────────

test('route() formats tuple waypoints and sends GET /routing', async () => {
  const c = makeStubClient();
  await c.route([[40.7128, -74.006], [34.0522, -118.2437]], { mode: 'drive' });
  const call = c.captured[0];
  assert.strictEqual(call.method, 'GET');
  assert.strictEqual(call.path, '/routing');
  assert.strictEqual(call.params.waypoints, '40.7128,-74.006|34.0522,-118.2437');
  assert.strictEqual(call.params.mode, 'drive');
});

test('route() passes string waypoints through unchanged', async () => {
  const c = makeStubClient();
  await c.route('40.7,-74|34,-118.2', { mode: 'walk' });
  assert.strictEqual(c.captured[0].params.waypoints, '40.7,-74|34,-118.2');
  assert.strictEqual(c.captured[0].params.mode, 'walk');
});

test('route() sends truck attrs when provided', async () => {
  const c = makeStubClient();
  await c.route([[40.7, -74.0], [34.0, -118.2]], {
    mode: 'truck', truckHeight: 4.0, truckWeight: 20000,
    truckLength: 15, truckWidth: 2.5, truckHazmat: true,
  });
  const p = c.captured[0].params;
  assert.strictEqual(p.truck_height, 4.0);
  assert.strictEqual(p.truck_weight, 20000);
  assert.strictEqual(p.truck_length, 15);
  assert.strictEqual(p.truck_width, 2.5);
  assert.strictEqual(p.truck_hazmat, 'true');
});

test('route() omits truck attrs when not provided', async () => {
  const c = makeStubClient();
  await c.route([[40.7, -74.0], [34.0, -118.2]], { mode: 'drive' });
  const p = c.captured[0].params;
  for (const k of ['truck_height','truck_weight','truck_length','truck_width','truck_hazmat']) {
    assert.strictEqual(p[k], undefined, `${k} leaked into params`);
  }
});

test('route() alternates + instructions + lang', async () => {
  const c = makeStubClient();
  await c.route([[40.7, -74.0], [34.0, -118.2]], {
    mode: 'drive', alternatives: 2, instructions: true, lang: 'de',
  });
  const p = c.captured[0].params;
  assert.strictEqual(p.alternatives, 2);
  assert.strictEqual(p.instructions, 'true');
  assert.strictEqual(p.lang, 'de');
});

test('route() rejects malformed waypoints', async () => {
  const c = makeStubClient();
  await assert.rejects(
    () => c.route([[40.7]], { mode: 'drive' }),
    InvalidRequestError
  );
});

test('route() format=polyline', async () => {
  const c = makeStubClient();
  await c.route([[40.7, -74.0], [34.0, -118.2]], { mode: 'drive', format: 'polyline' });
  assert.strictEqual(c.captured[0].params.format, 'polyline');
});

// ─────────────────────────────────────────────────────────
// /v1/isoline
// ─────────────────────────────────────────────────────────

test('isoline() with array of ranges', async () => {
  const c = makeStubClient();
  await c.isoline({ lat: 40.7, lng: -74.0, mode: 'drive', ranges: [300, 600, 900] });
  const call = c.captured[0];
  assert.strictEqual(call.path, '/isoline');
  assert.strictEqual(call.params.ranges, '300,600,900');
  assert.strictEqual(call.params.type, 'time');
});

test('isoline() with distance type', async () => {
  const c = makeStubClient();
  await c.isoline({ lat: 34.05, lng: -118.24, mode: 'walk', ranges: [1000, 2000], type: 'distance' });
  assert.strictEqual(c.captured[0].params.type, 'distance');
  assert.strictEqual(c.captured[0].params.ranges, '1000,2000');
});

test('isoline() requires lat/lng/mode/ranges', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.isoline({ lng: -74.0, mode: 'drive', ranges: [300] }), InvalidRequestError);
  await assert.rejects(() => c.isoline({ lat: 40.7, mode: 'drive', ranges: [300] }), InvalidRequestError);
  await assert.rejects(() => c.isoline({ lat: 40.7, lng: -74.0, ranges: [300] }), InvalidRequestError);
  await assert.rejects(() => c.isoline({ lat: 40.7, lng: -74.0, mode: 'drive' }), InvalidRequestError);
});

// ─────────────────────────────────────────────────────────
// /v1/route-matrix
// ─────────────────────────────────────────────────────────

test('routeMatrix() with dict sources/targets', async () => {
  const c = makeStubClient();
  await c.routeMatrix({
    sources: [{ lat: 40.7, lng: -74.0 }],
    targets: [{ lat: 34.0, lng: -118.2 }, { lat: 29.7, lng: -95.3 }],
    mode: 'drive',
  });
  const call = c.captured[0];
  assert.strictEqual(call.method, 'POST');
  assert.strictEqual(call.path, '/route-matrix');
  assert.deepStrictEqual(call.body.sources, [{ lat: 40.7, lng: -74.0 }]);
  assert.deepStrictEqual(call.body.targets, [{ lat: 34.0, lng: -118.2 }, { lat: 29.7, lng: -95.3 }]);
  assert.strictEqual(call.body.mode, 'drive');
});

test('routeMatrix() with tuple sources/targets', async () => {
  const c = makeStubClient();
  await c.routeMatrix({
    sources: [[40.7, -74.0]],
    targets: [[34.0, -118.2]],
    mode: 'walk',
  });
  assert.deepStrictEqual(c.captured[0].body.sources, [{ lat: 40.7, lng: -74.0 }]);
  assert.deepStrictEqual(c.captured[0].body.targets, [{ lat: 34.0, lng: -118.2 }]);
});

test('routeMatrix() rejects empty sources or targets', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.routeMatrix({ sources: [], targets: [[34.0, -118.2]], mode: 'drive' }), InvalidRequestError);
  await assert.rejects(() => c.routeMatrix({ sources: [[40.7, -74.0]], targets: [], mode: 'drive' }), InvalidRequestError);
});

test('routeMatrix() truck attrs + include filter', async () => {
  const c = makeStubClient();
  await c.routeMatrix({
    sources: [[40.7, -74.0]], targets: [[34.0, -118.2]], mode: 'truck',
    truckHeight: 4.0, truckHazmat: true, include: ['durations'],
  });
  const b = c.captured[0].body;
  assert.strictEqual(b.truck_height, 4.0);
  assert.strictEqual(b.truck_hazmat, true);
  assert.deepStrictEqual(b.include, ['durations']);
});

// ─────────────────────────────────────────────────────────
// /v1/map-match
// ─────────────────────────────────────────────────────────

test('mapMatch() with tuple trace', async () => {
  const c = makeStubClient();
  await c.mapMatch({ trace: [[40.7128, -74.006], [40.7130, -74.0058]], mode: 'drive' });
  const call = c.captured[0];
  assert.strictEqual(call.method, 'POST');
  assert.strictEqual(call.path, '/map-match');
  assert.deepStrictEqual(call.body.trace, [
    { lat: 40.7128, lng: -74.006 },
    { lat: 40.7130, lng: -74.0058 },
  ]);
});

test('mapMatch() preserves time + accuracy_m', async () => {
  const c = makeStubClient();
  await c.mapMatch({
    trace: [
      { lat: 40.7, lng: -74.0, time: '2026-05-11T14:00:00Z', accuracy_m: 5 },
      { lat: 40.71, lng: -74.01, time: '2026-05-11T14:00:05Z', accuracy_m: 5 },
    ],
    mode: 'drive',
    gpsAccuracyM: 5,
  });
  const trace = c.captured[0].body.trace;
  assert.strictEqual(trace[0].time, '2026-05-11T14:00:00Z');
  assert.strictEqual(trace[0].accuracy_m, 5);
  assert.strictEqual(c.captured[0].body.gps_accuracy_m, 5);
});

test('mapMatch() rejects trace under 2 points', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.mapMatch({ trace: [[40.7, -74.0]], mode: 'drive' }), InvalidRequestError);
});

// ─────────────────────────────────────────────────────────
// /v1/optimize_route
// ─────────────────────────────────────────────────────────

test('optimizeRoute() basic', async () => {
  const c = makeStubClient();
  await c.optimizeRoute([[40.7, -74.0], [34.0, -118.2], [29.7, -95.3]], { mode: 'drive' });
  const call = c.captured[0];
  assert.strictEqual(call.method, 'GET');
  assert.strictEqual(call.path, '/optimize_route');
  assert.strictEqual(call.params.waypoints, '40.7,-74|34,-118.2|29.7,-95.3');
});

test('optimizeRoute() roundtrip flag', async () => {
  const c = makeStubClient();
  await c.optimizeRoute([[40.7, -74.0], [34.0, -118.2]], { mode: 'drive', roundtrip: true });
  assert.strictEqual(c.captured[0].params.roundtrip, 'true');
});

// ─────────────────────────────────────────────────────────
// /v1/locate
// ─────────────────────────────────────────────────────────

test('locate() basic', async () => {
  const c = makeStubClient();
  await c.locate(40.7128, -74.006);
  const call = c.captured[0];
  assert.strictEqual(call.method, 'GET');
  assert.strictEqual(call.path, '/locate');
  assert.deepStrictEqual(call.params, { lat: 40.7128, lng: -74.006, mode: 'drive' });
});

test('locate() with mode + radius', async () => {
  const c = makeStubClient();
  await c.locate(40.7, -74.0, { mode: 'truck', radiusM: 1000 });
  const p = c.captured[0].params;
  assert.strictEqual(p.mode, 'truck');
  assert.strictEqual(p.radius_m, 1000);
});

test('locate() rejects missing coords', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.locate(null, -74.0), InvalidRequestError);
});

// ─────────────────────────────────────────────────────────
// /v1/elevation
// ─────────────────────────────────────────────────────────

test('elevation() basic', async () => {
  const c = makeStubClient();
  await c.elevation([[40.7, -74.0], [34.0, -118.2]]);
  const call = c.captured[0];
  assert.strictEqual(call.method, 'GET');
  assert.strictEqual(call.path, '/elevation');
  assert.strictEqual(call.params.points, '40.7,-74|34,-118.2');
});

test('elevation() imperial + geojson format', async () => {
  const c = makeStubClient();
  await c.elevation([[40.7, -74.0]], { units: 'imperial', format: 'geojson' });
  const p = c.captured[0].params;
  assert.strictEqual(p.units, 'imperial');
  assert.strictEqual(p.format, 'geojson');
});

// ─────────────────────────────────────────────────────────
// Cross-cutting: all 7 methods exist
// ─────────────────────────────────────────────────────────

test('all 7 routing methods exist on Client prototype', () => {
  const expected = ['route', 'isoline', 'routeMatrix', 'mapMatch', 'optimizeRoute', 'locate', 'elevation'];
  for (const m of expected) {
    assert.strictEqual(typeof Client.prototype[m], 'function', `Client.prototype.${m} missing`);
  }
});
