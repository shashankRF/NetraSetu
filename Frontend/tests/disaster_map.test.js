const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

test('Uttarakhand map has independently switchable dated data overlays and honest unavailable layers', () => {
  for (const layer of ['roads', 'warning', 'landslide']) {
    assert.match(html, new RegExp('data-disaster-layer="' + layer + '"'));
  }
  for (const layer of ['flood', 'fire', 'lower-risk']) {
    assert.match(html, new RegExp('data-disaster-layer="' + layer + '" disabled'));
  }
  assert.match(html, /25 July–25 October 2026/);
  assert.match(html, /Report snapshot 11 Sep 2026/);
  assert.match(html, /District shading counts dated road-closure rows of all causes/);
  assert.match(html, /Unshaded means no matching record in that layer, not “safe”/);
  assert.match(html, /disaster-map-caption/);
});

test('map uses real road basemap, authenticated dated-data API, citations and source-timestamped detail cards', () => {
  assert.match(html, /tile\.openstreetmap\.org\/\{z\}\/\{x\}\/\{y\}\.png/);
  assert.match(html, /OpenStreetMap contributors/);
  assert.match(html, /apiFetch\('\/api\/disaster-map\/data'/);
  for (const field of ['event_date', 'reported_date', 'alert_date', 'published_date', 'source_url', 'location_precision']) {
    assert.match(html, new RegExp(field));
  }
  assert.match(html, /No public event geometry verified for this window/);
  assert.match(html, /Browse all /);
});

test('demo markers are removed and remaining inline scripts parse', () => {
  assert.doesNotMatch(html, /DEMO MARKERS — NOT OBSERVED OR VERIFIED INCIDENTS|disasterMapSetDemos|demo_features|Demo flood marker/);
  assert.doesNotMatch(html, /data-dash-panel="terrain"|data-dash-view="terrain"|api\/terrain\/|terrainRunEvaluation|HG-TERRAIN-009/);
  const blocks = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)];
  for (const [, attrs, code] of blocks) {
    if (/\bsrc\s*=/.test(attrs) || /application\/ld\+json/.test(attrs)) continue;
    new vm.Script(code, { filename: 'Frontend/index.html inline script' });
  }
});

test('aftermath system is integrated only into Uttarakhand map with backend API and controls wired', () => {
  assert.match(html, /data-dash-panel="disaster-map"[\s\S]*?id="aftermath-title"/);
  assert.match(html, /if\(view==='disaster-map'\) \{ disasterMapLoad\(\); aftermathLoad\(\); \}/);
  assert.match(html, /aftermathBind\(\);dashLoadScenarios\(\)/);
  assert.match(html, /api\/aftermath/);
  for (const control of ['aftermath-scenario-select', 'aftermath-compare', 'aftermath-network-run', 'aftermath-reset', 'aftermath-asset-search', 'aftermath-asset-status', 'aftermath-asset-category', 'aftermath-asset-severity', 'aftermath-asset-area']) {
    assert.match(html, new RegExp('id="' + control + '"'));
  }
  assert.match(html, /window\.location\.pathname\.indexOf\('\/frontend\/'\) === 0 \? window\.location\.origin/);
  assert.match(html, /Verify the configured backend host and port/);
  assert.match(html, /aftermath\\\/\|audits/);
});
