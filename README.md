# NetraSetu

## Evidence Intelligence & Communication Reliability Platform

> **Connecting Evidence. Testing Resilience.**

NetraSetu is an evidence-grounded decision intelligence framework designed to evaluate high-stakes technical, regulatory, and operational questions without ungrounded LLM assumptions. Rather than operating as a conversational chatbot that retrieves passages and directly generates uncalibrated text, NetraSetu enforces an end-to-end reasoning and governance pipeline:

> **EVIDENCE IS THE SOURCE OF TRUTH.**  
> The language model serves strictly as an analytical and synthesis instrument over verified evidence, never as a parametric knowledge store or autonomous decision authority.

## Abstract

Mission-critical systems across telecommunications (5G/O-RAN), maritime navigation, defence infrastructure, and cybersecurity require verifiable, auditable reasoning. Standard Large Language Model (LLM) applications fail in these environments because they confuse retrieval failures with regulatory absence, hallucinate legal citations, collapse distinct national jurisdictions, and treat model recommendations as operational authorizations.

NetraSetu resolves these failure modes by enforcing strict epistemic boundaries: it discovers supporting and counter-evidence across specialized knowledge bases, verifies absence claims through a formal Absence Protocol, performs strict multi-step gap analysis, calculates deterministic risk scores, and gates consequential decisions behind evidence-backed authority boundaries and mandatory human review.

## What NetraSetu Does

NetraSetu provides controlled, evidence-traceable decision support for mission-critical inquiries:
- **Retrieves & Reranks Evidence:** Queries specialized corpora using dense semantic vectors and cross-encoder reranking.
- **Validates & Discovers Counter-Evidence:** Discovers supporting, contradicting, limiting, and contextual evidence roles.
- **Safeguards Against Negative Inferences:** Distinguishes between unretrieved provisions and verified absence (`ABSENCE_NOT_ESTABLISHED`).
- **Executes Strict Gap Analysis:** Refuses to label wording differences as gaps; requires identifiable missing elements and applicability proof.
- **Quantifies Risk Deterministically:** Computes risk tiers (LOW, MODERATE, HIGH, CRITICAL) and escalation levels via deterministic decision matrices.
- **Enforces Authority Boundaries:** Separates operational actors ("WHO SHOULD ACT?") from decision authorities ("WHO CAN DECIDE?").
- **Preserves Root-Cause Uncertainty:** Tracks competing incident hypotheses without fabricating attribution.
- **Enables Verifiable Governance:** Binds decisions to an immutable, append-only audit trail with human review overrides.

## Why It Exists

Conventional RAG pipelines follow an unconstrained path (`Query ──► Top-K Search ──► LLM ──► Uncalibrated Text`), causing critical failures in regulated sectors:
1. **Jurisdiction Collisions:** Blends foreign directives (e.g., EU NIS2) into domestic requirements (e.g., Indian DoT rules).
2. **Confirmation Bias:** Retrieves only passages matching the prompt's phrasing, ignoring contradictory caveats.
3. **False Absence Inferences:** Concludes a regulation does not exist simply because it was absent from top retrieval results.
4. **False Gaps:** Assumes minor wording differences between standards represent compliance gaps.
5. **Autonomous Mission Creep:** Treats an AI recommendation as an operational authorization to execute actions.


## Updated Product Roadmap: Strategic Capabilities

NetraSetu is evolving from a static compliance reasoning tool into an **evidence-grounded intelligence and communication-reliability testing platform**. The roadmap centers around two core planned capabilities:

### Feature A — Change-Impact Engine for Evidence and Requirements (Research Prototype)
* **Objective:** Track revisions in statutory instruments, technical specifications, and guidelines (e.g., CERT-In Directions 2022 vs FAQs, Telecommunications Act 2023 transitions, 3GPP Rel 17 vs Rel 18 5G-Advanced).
* **Core Capabilities:**
  * Clause-level document diffing and lineage tracking.
  * Automated impact mapping linking revised clauses to affected compliance requirements and previous findings.
  * Selective re-evaluation engine that updates only affected finding nodes rather than invalidating the entire corpus.
* **Current Status:** Available as an interactive research prototype workbench (`#/change-impact`) in the refreshed frontend console. Automated continuous diff ingestion backend is scheduled for development Phase 2.

