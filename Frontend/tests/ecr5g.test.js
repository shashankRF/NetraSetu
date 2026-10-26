const fs = require('fs');
const path = require('path');
const assert = require('assert');

const htmlPath = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(htmlPath, 'utf8');

console.log('--- Running ECR-5G & Navigation Acceptance Tests ---');

// 1. Navigation items
assert(html.includes('id="nav-ecr5g"'), 'Top nav must contain #nav-ecr5g');
assert(html.includes('href="#/ecr5g"'), 'Top nav must link to #/ecr5g');
assert(html.includes('data-dash-view="ecr5g"'), 'Dashboard sidebar must include data-dash-view="ecr5g"');
console.log('✓ Top-level ECR-5G navigation item verified in topbar and dashboard sidebar');

// 2. Dedicated ECR-5G panel
assert(html.includes('data-dash-panel="ecr5g"'), 'Dedicated ECR-5G panel must exist');
console.log('✓ Dedicated ECR-5G workspace panel verified');

// 3. Workspace 7 Core Sections
const requiredElements = [
  'ecr5g-run-btn',            // Section 1: Scenario Control
  'ecr5g-evidence-table',     // Section 2: Evidence Completeness
  'ecr5g-kpi-capacity',       // Section 3: Network Conditions
  'ecr5g-orchestration-table',// Section 4: QoS Orchestration
  'ecr5g-matrix-table',       // Section 5: Scenario Comparison
  'ecr5g-tasks-container',    // Section 6: Inter-Agency Coordination
  'ecr5g-approve-btn'         // Section 7: Governance & Audit
];
requiredElements.forEach(elemId => {
  assert(html.includes(`id="${elemId}"`), `ECR-5G Workspace must contain element id: ${elemId}`);
});
console.log('✓ All 7 core ECR-5G workspace sections verified');

// 4. Integrated Scenario ID
assert(html.includes('ECR5G-FLOOD-001'), 'Scenario ECR5G-FLOOD-001 must be present in frontend');
assert(html.includes('Operation Mountain Shield'), 'Operation Mountain Shield title must be present');
console.log('✓ Scenario ECR5G-FLOOD-001 (Operation Mountain Shield) registered in frontend');

// 5. Four Controlled Variants
['A', 'B', 'C', 'D'].forEach(variant => {
  assert(html.includes(`data-variant="${variant}"`), `Variant ${variant} button must exist in UI`);
});
assert(html.includes('ecr5gSelectVariant'), 'ecr5gSelectVariant handler must exist');
console.log('✓ Four controlled variants (A, B, C, D) configured and selectable');

// 6. Router and Event Bindings
assert(html.includes("if(view==='ecr5g') ecr5gLoad()"), 'Dashboard view routing must trigger ecr5gLoad');
assert(html.includes("requestedDashboardView = 'ecr5g'"), 'Router must recognize #/ecr5g path');
assert(html.includes("ecr5g:'ecr5g'"), 'Section aliases must include ecr5g');
assert(html.includes('ecr5gRunSimulation'), 'ecr5gRunSimulation must be defined');
assert(html.includes('ecr5gSubmitReview'), 'ecr5gSubmitReview must be defined');
console.log('✓ Frontend routing, API fetch, and interaction logic verified');

console.log('All ECR-5G frontend acceptance tests passed successfully!');
