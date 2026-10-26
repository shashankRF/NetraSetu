const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const server = fs.readFileSync(path.join(__dirname, '..', '..', 'Backend', 'server.py'), 'utf8');

test('p95 chart loads stored runs from the registered failure-combination API', () => {
  assert.match(html, /apiFetch\('\/api\/5g\/failure-combinations\?limit=20'/);
  assert.match(server, /@app\.get\("\/api\/5g\/failure-combinations"\)/);
});

test('p95 chart uses the stored scenario metric when older runs lack a detailed report', () => {
  assert.match(html, /row\.metrics&&row\.metrics\.tail_latency_p95_ms/);
  assert.match(html, /stored simulator p95 metric/);
  assert.match(html, /sample count not stored/);
  assert.match(html, /No stored scenario p95 values are available/);
});