### Feature B — Failure-Combination Discovery Engine for 5G Reliability (Design Prototype)
* **Objective:** Systematically explore multi-dimensional edge failure scenarios and compare communication-recovery strategies across mission-critical wireless infrastructure.
* **Core Capabilities:**
  * Combinatorial impairment matrix: Latency jitter (5–500ms), packet loss rate (0–15%), handover interruption window (0–3000ms), temporary coverage blind spot (0–30s), and radio slice congestion.
  * Service-Level Objective (SLO) targeting: Ultra-Reliable Low-Latency Communication (URLLC), High-Speed Rail (350 km/h) Doppler handover, Maritime coastal store-and-forward, and Smart Grid teleprotection.
  * Resilience strategy benchmarking: Multipath QUIC / Dual PDU Session active-active failover, Aggressive Selective ARQ + packet duplication, and Dynamic Slicing Preemption.
  * Reproducible failure vector generation (standardized JSON test configurations for ns-3 / OMNeT++ / Open5GS simulation).
* **Current Status:** Available as an interactive configuration and strategy comparison prototype (`#/reliability-lab`). Direct hardware-in-the-loop and packet-level emulation backend connections are scheduled for development Phase 2.

---

## Current Architecture

### Uttarakhand Disaster Map

The signed-in dashboard includes an **Uttarakhand Disaster Map** with a MapLibre/OpenStreetMap road basemap, bundled state/district boundaries, layer toggles, district details, and links to the source report for each dated overlay. The map covers **2026-07-25 through 2026-10-25** and was reviewed on **2026-10-25**. The integrated Public Works Department SRMD snapshot is dated **2026-09-11**: 86 table rows list roads marked closed whose closure dates fall within the selected window. Cause and coordinates are not present in the extracted rows, so the choropleth means “PWD road-closure record count by district”; it is not a flood/landslide footprint or a live road status. The curated source rows, date filter, source pages and precision caveat are recorded in `Backend/disaster_map_data/pwd_road_closures_2026-09-11.json`.

The map separately shows USDMA's **2026-09-26 heavy-rain red warning** (page published 2026-09-28) and two GSI Bhooskhalan portal-reported landslides (event dates **2026-08-19** and **2026-09-01**). Those notices identify districts/roads but provide no verified event coordinates or affected polygons, so the overlays outline named districts and state their precision. Flood extents, forest-fire observations, and lower-risk zones remain unavailable/unclassified because no public dated Uttarakhand geometry or supporting risk dataset was verified for this window. This absence does not mean no such incidents occurred. No private NDEM data, undocumented API, or simulated incident is used. OSM tiles are loaded only for the user's interactive viewport, with visible attribution; see the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/). See `Backend/disaster_map_boundaries/metadata.json` for boundary provenance and licence.
```
USER QUESTION / OPERATIONAL INCIDENT
                ↓
       QUERY UNDERSTANDING (Domain & Intent)
                ↓
  JURISDICTION-AWARE RETRIEVAL (BGE-M3 + FAISS)
                ↓
    SEMANTIC RERANKING (BGE-Reranker-v2-M3)
                ↓
PRIMARY EVIDENCE   +   COUNTER-EVIDENCE DISCOVERY
                ↓
       EVIDENCE ROLE CLASSIFICATION
                ↓
        EVIDENCE SUFFICIENCY ENGINE
                ↓
            ABSENCE PROTOCOL
                ↓
          STRICT GAP ANALYSIS
                ↓
       DETERMINISTIC RISK ENGINE
                ↓
   GOVERNANCE & AUTHORITY BOUNDARY GATE
                ↓
   GPT-OSS REASONING & EVIDENCE SYNTHESIS
                ↓
    CLAIM → EVIDENCE TRACEABILITY MAPPING
                ↓
    HUMAN REVIEW (Approve / Modify / Reject)
                ↓
    APPEND-ONLY CRYPTOGRAPHIC AUDIT TRAIL
```

## End-to-End Pipeline

