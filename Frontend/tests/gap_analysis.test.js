const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const start = html.indexOf('var dashGapOpenItems=[];');
const end = html.indexOf('function dashRenderGovernance()', start);
assert.notEqual(start, -1, 'gap analysis renderer must exist');
assert.notEqual(end, -1, 'gap analysis renderer block must end before governance rendering');

function makeRenderer(pipeline, evidence = []) {
  const host = { innerHTML: '' };
  const state = { latest: { record: { audit_id: 'AUD-gap-test' } }, persistedRecord: null };
  const context = {
    dashState: state,
    dashGetPipeline: () => pipeline,
    dashGetEvidence: () => evidence,
    dashCitationCard: (ev, _subject, label) => `<article>${label} ${JSON.stringify(ev)}</article>`,
    dashDocData: () => ({}),
    escapeHtml: (value) => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    $: (id) => id === 'dash-gap-content' ? host : null,
    Array, String, Set,
  };
  vm.createContext(context);
  vm.runInContext(`${html.slice(start, end)}\nglobalThis.renderGap = dashRenderGapAnalysis;`, context);
  return { render: context.renderGap, host };
}

test('renders contradicting evidence without throwing and preserves its classification', () => {
  const evidence = {
    evidence_id: 'EV-CONTRA-17',
    source_title: 'Emergency Telecom Restoration Report',
    citation: 'page 12, lines 4–8',
  };
  const { render, host } = makeRenderer({
    audit_id: 'AUD-gap-test',
    evidence_analysis: { contradicting_evidence: [evidence] },
    counter_evidence: [],
  });

  assert.doesNotThrow(() => render());
  assert.match(host.innerHTML, /Classified as contradicting:<\/strong> 1/);
  assert.match(host.innerHTML, /Counter-evidence passage/);
  assert.match(host.innerHTML, /Pipeline classified as contradicting/);
  assert.match(host.innerHTML, /EV-CONTRA-17/);
});

test('joins a source passage to its backend-verified exact clause, quote, and line metadata', () => {
  const rawEvidence = { evidence_id: 'EV-CITE-1', title: 'Emergency Communications Rules', text: 'Source passage from retrieval.' };
  const quote = 'The authority shall maintain emergency communication services.';
  const structured = {
    source_title: 'Emergency Communications Rules',
    source_doc_id: 'DOC-EMERGENCY-1',
    local_viewer_url: '/api/documents/raw/emergency-rules.pdf#page=12',
    verification_status: 'EXACT_MATCH_VERIFIED',
    exact_source_quote: quote,
    source_line_numbers: [18],
    citation: {
      document_name: 'Emergency Communications Rules',
      document_id: 'DOC-EMERGENCY-1',
      clause: 'Rule 3(1)(b) — Emergency communications',
      rule_identifier: '3',
      rule_title: 'Emergency communications',
      subclause: '(1)(b)',
      physical_pdf_page: 12,
      source_line_numbers: [18],
      exact_statement: quote,
      verification_status: 'EXACT_MATCH_VERIFIED',
      verification_detail: 'Verbatim passage matched in the source PDF.',
    },
  };
  const pipeline = {
    audit_id: 'AUD-gap-test',
    claim_evidence_mappings: [{ evidence_ids: ['EV-CITE-1'], structured_evidence: structured }],
  };
  const { render, host } = makeRenderer(pipeline, [rawEvidence]);

  render();
  assert.match(host.innerHTML, /Rule 3\(1\)\(b\) — Emergency communications/);
  assert.match(host.innerHTML, /The authority shall maintain emergency communication services\./);
  assert.match(host.innerHTML, /18/);
  assert.match(host.innerHTML, /EXACT_MATCH_VERIFIED/);
  assert.match(host.innerHTML, /Emergency Communications Rules/);
});


test('human review does not solicit or transmit guessed ministry accountability', () => {
  const panel = html.slice(html.indexOf('id="dash-human-review"'), html.indexOf('</div>', html.indexOf('id="dash-human-review"')));
  assert.doesNotMatch(panel, /dash-accountable-authority|Accountable Government ministry \/ agency<input/i);
  assert.match(panel, /Accountability from cited evidence/);
  assert.match(html, /Accountability: not retrieved from cited evidence/);
  const submitStart = html.indexOf('async function dashSubmitReview(');
  const submitEnd = html.indexOf(String.fromCharCode(10), submitStart);
  const submitFunction = html.slice(submitStart, submitEnd);
  assert.doesNotMatch(submitFunction, /accountable_authority|dash-accountable-authority/);
});
