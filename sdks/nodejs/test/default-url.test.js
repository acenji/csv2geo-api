// URL-lock unit tests.
//
// These tests do NOT hit the network. They guard the single class of bug
// that broke the v1.1.x SDK: the default base URL pointing at the internal
// Go service (api.csv2geo.com/v1) instead of the customer-facing Laravel
// proxy (csv2geo.com/api/v1). A geo_live_* key never validates against
// the internal service, so a bad default would 401 every customer install.
//
// Locking the value here means any future change to the constant fails
// CI before it can ship to npm.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const { Client } = require('../src/index');

const CUSTOMER_BASE_URL = 'https://csv2geo.com/api/v1';

test('default base URL points at the customer-facing Laravel proxy', () => {
  const c = new Client('dummy_key_for_unit_test');
  assert.strictEqual(
    c.baseUrl,
    CUSTOMER_BASE_URL,
    `baseUrl drifted to ${c.baseUrl} — customer keys (geo_live_*) only ` +
      `validate against ${CUSTOMER_BASE_URL}. If you genuinely meant to ` +
      `point at the internal Go service, pass {baseUrl: ...} when ` +
      `constructing Client; do not change the default.`
  );
});

test('explicit baseUrl override is honored', () => {
  const c = new Client('dummy', { baseUrl: 'https://my-proxy.example.com/v1' });
  assert.strictEqual(c.baseUrl, 'https://my-proxy.example.com/v1');
});

test('baseUrl trailing slash is normalized', () => {
  const c = new Client('dummy', { baseUrl: 'https://example.com/v1/' });
  assert.strictEqual(c.baseUrl, 'https://example.com/v1');
});

test('User-Agent header matches package.json version', () => {
  // Read the package.json version
  const pkg = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8')
  );
  // The User-Agent is set inside _request, not on construction. Re-read
  // the source to extract it at the constant level (no live request).
  const src = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'index.js'),
    'utf8'
  );
  const m = src.match(/'User-Agent':\s*'csv2geo-node\/(\d+\.\d+\.\d+)'/);
  assert.ok(m, 'User-Agent header missing or malformed in src/index.js');
  assert.strictEqual(
    m[1],
    pkg.version,
    `User-Agent version ${m[1]} does not match package.json ${pkg.version}`
  );
});

test('source must not contain api.csv2geo.com (the internal Go host)', () => {
  // Defensive — catches accidental future drift back to the wrong host
  // anywhere in the SDK source/types/readme.
  const filesToScan = [
    path.join(__dirname, '..', 'src', 'index.js'),
    path.join(__dirname, '..', 'src', 'index.d.ts'),
  ];
  for (const f of filesToScan) {
    const content = fs.readFileSync(f, 'utf8');
    assert.ok(
      !content.includes('api.csv2geo.com'),
      `${f} mentions api.csv2geo.com — that's the internal Go service ` +
        `which only honors sk_test_* keys. Customer SDK must use ` +
        `csv2geo.com/api/v1. This regression would 401 every install.`
    );
  }
});