| Pipeline Stage | Function & Invariant | Model / Component |
|---|---|---|
| **0. Intent & Domain** | Classifies domain (Telecom, Maritime, Defence, Cyber) and intent (Incident, Compliance, Gap). | Deterministic Classifier |
| **1. Multi-KB Retrieval** | Retrieves candidates from targeted knowledge bases filtered by jurisdiction profile. | `BAAI/bge-m3` + FAISS |
| **2. Semantic Reranking** | Cross-encoder scores candidate relevance; discovers counter-evidence candidates. | `BAAI/bge-reranker-v2-m3` |
| **3. Evidence Engine** | Classifies evidence into Supporting, Contradicting, Limiting, or Contextual roles. | Deterministic / LLM Classifier |
| **4. Absence Protocol** | Prevents false negative claims; assigns `ABSENCE_NOT_ESTABLISHED` on missing text. | Absence Safeguard Engine |
| **5. Strict Gap Analysis** | Tests requirement applicability, coverage, and missing elements before declaring a gap. | Gap Reasoning Engine |
| **6. Risk Assessment** | Computes 0–100 risk score and escalation tier across operational impact vectors. | Deterministic Risk Engine |
| **7. Governance Gate** | Gates automation: `AUTOMATION PERMITTED`, `LIMITED`, `PROHIBITED`, or `AUTHORITY NOT ESTABLISHED`. | Decision Governance Engine |
| **8. Final Synthesis** | Synthesizes grounded assessment anchored strictly to cited evidence records. | `openai/gpt-oss-120b` (Groq) |
| **9. Claim Mapping** | Maps every substantive output assertion (`CLAIM-xxx`) to evidence IDs (`EV-xxx`). | Provenance Mapper |
| **10. Audit & Review** | Records full state to immutable ledger; awaits authorized human review. | Append-Only Audit Recorder |

## Multi-Knowledge-Base Architecture

NetraSetu indexes domain evidence in isolated, targeted knowledge bases:
- **Main Knowledge Base (14,143 chunks):** Indian DoT Rules, Gazette of India, ETSI/3GPP releases, TEC standards.
- **Defence Knowledge Base (397 chunks):** Tactical communications, UAV datalinks, electronic warfare response, secure C2 specs.
- **Maritime Knowledge Base (273 chunks):** Navigational safety, ECDIS/AIS integrity, SOLAS, port cybersecurity.
- **Total Validated Corpus (14,813 chunks):** 1,024-dimensional dense vectors indexed via FAISS (`IndexFlatIP`).

> *Note: The indexed corpus represents the evidence available to the prototype. It is not an exhaustive legal or regulatory database.*

## Query Understanding

Inputs are analyzed for domain context and intent to configure downstream retrieval quotas and validation rules:
- **Domains:** Telecom / 5G, Defence, Maritime, Policy / Compliance, Research, Enterprise Cyber Incident, General Evidence Analysis.
- **Intents:** Incident Analysis, Threat Analysis, Root Cause Analysis, Compliance, Policy Gap, Research Gap, Evidence Assessment, General Analysis.

## Jurisdiction-Aware Reasoning

Jurisdiction governs evidence applicability, not merely display filtering:
- **India:** Retrieves Indian statutory acts, gazette notifications, and TEC standards, crosswalked against international technical specifications.
- **European Union:** Retrieves EU directives, ENISA frameworks, and GDPR/NIS2 standards, crosswalked against international specifications.
- **International / Standards:** 3GPP releases, ITU-T recommendations, ETSI specifications, and IEEE standards.

**Regulatory Invariants:** International standard $\neq$ national statutory law; divergent terminology $\neq$ regulatory conflict; additional national requirement $\neq$ compliance failure; never silently cross-apply provisions across distinct jurisdictions.

## Retrieval and Semantic Reranking

1. **Candidate Retrieval:** Queries generate 1,024-dimensional dense embeddings via `BAAI/bge-m3`, searching FAISS vector spaces under strict jurisdiction filters.
2. **Cross-Encoder Reranking:** Candidate passages are reranked via `BAAI/bge-reranker-v2-m3` to isolate top primary evidence records. Retrieval identifies candidate evidence; retrieval alone does not establish conclusions.

## Primary and Counter-Evidence

NetraSetu pairs every retrieval with active counter-evidence discovery:
- **PRIMARY / SUPPORTING EVIDENCE:** Surfaces passages directly supporting the inquiry hypothesis.
- **COUNTER / LIMITING EVIDENCE:** Actively searches for contradictions, exceptions, limitations, and exclusions.
- **Evidence Roles:** `SUPPORTING`, `CONTRADICTING`, `LIMITING`, `CONTEXTUAL`. NetraSetu does not become more confident simply because supporting evidence exists.

