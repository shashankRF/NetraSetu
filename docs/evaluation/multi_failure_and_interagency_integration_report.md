# Multi-Failure, Governance, Evidence, and Coordination Integration

## Summary

The Failure Combination Lab now connects each completed synthetic combination to the existing deterministic `Backend.risk_engine.RiskEngine`, exposes jurisdiction-scoped evidence retrieval and exact-quote verification, enforces a server-side review gate, creates four recipient-specific simulated coordination messages, and persists the complete linked run in the existing append-only audit and run JSONL stores. Existing simulator and API fields remain available; additions are backward-compatible.

No network action or external agency message is sent. No dependency/cascade graph was added because the simulator has no defensible topology or geographic inputs.

## Data flow

**Before:** the combination engine returned synthetic metrics and an audit summary, while describing evidence as not retrieved; it did not invoke the Risk & Governance Engine or create scenario-derived agency messages.

**After:** the authenticated, CSRF-protected POST runs the existing bounded combination engine → optionally retrieves passages through existing jurisdiction-scoped BGE-M3/FAISS retrieval and verifies quotes with the existing PyMuPDF clause verifier → creates a typed simulation provenance record for each successful result → calls the real deterministic RiskEngine → marks failed rows `NOT_EVALUATED` and insufficient evidence `BLOCKED`/review-required → derives four agency messages from the highest-risk run result (ties use packet loss and p95 latency) → appends the full result and request to the existing audit record and appends the run to the existing simulation JSONL store. GET run/list responses overlay the latest persisted review event.

The new audit record hash is recalculated after the full integration payload is attached. Its embedded run ID, run store ID, scenario case IDs, citations, risk results, review status, and transport transitions are linked and reconstructable.

## Changes

- `Backend/server.py`: request fields for scenario, jurisdiction, explicit governance context, and simulated link conditions; integration orchestration; complete persistence; review overlays; recovery metric semantics.
- `Backend/telemetry_5g/governance_integration.py`: typed simulation input, optional retrieval and quote verification, and adapter to the existing RiskEngine.
- `Backend/telemetry_5g/coordination.py`: agency-specific message mapping and deterministic local delivery state machine.
- `Backend/telemetry_5g/engine.py` and `combination_engine.py`: additive `simulated_post_impairment_interval_ms` metric alias.
- `Backend/audit_api.py`: reviewer identity from the authenticated session; APPROVED/MODIFIED is blocked for simulation records while evidence applicability is unestablished.
- `Frontend/index.html`: jurisdiction/scenario/transport controls, per-row risk and review display, truthful evidence/recovery language, and coordination views sourced from saved simulation messages.
- `Backend/tests/test_failure_combination_engine.py`, `Backend/tests/test_5g_and_architecture_decisions.py`, `Backend/tests/test_failure_governance_integration.py`: API, persistence, risk, citation pass-through, review, transport, and metric-semantics coverage.

## Risk, evidence, and review

Each completed simulation row invokes the real `RiskEngine.assess()` with the engine’s typed `DecisionContext`, `EvidenceAssessment`, and `AIAnalysis`. Risk context values come from explicit request fields or documented defaults. Latency, loss, delivery, profile checks, and user-defined thresholds remain synthetic observations and are recorded with units/provenance; they are not silently converted into consequence scores, safety findings, or legal conclusions because the existing risk schema has no telemetry metric fields. Accordingly, the risk engine may return the same score for cases with different metrics when their explicit context and evidence state are the same.

With no jurisdiction, evidence is `EVIDENCE_PENDING` and retrieval is not attempted. With a supported jurisdiction, the adapter calls the existing retrieval interface and verifies each passage with the existing PDF clause verifier. Retrieval, quote verification, and legal/operational applicability are kept separate. Verification outcomes and citation metadata are retained; applicability remains `NOT_ASSESSED`. A retrieval error becomes `UNAVAILABLE`, and zero results becomes `NO_RESULTS`; neither means the requirement is absent or the system is safe.

The adapter currently supplies `INSUFFICIENT` evidence to the RiskEngine because the workflow does not establish that retrieved requirements apply to synthetic measurements. The engine’s actual blocking condition and mandatory human-review output are returned. The review API derives identity from the authenticated session and rejects APPROVED/MODIFIED transitions for these records; rejection, investigation, escalation, or deferral remain recorded review outcomes. There is one configured administrator identity in the current application, not separate agency roles or a multi-user authorization registry.

## Coordination and recovery semantics

Four demo-role messages share a source run and selected simulation case but contain recipient-specific content. They include simulation provenance, UTC message-creation time, risk/review status, citation references when exactly verified, and transport transitions. The dashboard no longer seeds unrelated example messages; it displays messages from the latest stored run and synchronizes scenario context to that run. Local user-composed messages remain browser-local.

Transport modes cover available, delayed, unavailable, expired, retry-queued, and reconnect-and-acknowledge paths. These are deterministic state transitions, not a telecom protocol, measured timing, or external delivery. Every message explicitly has `external_delivery: false`.

The legacy `recovery_time_ms` field remains for compatibility. The new `simulated_post_impairment_interval_ms` alias and explanatory metadata describe the existing calculation: elapsed synthetic time from the fixed impairment window to the first healthy generated sample (or the end of generated samples). It is not operator repair or service-restoration time. Profile thresholds using the legacy field name are likewise documented as simulator comparisons.

## Scope table

