// /normalize SDK <-> API wire contract (no network). The normalization rules themselves are
// tested in overture-geocoder/api/internal/usps; here we lock what the SDK puts on the wire.

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

test('normalize(string) sends GET /normalize?q=', async () => {
  const c = makeStubClient();
  await c.normalize('123 Stewart Street Northwest, Huntsville AL 35801');
  assert.deepStrictEqual(c.captured[0].method, 'GET');
  assert.strictEqual(c.captured[0].path, '/normalize');
  assert.strictEqual(c.captured[0].params.q, '123 Stewart Street Northwest, Huntsville AL 35801');
});

test('normalize(object) forwards the structured fields', async () => {
  const c = makeStubClient();
  await c.normalize({ address: '9 Elm Ave', city: 'Huntsville', state: 'AL', zip: '35801' });
  assert.deepStrictEqual(c.captured[0].params, { address: '9 Elm Ave', city: 'Huntsville', state: 'AL', zip: '35801' });
});

test('normalizeBatch posts {addresses} to /normalize and keeps ids', async () => {
  const c = makeStubClient();
  const rows = ['1 Oak St', { id: 'r2', address: '2 Pine Rd', zip: '35801' }];
  await c.normalizeBatch(rows);
  assert.strictEqual(c.captured[0].method, 'POST');
  assert.strictEqual(c.captured[0].path, '/normalize');
  assert.deepStrictEqual(c.captured[0].body, { addresses: rows });
});

test('normalizeBatch rejects empty and >1000 before any request', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.normalizeBatch([]));
  await assert.rejects(() => c.normalizeBatch(new Array(1001).fill('a')));
  assert.strictEqual(c.captured.length, 0);
  await c.normalizeBatch(new Array(1000).fill('a'));
  assert.strictEqual(c.captured.length, 1);
});

test('parseBatch limit is 1,000 (the API rejects more)', async () => {
  const c = makeStubClient();
  await assert.rejects(() => c.parseBatch(new Array(1001).fill('a')));
  assert.strictEqual(c.captured.length, 0);
});