## Evidence Sufficiency

Evidence is evaluated across four orthogonal dimensions:
- **Evidence Status:** `SUFFICIENT`, `CONFLICTING`, `PARTIALLY ESTABLISHED`, `INSUFFICIENT`, `AMBIGUOUS`, `ABSENCE_NOT_ESTABLISHED`, `NOT_APPLICABLE`.
- **Evidence Strength:** `STRONG`, `MODERATE`, `WEAK`, `INSUFFICIENT`.
- **Source Authority & Diversity:** Distinguishes binding statutory gazettes from advisory documentation. High AI confidence does not override weak evidence.

## Absence Protocol

The Absence Protocol enforces epistemic safety:
- Never infer: *"No relevant regulation was retrieved, therefore the regulation does not exist."*
- Instead assign: `ABSENCE_NOT_ESTABLISHED`. Failure to retrieve an authoritative provision does not establish that the provision does not exist.

## Strict Gap Analysis

NetraSetu rejects naive text diffing. Wording variations, structural differences, differing abstraction levels, additional national mandates, or unretrieved text do **not** constitute a gap.

```
Technical Requirement ──► Jurisdiction Applicability ──► National Provision ──► Identifiable Missing Element ──► Gap Status ──► Remediation
```

- **Classifications:** `COVERED`, `PARTIALLY COVERED`, `ADDITIONAL NATIONAL REQUIREMENT`, `CONFLICT`, `NOT APPLICABLE`, `INSUFFICIENT EVIDENCE`, `POTENTIAL GAP — NOT ESTABLISHED`, `ESTABLISHED GAP`.
- **Remediation Actions:** `FIX`, `VERIFY`, `INVESTIGATE`, `NO ACTION`.

## Regulatory Reasoning Safeguards

NetraSetu strictly separates: (1) Technical Requirements, (2) Regulatory Mandates, (3) Incident Reporting Obligations, and (4) Decision Authorities. A detected incident does not automatically imply a mandatory reporting duty; reporting triggers require evidence establishing jurisdiction, mandatory status, and legal thresholds. If authority is unproven: `"Authority not established by supplied evidence."`

## Risk Assessment

Risk is calculated deterministically across operational impact, consequence severity, and evidence quality:
- **LOW (0–29):** Informational analysis; minimal operational consequence.
- **MODERATE (30–59):** Advisory adjustments; standard operational monitoring.
- **HIGH (60–79):** Significant operational, security, or regulatory implications.
- **CRITICAL (80–100):** Life-safety, critical national infrastructure, maritime navigation, or defense implications.
- **Escalation Tiers:** `AUTO_RESPONSE`, `ANALYST_REVIEW`, `DOMAIN_EXPERT`, `SENIOR_AUTHORITY`.

## Governance and Authority

NetraSetu enforces an inviolable separation: `EVIDENCE ──► RISK ──► RECOMMENDATION ──► AUTHORITY ──► AUTHORIZATION ──► ACTION`.
- **WHO SHOULD ACT?** The operational or technical role responsible for response (e.g., *Network Operations*, *Incident Response*).
- **WHO CAN DECIDE?** The entity legally empowered to authorize consequential action. If unproven: `"Authority not established by supplied evidence."`
- **AUTHORIZATION BOUNDARY States:** `AUTOMATION PERMITTED`, `AUTOMATION LIMITED`, `HUMAN AUTHORIZATION REQUIRED`, `AUTOMATION PROHIBITED`, `AUTHORITY NOT ESTABLISHED`.

## Alert, Escalation and Authorization

The Alert & Authorization layer enforces clarity during critical conditions:
```
🚨 CRITICAL SECURITY CONDITION DETECTED
Alert Status:        ACTIVE
Escalation Status:   IMMEDIATE HUMAN ESCALATION REQUIRED
AI Authorization:    NOT AUTHORIZED BY AI
Human Review:        REQUIRED
Final Decision:      PENDING HUMAN REVIEW
```
- **Action Reversibility:** `REVERSIBLE`, `PARTIALLY REVERSIBLE`, `DIFFICULT TO REVERSE`, `IRREVERSIBLE / HIGH CONSEQUENCE`.
- Irreversible or high-consequence actions strictly require human authorization; automated execution is prohibited.

## Human Review