| Capability | Status |
|---|---|
| Combination output reaches deterministic RiskEngine | Implemented for completed rows; failed rows are explicitly not evaluated |
| Jurisdiction-scoped BGE-M3/FAISS retrieval and PDF quote verification | Integrated; no-jurisdiction, unavailable, no-result, and per-citation outcomes remain distinct |
| Legal/operational applicability of retrieved sources to synthetic metrics | Not assessed; evidence remains insufficient for approval |
| Authenticated human review record | Implemented through existing session and append-only review/audit stores; APPROVED/MODIFIED blocked for these insufficient-evidence simulation records |
| Inter-agency notifications | Simulated, recipient-specific, sourced from the selected actual run result |
| Delivery outage/retry/reconnection | Deterministic local state model; not real transport |
| Geographic/topological cascading failures | Unsupported and intentionally not mocked |
| Operational network action or agency authorization | Not implemented; no action is executed or authorized |

## Verification

Python environment: repository root in `PYTHONPATH`; `NETRASETU_TESTING=1` prevents application startup model prewarming during tests.

Commands and observed results:

- `pytest -q Backend/tests/test_failure_combination_engine.py Backend/tests/test_5g_and_architecture_decisions.py Backend/tests/test_failure_governance_integration.py` — **18 passed**, 3 deprecation warnings (Starlette/httpx TestClient and FastAPI `on_event` startup hook).
- `pytest -q Backend/tests/test_risk_engine.py Backend/tests/test_governance_rules.py Backend/tests/test_governance_invariants.py Backend/tests/test_evidence_engine.py Backend/tests/test_evidence_engine_integration.py Backend/tests/test_source_clause_verification.py` — **26 passed**.
- `python -m py_compile` on the changed Python modules and test modules — passed.
- `node --check` on the three inline scripts in `Frontend/index.html` — passed after the final coordination-context update.

The passing API assertions verify that every completed row returns the actual engine output, the serialized risk score/level match a direct `RiskEngine` calculation, the integration record contains the full run and four messages, the content-derived audit ID is stable, approval is rejected, authenticated reviewer identity overrides a caller-supplied label, and review overlays appear on GET. The citation test verifies that retrieval metadata and an exact clause/page result pass through while applicability stays `NOT_ASSESSED`. The transport tests cover available acknowledgement, delayed expiry, unavailable failure, and queued delivery after reconnection.

Representative values observed/asserted from the local API test (generated IDs and measured synthetic metrics omitted):

```json
{
  "run_status": "COMPLETED",
  "evidence_status": "EVIDENCE_PENDING",
  "risk_engine": "Backend.risk_engine.RiskEngine",
  "review_gate": "BLOCKED",
  "coordination_message_count": 4,
  "external_delivery": false,
  "approval_http_status": 409,
  "review_action": "REJECTED"
}
```

The citation pass-through test uses a controlled retrieved row and verifier result; existing PDF/citation regression tests exercise the local verifier. A live jurisdiction-scoped multi-failure request against BGE-M3/FAISS was not run in this test pass.

The initial focused test attempt without `PYTHONPATH` failed collection (`ModuleNotFoundError: Backend`). One initial pytest process also stalled during startup model prewarming and was manually interrupted; a later run overlapped a source edit and two API calls returned 500. After setting `NETRASETU_TESTING=1` and stabilizing the source, the final targeted command above passed. The final process check found no pytest, Python, or Uvicorn process and no listener on port 8000. The full repository suite was not run because several existing audit tests append to the shared audit JSONL file, which was already modified before this task; the opt-in live Groq check was not enabled. No before-change baseline for this integration was established in this turn because the work began with partially created integration files. Earlier project runs recorded in the prior task are not treated as a clean baseline for this change.

## Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:NETRASETU_TESTING = '1'
pytest -q Backend/tests/test_failure_combination_engine.py Backend/tests/test_5g_and_architecture_decisions.py Backend/tests/test_failure_governance_integration.py
```

For the evidence/risk regression subset, run the second pytest command listed above. To exercise retrieval from the app, submit a failure-combination request with `jurisdiction` set to a supported value (`India` or `European Union`); inspect `integration.evidence.sources` for exact citation verification fields and keep `applicability: NOT_ASSESSED` distinct from quote verification.

## Answers to the requested completion checks

- **Does every tested multi-failure run reach the real Risk & Governance Engine?** Every completed row in the tested API run did; failed rows are marked `NOT_EVALUATED`.
- **What triggers human review or blocking?** The RiskEngine’s actual insufficient/conflicting/ambiguous evidence and escalation rules. In this integration, applicability remains unestablished, so evidence is insufficient and APPROVED/MODIFIED review actions are blocked.
- **Is evidence retrieved and verified, or marked unavailable?** It is pending when jurisdiction is omitted; with jurisdiction it is retrieved and each quote-verification result is preserved, or explicitly marked unavailable/no-results. Existing evidence applicability is not inferred.
- **Are agency messages derived from actual simulation results?** Yes. They are generated from the selected completed result, its metrics, failure set, risk/evidence state, and scenario/case IDs.
- **Does coordination respond to outages?** Yes, in a deterministic synthetic state model that represents delay, retries, expiry, and reconnect acknowledgement; no external recipient is contacted.
- **Are audit records reconstructable?** Yes. The full request and run are persisted in the append-only audit record and the run JSONL store; the test checks their linked run ID and review overlay.
- **What remains unsupported?** Applicable-requirement decisions, role separation among agencies, real delivery, operational execution, and geographic/topological cascade analysis.
- **Which results are synthetic vs. software-test observations?** All network metrics, incident severity narratives, and transport timing are synthetic. Pass/fail counts, endpoint status codes, RiskEngine outputs, citation-verifier outcomes, audit persistence, and review transitions are observations from local software tests.