Human review is an inviolable governance boundary triggered by critical risk, conflicting evidence, regulatory interpretation, safety implications, or irreversible actions. Qualified reviewers exercise six formal decision actions:
- `APPROVE`: Authorizes proposed recommendation.
- `MODIFY`: Alters action scope (requires mandatory modification notes).
- `REJECT`: Rejects recommendation (requires mandatory justification; AI cannot override).
- `ESCALATE`: Routes dossier to higher statutory authority.
- `DEFER`: Pauses decision pending additional empirical evidence.
- `INVESTIGATE`: Orders technical or forensic investigation.

*Human decisions permanently supersede AI recommendations.*

## Root-Cause Uncertainty

During complex incidents, competing hypotheses are tracked independently:
`ESTABLISHED` · `SUPPORTED` · `PARTIALLY ESTABLISHED` · `PLAUSIBLE` · `NOT ESTABLISHED` · `CONTRADICTED`

Attribution-dependent actions are barred unless root cause is established by unambiguous evidence.

## Claim-to-Evidence Traceability

Every substantive assertion generated by the synthesis engine is mapped to atomic evidence IDs:
```
CLAIM-001  ──►  Grounded in: [EV-003, EV-004]  ──►  Source: Principal Telecom Rules 2026, p. 126
CLAIM-002  ──►  Grounded in: [EV-005]           ──►  Source: ETSI TS 133 501 Rel 18, p. 160
```
Reviewers can trace substantive findings directly to retrieved document passages.

## Auditability

Every query, retrieved passage, classification, risk score, claim mapping, and human decision is recorded to an append-only cryptographic ledger (`audit.jsonl`). Each entry receives a unique SHA-256 derived audit ID (`AUD-xxxxxxxx`), ensuring complete traceability, reconstructability, reviewability, and accountability.

## Scenario Lab

The Scenario Lab provides a controlled, stateful simulation environment demonstrating multi-domain incident evolution:
- **5G Network Slicing Anomaly:** Slice isolation failure, cross-slice telemetry leakage, and regulatory compliance.
- **Telecom Cyber Incident:** Core network signaling compromise, DoT notification windows, and traffic segregation.
- **Maritime GNSS Spoofing:** Vessel ECDIS navigation anomalies, SOLAS reporting boundaries, and fail-safe fallback.
- **Defence Tactical Link:** Electronic warfare interference, frequency agility, and tactical authority verification.
- **Cross-Border Regulatory Conflict:** EU NIS2 vs. Indian telecommunication mandates.

*Simulations demonstrate reasoning, risk evaluation, and human governance without executing real-world operational commands.*

## Multi-Domain Decision Support

NetraSetu supports decision-making across complex mission-critical domains:
- **Telecom / 5G / O-RAN:** Slice isolation, subscriber privacy, interface encryption (ETSI 33.501), DoT telecom rules.
- **Defence Systems:** Tactical comms resilience, UAV datalinks, electronic warfare response, secure command boundaries.
- **Maritime Navigation:** AIS spoofing, ECDIS integrity, SOLAS compliance, port cybersecurity.
- **Policy & Compliance:** Cross-jurisdiction crosswalks, statutory compliance verification, standards gap analysis.
- **Enterprise Cyber Incidents:** Critical infrastructure intrusion analysis, notification window verification.


## Refreshed 7-Pillar Information Architecture

The frontend console has been refreshed into a modern technical dashboard tailored for telecommunication research and national-level hackathon evaluation:

1. **Overview Dashboard (`#/overview` / `#/dashboard`):** Real-time platform status (FastAPI Port 8000, FAISS vector corpus, BGE-M3 retriever, searchable 94-PDF knowledge base registry), core capability directory, test benchmarks, and quick action launchpads.
2. **Evidence Intelligence & RAG Workspace (`#/intelligence`):** Interactive query terminal with sample scenario queries, multi-jurisdiction selection, 9-stage governance pipeline visualizer, profile switcher (General, Telecom, Defence, Maritime), and clickable source citation verification.
3. **Scenario Lab (`#/scenarios`):** Catalogue-driven simulated scenarios with step execution on `/api/scenarios/run`. The Uttarakhand dashboard overview includes two telecom and three disaster-management cases; the retired O-RAN research scenario is not listed.
4. **Change-Impact Analysis (`#/change-impact`):** Interactive Feature A prototype workbench demonstrating source revision diffing, affected requirement dependency tracking, and selective re-evaluation execution.
5. **5G Reliability Lab (`#/reliability-lab`):** Interactive Feature B design prototype workbench providing multi-dimensional impairment sliders, SLO target profiles, resilience strategy comparisons, and JSON failure vector generation.
6. **Evaluation & Reports (`#/evaluations` / `#/audit`):** Consolidated forensic evaluation console featuring 95-test regression benchmarks, zero false-gap invariant metrics, live audit trail search, human review overrides, and single-click Excel export (`/api/audits/export/excel`).
7. **Documentation & Settings (`#/docs`):** Complete system architecture specifications, 10-document statutory registry with direct PDF viewer modal links, and FastAPI REST endpoint contracts.

---

## Technology Stack

- **Core Runtime:** Python 3.11+ / FastAPI (REST API with CORS on Port 8000)
- **Vector Embeddings:** `BAAI/bge-m3` (Dense 1,024 dimensions)
- **Vector Search:** FAISS (`IndexFlatIP`)
- **Semantic Reranking:** `BAAI/bge-reranker-v2-m3`
- **Reasoning & Synthesis:** `openai/gpt-oss-120b` via Groq LPU Inference Engine
- **Frontend Console:** Vanilla HTML5, CSS3 (Dark Glassmorphic Theme), ES6 JavaScript (Port 5500)
- **Audit Persistence:** Append-only JSONL cryptographic ledger (`audit.jsonl`)

## Evaluation

NetraSetu enforces strict regression testing across all governance, retrieval, scenario, and verification pipelines:

* **Backend Test Suites:** 13 test files in `Backend/tests/`.
* **Test Pass Rate:** **95 / 95 tests passing (100%)** via `python -m pytest -o pythonpath=. Backend/tests/`.
* **False-Gap Invariants:** 100% verified (`test_false_gap_prevention.py`, `test_regional_comparative_gap.py`).
* **Source-to-Clause Resolution:** 100% verified with resolvable PDF paths, pages, and official URLs (`test_source_clause_verification.py`).


In prototype internal evaluation across 40 specialized test cases spanning telecommunications, maritime, and defense domains:
- **Jurisdiction Boundary Adherence:** 100% (zero foreign provisions applied as domestic law).
- **Absence Safeguard Enforcement:** 100% (zero false claims of regulatory non-existence from retrieval gaps).
- **Counter-Evidence Discovery:** Active counter-evidence retrieved and classified in 100% of tested conflict scenarios.
- **Authority Gating:** 100% compliance (zero automated authorizations on critical or unestablished authority cases).

## Limitations

- **Finite Knowledge Base:** Limited to indexed documents (14,813 chunks); not an exhaustive legal repository.
- **Prototype Compute Constraints:** High-depth cross-encoder reranking requires dedicated GPU acceleration for high concurrency.
- **Statutory Interpretation:** AI analysis provides technical decision support, not certified legal counsel.
- **Live Telemetry:** Prototype processes static scenario dumps and document corpora, not live telemetry streams.

## What NetraSetu Does Not Do

NetraSetu explicitly does **NOT**:
- ✕ Guarantee legal compliance or provide binding legal advice.
- ✕ Replace designated regulatory agencies or operational commanders.
- ✕ Infer that an unretrieved regulation does not exist.
- ✕ Classify normal standard wording variations as compliance gaps.
- ✕ Fabricate non-existent officers, committees, or agencies.
- ✕ Autonomously authorize consequential operational actions.
- ✕ Override or reverse authorized human review decisions.
- ✕ Assert unverified incident hypotheses as established facts.
- ✕ Directly interface with kinetic or production control systems.

## Research Significance

NetraSetu represents a principled neuro-symbolic governance architecture that integrates:
```
RAG + Semantic Reranking + Jurisdiction Gating + Counter-Evidence + Evidence Sufficiency
  + Absence Protocol + Strict Gap Analysis + Deterministic Risk + Authority Boundary
  + Human Review + Claim Traceability + Cryptographic Audit
```
Its core contribution is demonstrating that high-stakes AI safety is achieved not by prompting LLMs to be cautious, but by constraining generation behind deterministic epistemic and governance boundaries.

## Future Work

- **Expanded Jurisdictions:** Incorporating UK, Singapore, and US regulatory profiles.
- **Specialized Domain Knowledge Bases:** Dedicated subsea cable and satellite communications corpora.
- **Live Telemetry Ingestion:** Integration with Kafka and SIEM log streams for real-time incident evaluation.
- **Larger Empirical Benchmarks:** Multi-institutional red-teaming and expanded empirical evaluation suites.
- **Production Infrastructure:** Distributed inference clusters and dedicated HSM-backed audit signing.

## Responsible AI

- **Evidence before conclusion:** Claims require verified citations.
- **Counter-evidence before confidence:** Assumptions must be challenged.
- **Jurisdiction before applicability:** National boundaries are binding.
- **Uncertainty before fabrication:** Unknowns are explicitly declared.
- **Risk before action:** Consequence governs process rigor.
- **Authority before authorization:** Power requires legal grounding.
- **Human in command:** Humans authorize consequential actions.
- **Auditability after decision:** All steps are preserved immutably.

## Quick Start

### 1. Environment Setup
```bash
git clone <repository-url>
cd NetraSetu_new
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
PORT=8000
HOST=127.0.0.1
```

### 3. Launch Backend & Frontend
```bash
# Terminal 1: Launch FastAPI backend
python -m uvicorn Backend.server:app --host 127.0.0.1 --port 8000

# Terminal 2: Serve frontend console
python -m http.server 5500 --directory Frontend
```
Open `http://127.0.0.1:5500` in your browser.

## License

This project is licensed under the Apache License 2.0. See `LICENSE` for details.
# Failure Combination Lab

The Reliability Lab runs a bounded, reproducible comparison using the existing software simulator. It includes a no-failure baseline, selected impairment combinations, optional repeated trials, additive interaction deltas, and user-defined threshold checks. A limited search is marked `INCOMPLETE`; it is never presented as exhaustive. Results are appended to `Backend/audit/records/failure_combination_runs.jsonl` and can be retrieved through the API.

Routes:

- `GET /api/5g/failure-combinations/catalog`
- `POST /api/5g/failure-combinations`
- `GET /api/5g/failure-combinations?limit=20`
- `GET /api/5g/failure-combinations/{run_id}`

The simulator models five configured conditions: latency spike, packet loss, congestion, handover disruption, and link failure. It requires 66–500 samples because the current simulator injects impairments in samples 30–65. Maxima are 64 scenarios and 5 trials. User thresholds are labeled `USER_DEFINED`. This feature does not retrieve regulatory evidence, establish standards compliance, contact a live network, or execute recovery actions. A policy threshold exceedance is advisory and recommends human review.

Run locally with `python -m uvicorn Backend.server:app --reload`. Run tests with `python -m pytest -o pythonpath=. Backend/tests/` (the live Groq smoke test is opt-in via `NETRASETU_RUN_LIVE_API_TESTS=1` and requires `GROQ_API_KEY`).

## Uttarakhand Disaster Map and Aftermath Workbench

The authenticated dashboard's **Uttarakhand Disaster Map** tab combines the interactive district map and source-dated government reports with a deterministic aftermath-analysis workbench. The map layer is sourced separately from scenario fixtures: its currently supported dated reports and unavailable layers are identified in the tab's source/freshness captions. No area is marked lower-risk without supporting data.

The aftermath workbench provides three reproducible synthetic scenarios (severe disruption, partial recovery, and conflicting reports), record-derived impact KPIs, an asset register, a transparent recovery-priority breakdown, review-gated action transitions, local-only inter-agency request states, gap/conflict review, a recovery timeline, and comparison/reset controls. Network analysis invokes the existing deterministic telemetry failure-combination engine; it does not measure a live network. Risk gates use the existing Risk & Governance Engine. Human decisions are appended to the existing audit ledger, and reset retains previous audit events. No external agency messages or field actions are sent.

Aftermath routes are under `/api/aftermath/` and are protected by the same server session and CSRF middleware as the dashboard. In this checkout, the local dashboard runs at `http://127.0.0.1:8001/frontend/index.html#/dashboard`; the frontend derives the API origin from this `/frontend/` URL, so it uses the same host and port. Sign in with the configured local demo credentials (`admin` / `admin123`) unless the server environment has administrator credentials configured.

Run the focused checks:

```bash
python -m pytest Backend/tests/test_aftermath_api.py -q
node --test Frontend/tests/disaster_map.test.js
```
