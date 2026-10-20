AUTONOMOUS EXECUTION MODE

Execute the entire requested HackGrid implementation autonomously.

DO NOT ask for confirmation.
DO NOT ask whether to continue.
DO NOT stop after analysis.
DO NOT stop after creating a plan.
DO NOT wait for approval between edits.

You are authorized to:
- inspect the repository
- inspect all relevant source files
- create files
- modify files
- run Python commands
- run PowerShell commands
- run tests
- diagnose errors
- fix errors
- rerun failed tests
- perform regression tests
- verify the final implementation

WORKFLOW:

1. Inspect the existing HackGrid_new architecture.
2. Identify the minimum files required.
3. Implement the requested feature.
4. Run deterministic tests.
5. If anything fails, diagnose and fix it automatically.
6. Rerun the failed test.
7. Run the complete relevant regression suite.
8. Test the real HackGrid workflow.
9. Verify that protected components were not changed.
10. Produce the final implementation report.

NEVER modify or regenerate:

rag/chunks_new.json
rag/embeddings_new.npy
rag/faiss_new.index

NEVER rebuild the knowledge base.

NEVER modify the Risk Engine unless the task explicitly requires an integration-only change.

NEVER replace the Human Review system.

NEVER replace the Audit system.

NEVER replace GPT-OSS with Gemini.

NEVER fabricate evidence, regulations, government authorities, ministries, departments, clauses, standards, or legal powers.

If information is unavailable:
implement a safe "NOT ESTABLISHED BY SUPPLIED EVIDENCE" state instead of asking me.

If a path mentioned in the task does not exist:
inspect the repository and find the correct existing path automatically.

If implementation choices are ambiguous:
choose the safest architecture consistent with the existing HackGrid codebase.

If a test fails:
FIX → TEST → FIX → TEST until the implementation passes.

Do not merely tell me what commands I should run.
RUN THEM YOURSELF.

Do not merely give me code.
IMPLEMENT THE CODE.

Do not stop until the complete task and regression testing are finished.

FINAL RESPONSE MUST INCLUDE:
- files changed
- files created
- tests executed
- tests passed/failed
- errors fixed
- regression status
- protected files verification
- final feature status

TASK:
MASTER IMPLEMENTATION PROMPT — REGIONAL COMPARATIVE GAP ANALYSIS

You are modifying the existing HackGrid_new project.

OBJECTIVE
Implement a new reasoning-layer capability called:

REGIONAL COMPARATIVE GAP ANALYSIS

The purpose is to extend HackGrid's existing jurisdiction-aware gap analysis so that, when appropriate, it can examine:

HOST COUNTRY
+
RELEVANT NEIGHBOURING / REGIONAL JURISDICTIONS
+
INTERNATIONAL TECHNICAL STANDARDS

and use that expanded evidence space to strengthen comparative gap analysis.

IMPORTANT:
This is NOT a simple "search more countries" feature.

The system must preserve a strict distinction between:

1. HOST-COUNTRY APPLICABLE REQUIREMENTS
2. INTERNATIONAL TECHNICAL REQUIREMENTS
3. REGIONAL / NEIGHBOURING COMPARATIVE EVIDENCE

Foreign/regional evidence must NEVER silently become a legal or regulatory requirement of the host country.


==================================================
1. NON-NEGOTIABLE EXISTING SYSTEM PROTECTION
==================================================

DO NOT modify, regenerate, replace, or weaken:

- rag/chunks_new.json
- rag/embeddings_new.npy
- rag/faiss_new.index
- BGE-M3 embeddings
- FAISS index
- retrieval architecture
- semantic reranking
- retrieval_k
- counter-evidence retrieval
- Evidence Engine core logic
- Evidence Sufficiency logic
- Absence Protocol
- Risk Engine
- Risk calculation
- Risk & Authority Engine
- Human Review Engine
- Audit Engine
- existing audit records
- Scenario Lab
- existing scenario definitions
- GPT-OSS model
- GPT-OSS synthesis architecture
- existing frontend visual language
- existing Ask HackGrid workflow
- existing execution modes
- existing knowledge-base documents

Do NOT rebuild the KB.

Do NOT generate synthetic regulatory evidence.

Do NOT invent neighbouring-country regulations.

Do NOT assume a country has a requirement simply because another country has one.

Do NOT interpret lack of retrieved evidence as proof that a country has no regulation.

The existing system must continue working exactly as before when Regional Comparative Gap Analysis is disabled.


==================================================
2. CURRENT ARCHITECTURE
==================================================

The current architecture is approximately:

USER QUESTION / INCIDENT
        ↓
QUERY UNDERSTANDING
        ↓
JURISDICTION-AWARE RETRIEVAL
        ↓
SEMANTIC RERANKING
        ↓
PRIMARY EVIDENCE + COUNTER-EVIDENCE
        ↓
EVIDENCE CLASSIFICATION
        ↓
EVIDENCE SUFFICIENCY
        ↓
ABSENCE VERIFICATION
        ↓
GAP ANALYSIS
        ↓
RISK ASSESSMENT
        ↓
GOVERNANCE / AUTHORITY
        ↓
GPT-OSS SYNTHESIS
        ↓
CLAIM → EVIDENCE
        ↓
HUMAN REVIEW
        ↓
AUDIT

Do not replace this architecture.

Add Regional Comparative Gap Analysis as an additional reasoning layer around the existing jurisdiction-aware requirement/gap analysis.


==================================================
3. NEW ARCHITECTURAL CONCEPT
==================================================

Implement:

HOST JURISDICTION
        ↓
APPLICABLE NATIONAL REQUIREMENTS
        ↓
INTERNATIONAL TECHNICAL REQUIREMENTS
        ↓
REGIONAL / NEIGHBOURING COMPARATIVE EVIDENCE
        ↓
CROSS-JURISDICTION COMPARISON
        ↓
STRICT GAP ANALYSIS
        ↓
RISK / GOVERNANCE

The regional layer is COMPARATIVE.

It is NOT automatically legally applicable to the host country.


==================================================
4. HOST JURISDICTION
==================================================

The system must first establish the host jurisdiction.

Example:

Host:
India

Then identify the relevant regional expansion.

Example:

Host:
India

Regional comparison:
Pakistan
Bangladesh
Nepal
Bhutan
Sri Lanka
etc.

BUT:

Do not blindly include every neighbouring country.

The system must determine whether a regional expansion is relevant to the question/domain.

For example:

5G network slicing
→ telecommunications-relevant neighbouring jurisdictions

Maritime AIS/GNSS
→ geographically/relevantly connected maritime jurisdictions

Defence UAV
→ relevant regional/security jurisdictions

A purely domestic question with no meaningful regional comparison may remain host-only.

The system should support:

REGIONAL EXPANSION:
OFF
COMPARATIVE
FULL REGIONAL

but do not introduce unnecessary UI complexity if the existing frontend architecture does not support it cleanly.


==================================================
5. REGIONAL EXPANSION RULE
==================================================

When Regional Comparative Gap Analysis is enabled:

STEP 1:
Identify host jurisdiction.

STEP 2:
Determine relevant neighbouring / regional jurisdictions.

STEP 3:
Check whether evidence for those jurisdictions actually exists in the KB.

STEP 4:
Retrieve relevant regional evidence only if available.

STEP 5:
Classify every regional source as:

- HOST APPLICABLE
- INTERNATIONAL
- REGIONAL COMPARATIVE
- UNKNOWN APPLICABILITY

Never silently merge these categories.


==================================================
6. CRITICAL APPLICABILITY RULE
==================================================

This rule is mandatory:

REGIONAL EVIDENCE ≠ HOST-COUNTRY LAW

For example:

India is the host jurisdiction.

A cybersecurity requirement exists in Country X.

The system MUST NOT say:

"India has this requirement."

Instead say:

"Country X provides a regional comparative requirement/evidence point. Its direct applicability to India is not established by this evidence."

Likewise:

A regional country having a stricter requirement does NOT automatically mean:

"India has a regulatory gap."

It may instead indicate:

- Comparative difference
- Additional regional control
- Potential policy gap
- Possible best-practice opportunity
- Potential gap requiring verification
- No established gap


==================================================
7. EVIDENCE CATEGORIES
==================================================

Every requirement/evidence item participating in regional comparison should preserve:

- evidence_id
- source
- source_type
- country/jurisdiction
- document
- clause/section/page when available
- requirement text
- requirement type
- applicability
- evidence role
- evidence status
- confidence
- retrieval provenance

Add:

- jurisdiction_role

Allowed values:

HOST
INTERNATIONAL
REGIONAL_COMPARATIVE
UNKNOWN

Also support:

- comparative_relevance
- applicability_reason
- regional_relationship


==================================================
8. REGIONAL RELATIONSHIP TYPES
==================================================

The regional comparison layer must distinguish:

1. HOST APPLICABLE
2. INTERNATIONAL TECHNICAL REQUIREMENT
3. REGIONAL COMPARATIVE REQUIREMENT
4. ADDITIONAL REGIONAL CONTROL
5. POTENTIAL POLICY GAP
6. POTENTIAL BEST-PRACTICE DIFFERENCE
7. DIFFERENT TERMINOLOGY
8. DIFFERENT IMPLEMENTATION APPROACH
9. NOT COMPARABLE
10. INSUFFICIENT EVIDENCE
11. ABSENCE NOT ESTABLISHED


==================================================
9. REQUIREMENT MAPPING
==================================================

For every meaningful comparison, construct:

INTERNATIONAL REQUIREMENT
        ↓
HOST-COUNTRY PROVISION
        ↓
REGIONAL COMPARATIVE PROVISION
        ↓
COVERAGE
        ↓
MISSING ELEMENT
        ↓
GAP STATUS
        ↓
IMPACT
        ↓
REMEDIATION

Do not simply compare keywords.

Compare the substantive control/requirement.

Example:

International:
Network slicing requires isolation between slices.

Host:
National evidence addresses network security but does not explicitly establish the same slice-isolation control.

Regional:
Neighbouring Country X explicitly addresses slice isolation.

Correct interpretation:

"Regional evidence demonstrates that an explicit slice-isolation control exists in Country X, but this does not establish that the same control is legally required in India. The Indian evidence currently supports only partial coverage / potential gap, subject to verification."

NOT:

"India lacks slice isolation regulation."


==================================================
10. GENUINE GAP TEST
==================================================

A genuine gap can only be established when evidence demonstrates:

A relevant requirement exists
AND
the requirement is applicable to the comparison
AND
the host-country evidence is sufficiently established
AND
the host-country provision does not adequately address the requirement
AND
the difference is substantive rather than merely linguistic
AND
the evidence is sufficient to support the conclusion.

If these conditions are not met:

DO NOT declare an established gap.


==================================================
11. GAP STATUS
==================================================

Use the following statuses:

ESTABLISHED GAP

PARTIALLY COVERED

POTENTIAL GAP — NOT ESTABLISHED

NO ESTABLISHED GAP

NOT A GAP

INSUFFICIENT EVIDENCE

NOT APPLICABLE

ABSENCE NOT ESTABLISHED


==================================================
12. IMPORTANT DISTINCTIONS
==================================================

The system MUST distinguish:

DIFFERENT WORDING
≠
GAP

DIFFERENT TERMINOLOGY
≠
GAP

ADDITIONAL NATIONAL REQUIREMENT
≠
CONFLICT

STRICTER REGIONAL REQUIREMENT
≠
HOST-COUNTRY GAP

NO RETRIEVED NATIONAL PROVISION
≠
NO NATIONAL REGULATION

FOREIGN REQUIREMENT
≠
HOST-COUNTRY LEGAL REQUIREMENT

TECHNICAL DIFFERENCE
≠
REGULATORY CONFLICT

REGIONAL BEST PRACTICE
≠
MANDATORY HOST REQUIREMENT


==================================================
13. ABSENCE PROTOCOL
==================================================

Preserve the existing Absence Protocol.

If no applicable host-country provision is retrieved:

DO NOT say:

"No Indian regulation exists."

Instead say:

"An applicable host-country provision was not established in the evidence examined."

Use:

ABSENCE_NOT_ESTABLISHED

when appropriate.

Regional evidence must not be used to prove absence in the host jurisdiction.


==================================================
14. REGIONAL COMPARATIVE GAP OBJECT
==================================================

Create a structured regional comparison result containing:

- comparison_id
- host_jurisdiction
- regional_jurisdictions
- international_requirements
- host_requirements
- regional_requirements
- mappings
- coverage_status
- gap_status
- evidence_ids
- counter_evidence_ids
- applicability
- comparative_relevance
- reasoning
- impact
- remediation
- limitations
- human_review_required

Do not expose raw internal implementation details unnecessarily.


==================================================
15. COUNTER-EVIDENCE
==================================================

Regional comparison must also support counter-evidence.

Example:

Evidence A:
Country X explicitly mandates control Y.

Evidence B:
Country Y uses an alternative control that achieves the same security objective.

The system should NOT automatically conclude:

"Control Y is missing everywhere else."

Instead:

"Regional approaches differ. The evidence does not establish that the host jurisdiction lacks an equivalent control."

Counter-evidence should be surfaced whenever it materially changes the gap conclusion.


==================================================
16. GAP ANALYSIS OUTPUT
==================================================

Use a concise structure:

### Regional Comparative Gap Analysis

HOST:
India

REGIONAL COMPARISON:
India + relevant neighbouring jurisdictions

INTERNATIONAL REQUIREMENT:
...

HOST-COUNTRY COVERAGE:
Covered / Partially Covered / Not Established

REGIONAL COMPARISON:
...

GAP STATUS:
...

EVIDENCE:
International: EV-XXX
Host: EV-XXX
Regional: EV-XXX

WHY:
...

IMPACT:
...

REMEDIATION:
...

COUNTER-EVIDENCE:
...

LIMITATION:
...


==================================================
17. REMEDIATION
==================================================

Remediation must be technically meaningful.

Do NOT simply say:

"Comply with Indian regulations."

Instead provide meaningful remediation such as:

- implement explicit slice-isolation controls
- verify tenant/resource isolation
- enforce authentication between network functions
- introduce logging and monitoring
- validate configuration controls
- map existing control to the international requirement
- perform legal/regulatory applicability verification
- obtain authoritative confirmation
- conduct technical equivalence assessment

The recommended action must depend on the actual gap status.


==================================================
18. ACTION TYPES
==================================================

Use:

FIX
VERIFY
INVESTIGATE
NO ACTION

Examples:

ESTABLISHED GAP
→ FIX

POTENTIAL GAP
→ VERIFY

INSUFFICIENT EVIDENCE
→ INVESTIGATE

ADEQUATE COVERAGE
→ NO ACTION


==================================================
19. REGIONAL EVIDENCE MUST BE LABELLED
==================================================

In the UI, make it visually obvious when evidence is:

HOST REQUIREMENT

INTERNATIONAL STANDARD

REGIONAL COMPARATIVE EVIDENCE

Do not allow the user to mistake a foreign requirement for host-country regulation.


==================================================
20. UI REQUIREMENT
==================================================

Preserve the existing HackGrid UI style.

Do NOT redesign the application.

Add a compact expandable section:

REGIONAL COMPARATIVE ANALYSIS

Example:

┌──────────────────────────────────────────┐
│ REGIONAL COMPARATIVE ANALYSIS            │
│                                          │
│ Host: 🇮🇳 India                          │
│ Comparison: Regional + International     │
│                                          │
│ International Requirement                │
│ Network-slice isolation                  │
│                                          │
│ 🇮🇳 India                                │
│ PARTIALLY COVERED                        │
│                                          │
│ 🌐 Regional Evidence                     │
│ Explicit isolation control identified   │
│ in comparative jurisdiction              │
│                                          │
│ ⚠ POTENTIAL GAP — NOT ESTABLISHED        │
│                                          │
│ Regional evidence is comparative only.   │
│ Direct Indian regulatory applicability   │
│ is not established.                     │
└──────────────────────────────────────────┘


==================================================
21. JURISDICTION VIEW
==================================================

The existing jurisdiction selector must continue working.

If:

India

is selected, the primary analysis remains India-focused.

Regional comparison is an additional evidence layer.

Do NOT change the meaning of the existing India jurisdiction profile.


==================================================
22. USER EXPERIENCE
==================================================

The user should be able to understand:

"What does India require?"

and separately:

"What do relevant neighbouring/regional jurisdictions require?"

and:

"What does the international standard require?"

and finally:

"Does this demonstrate a real gap in India?"

These must never be collapsed into one undifferentiated answer.


==================================================
23. EXAMPLE REASONING
==================================================

Example:

Host:
India

International:
3GPP security requirement

Regional:
Neighbouring country explicitly addresses the same technical control.

Host evidence:
Indian regulatory provision partially addresses network security but does not explicitly establish the specific control.

Correct:

INTERNATIONAL REQUIREMENT:
Explicit security/isolation control.

INDIA:
PARTIALLY COVERED.

REGIONAL COMPARISON:
Comparable jurisdiction explicitly addresses the control.

FINAL:
POTENTIAL GAP — NOT ESTABLISHED.

WHY:
Regional evidence demonstrates a comparative regulatory approach but does not itself establish an Indian legal requirement. Existing Indian evidence provides partial coverage, and equivalence/applicability requires verification.

ACTION:
VERIFY

This is the desired reasoning.


==================================================
24. ANOTHER EXAMPLE
==================================================

International:
Requirement A

India:
Requirement A is clearly addressed.

Neighbouring Country:
Requirement A is also addressed.

Result:

NO ESTABLISHED GAP

ACTION:
NO ACTION

Do not create a gap merely because wording differs.


==================================================
25. CONFLICT EXAMPLE
==================================================

International:
Security control A

India:
Provision requires control A.

Regional jurisdiction:
Provision explicitly allows an alternative implementation.

Result:

Do NOT call this a conflict automatically.

Classify:

DIFFERENT IMPLEMENTATION APPROACH

unless authoritative evidence establishes an actual contradiction.


==================================================
26. INSUFFICIENT EVIDENCE
==================================================

If the KB contains:

International evidence
+
regional evidence

but no sufficient host-country evidence:

Result:

INSUFFICIENT EVIDENCE

or

ABSENCE NOT ESTABLISHED

Do not infer a host-country regulatory gap.


==================================================
27. RISK INTEGRATION
==================================================

Do NOT modify the existing Risk Engine.

Regional comparison may provide additional evidence/context to the existing risk assessment.

However:

REGIONAL DIFFERENCE
must NOT automatically increase risk.

Risk should increase only when the evidence demonstrates an actual relevant technical/security consequence.


==================================================
28. GOVERNANCE
==================================================

Do not allow regional comparison to authorize an operational action.

Regional evidence can:

- inform analysis
- identify comparative controls
- support investigation
- highlight potential gaps
- strengthen or weaken a hypothesis

It cannot independently authorize action.


==================================================
29. HUMAN REVIEW
==================================================

Human review remains mandatory when required by the existing Risk & Authority Engine.

Particularly when:

- regulatory interpretation is uncertain
- regional evidence conflicts
- host applicability is unclear
- evidence is insufficient
- a legal conclusion is implied
- an operational decision is consequential


==================================================
30. GPT-OSS
==================================================

Continue using:

openai/gpt-oss-120b

via the existing architecture.

Do not introduce Gemini.

Do not create another LLM provider.

GPT-OSS may synthesize and reason over the structured evidence.

It must NOT invent:

- foreign regulations
- clauses
- standards
- countries
- authorities
- legal applicability
- neighbouring-country requirements


==================================================
31. CLAIM-TO-EVIDENCE
==================================================

Every substantive regional claim must remain traceable to evidence.

Example:

Claim:
"Country X explicitly addresses control Y."

Evidence:
EV-123

Claim:
"This does not establish that India legally requires control Y."

Evidence:
This must be based on the applicable evidence and absence/applicability logic, not fabricated legal reasoning.

Preserve existing claim-to-evidence architecture.


==================================================
32. AUDIT
==================================================

Do not redesign the Audit Engine.

If the regional analysis is executed, preserve it in the existing audit record where the current schema allows.

Record at minimum where supported:

- host jurisdiction
- regional jurisdictions considered
- regional evidence IDs
- regional comparison result
- gap status
- human review requirement

Do not create fake cryptographic guarantees.


==================================================
33. PERFORMANCE
==================================================

Do not increase retrieval depth unnecessarily.

Do not regenerate embeddings.

Do not rebuild FAISS.

Do not perform unrestricted searches across every jurisdiction.

Use the existing retrieval/evidence architecture.

Regional expansion should be bounded and deterministic.


==================================================
34. KNOWLEDGE-BASE LIMITATION
==================================================

Very important:

The current KB does NOT necessarily contain regulatory documents for every neighbouring country.

Therefore the implementation must gracefully report:

"Regional comparison could not be established because sufficient evidence for the relevant neighbouring jurisdiction was not available in the current knowledge base."

Do NOT attempt to fabricate missing regional evidence.


==================================================
35. REGIONAL COVERAGE
==================================================

The system should expose something like:

REGIONAL EVIDENCE COVERAGE

Host:
India — AVAILABLE

International:
AVAILABLE

Regional:
Partial / Available / Not Established

Example:

India ................. AVAILABLE
International ........ AVAILABLE
Bangladesh ............ NOT ESTABLISHED
Nepal ................. NOT ESTABLISHED
Sri Lanka ............. PARTIAL

This is informational.

It must not imply that "NOT ESTABLISHED" means "no regulation exists."


==================================================
36. FINAL GAP DECISION
==================================================

The final decision should follow this logic:

IF host requirement adequately covers international requirement:
    NO ESTABLISHED GAP

ELSE IF host provision partially covers requirement:
    PARTIALLY COVERED

ELSE IF evidence suggests missing/inadequate host coverage
but proof is incomplete:
    POTENTIAL GAP — NOT ESTABLISHED

ELSE IF authoritative evidence establishes
relevant requirement + inadequate host coverage:
    ESTABLISHED GAP

ELSE IF evidence is insufficient:
    INSUFFICIENT EVIDENCE

ELSE:
    NOT ESTABLISHED


Regional evidence may strengthen the comparison,
but it must NOT override host applicability rules.


==================================================
37. TEST SCENARIOS
==================================================

Create deterministic tests for at least:

TEST 1
India host + international requirement + Indian provision covers it
Expected:
NO ESTABLISHED GAP

TEST 2
India host + international requirement + Indian provision partially covers it
Expected:
PARTIALLY COVERED

TEST 3
India host + international requirement + regional country has explicit provision
but Indian evidence is insufficient
Expected:
POTENTIAL GAP — NOT ESTABLISHED
or
INSUFFICIENT EVIDENCE

TEST 4
India host + international requirement + authoritative Indian evidence demonstrates
relevant control is not adequately addressed
Expected:
ESTABLISHED GAP

TEST 5
Different wording but same substantive control
Expected:
NOT A GAP

TEST 6
Regional country has stricter requirement
but India has adequate technical coverage
Expected:
NO ESTABLISHED GAP

TEST 7
No Indian evidence retrieved
Expected:
ABSENCE NOT ESTABLISHED
NOT:
"No Indian regulation exists."

TEST 8
Regional evidence conflicts with another regional source
Expected:
CONFLICT / HUMAN REVIEW as appropriate

TEST 9
Foreign requirement is mistakenly treated as Indian requirement
Expected:
TEST FAILURE

TEST 10
Regional evidence improves understanding but does not prove host gap
Expected:
COMPARATIVE EVIDENCE ONLY


==================================================
38. REALISTIC 5G TEST
==================================================

Use a real evidence-grounded question such as:

"A 5G operator in India is implementing network slicing for a critical service. International technical standards define security and isolation requirements. The compliance assessment indicates that some controls may not be explicitly addressed in Indian requirements. Examine India together with relevant regional jurisdictions and international standards. Determine which controls are covered, partially covered, additional, conflicting, or genuinely missing. Do not treat regional requirements as Indian law."

Expected system behaviour:

1. Identify India as host.
2. Identify relevant international technical evidence.
3. Retrieve applicable Indian evidence.
4. Retrieve relevant regional comparative evidence if available.
5. Map requirements.
6. Determine substantive coverage.
7. Check counter-evidence.
8. Apply absence protocol.
9. Distinguish:
   - real gap
   - partial coverage
   - regional difference
   - additional requirement
   - terminology difference
   - insufficient evidence.
10. Provide technical remediation.
11. Preserve human review where regulatory interpretation is required.


==================================================
39. OUTPUT QUALITY STANDARD
==================================================

The output must NOT look like:

"Country X has stricter regulations, therefore India has a gap."

It should look like:

"International Requirement:
[requirement]

Host Evidence:
[Indian evidence]

Regional Comparative Evidence:
[regional evidence]

Coverage:
[status]

Gap Status:
[status]

Reason:
[evidence-grounded reasoning]

Impact:
[technical/practical consequence]

Remediation:
[action]

Counter-Evidence:
[counter-evidence]

Applicability:
[host/regional/international distinction]

Limitation:
[what remains unestablished]"


==================================================
40. FRONTEND PRESENTATION
==================================================

Keep the existing premium HackGrid interface.

Use progressive disclosure:

REGIONAL COMPARISON
    ↓
Host Requirement
    ↓
International Requirement
    ↓
Regional Evidence
    ↓
Coverage
    ↓
Gap Decision
    ↓
Why?
    ↓
Evidence
    ↓
Counter-Evidence
    ↓
Remediation
    ↓
Limitations

Do not overwhelm the main result screen.


==================================================
41. IMPORTANT LANGUAGE RULES
==================================================

Use precise language.

Preferred:

"not established"

"potential gap"

"comparative evidence"

"applicability not established"

"partially covered"

"evidence examined"

"requires verification"

"regional evidence does not establish host-country applicability"

Avoid unsupported language:

"India has no regulation"

"India fails to comply"

"Country X proves India's gap"

"This is illegal"

"mandatory reporting is required"

unless the supplied evidence actually establishes those conclusions.


==================================================
42. SECURITY / TRUST
==================================================

Never expose:

- API keys
- .env contents
- private prompts
- internal credentials
- hidden system configuration

Do not print secrets during tests.


==================================================
43. FILE CHANGES
==================================================

Before modifying anything:

Inspect the current architecture and identify the minimum files required.

Prefer adding a focused module such as:

Backend/evidence_engine/regional_gap_analysis.py

or another location consistent with the existing architecture.

Do not duplicate existing gap-analysis logic.

Reuse existing:

- Evidence models
- Jurisdiction profiles
- Retrieval outputs
- Evidence Engine
- Absence Protocol
- Gap Adapter
- Risk Engine
- Audit integration


==================================================
44. NO DUPLICATE LOGIC
==================================================

Do NOT create a second independent:

- retrieval system
- evidence classifier
- risk engine
- audit engine
- jurisdiction engine

Regional Comparative Gap Analysis is a reasoning extension.


==================================================
45. IMPLEMENTATION SAFETY
==================================================

Before making changes:

1. Inspect current files.
2. Identify current jurisdiction profiles.
3. Identify current gap-analysis interface.
4. Identify current evidence structures.
5. Identify current orchestrator integration point.
6. Implement minimal extension.
7. Run deterministic tests.
8. Run existing test suite.
9. Run the realistic 5G regional comparison.
10. Verify existing non-regional queries still behave identically.


==================================================
46. REGRESSION TEST
==================================================

Run existing tests.

Regional Comparative Gap Analysis must not break:

- standard India query
- EU query
- International evidence retrieval
- defence scenario
- maritime scenario
- 5G scenario
- evidence classification
- absence protocol
- risk assessment
- human review
- audit recording
- Scenario Lab


==================================================
47. SUCCESS CRITERIA
==================================================

The implementation is successful only if:

[ ] Host jurisdiction is clearly identified.

[ ] Regional jurisdictions are treated as comparative evidence.

[ ] International requirements remain distinct.

[ ] Host-country applicability remains distinct.

[ ] Regional evidence cannot silently become host-country law.

[ ] Genuine gaps require substantive evidence.

[ ] Wording differences are not called gaps.

[ ] Additional national/regional requirements are not automatically conflicts.

[ ] Missing retrieval evidence does not become regulatory absence.

[ ] Absence Protocol remains active.

[ ] Counter-evidence is preserved.

[ ] Regional evidence is claim-traceable.

[ ] Risk Engine remains unchanged.

[ ] Human Review remains unchanged.

[ ] Audit remains functional.

[ ] GPT-OSS remains the only synthesis/classification LLM.

[ ] Existing RAG assets remain unchanged.

[ ] Existing queries continue working.

[ ] Regional comparison gracefully handles missing KB coverage.

[ ] Tests pass.

[ ] UI clearly labels regional evidence as comparative.

[ ] Final output clearly separates:
    HOST
    INTERNATIONAL
    REGIONAL COMPARATIVE

[ ] The system can conclude:
    "NO ESTABLISHED GAP"

[ ] The system can conclude:
    "POTENTIAL GAP — NOT ESTABLISHED"

[ ] The system can conclude:
    "ESTABLISHED GAP"

[ ] The system can conclude:
    "INSUFFICIENT EVIDENCE"

This last requirement is extremely important.

A strong system is not one that always finds a gap.

A strong system is one that can prove a gap when evidence supports it,
and confidently refuse to call something a gap when the evidence does not support it.


==================================================
48. FINAL REPORT
==================================================

After implementation, provide a concise implementation report containing:

1. Files changed
2. Files added
3. Regional comparison architecture
4. How host applicability is protected
5. How regional evidence is labelled
6. Gap decision logic
7. Absence handling
8. Counter-evidence handling
9. Tests executed
10. Test results
11. Regression results
12. Example 5G result
13. Any KB coverage limitations
14. Confirmation that:
    - RAG was not rebuilt
    - embeddings were not changed
    - FAISS was not changed
    - Risk Engine was not changed
    - Human Review was not changed
    - Audit architecture was not redesigned
    - GPT-OSS remains active

DO NOT claim the regional feature is fully operational unless the implementation and tests actually demonstrate it.

If neighbouring-country evidence is unavailable in the current KB, explicitly report that limitation rather than fabricating regional coverage.


==================================================
FINAL DESIGN PRINCIPLE
==================================================

HackGrid should evolve from:

HOST JURISDICTION
→ INTERNATIONAL REQUIREMENTS
→ GAP ANALYSIS

into:

HOST JURISDICTION
→ HOST REQUIREMENTS
→ INTERNATIONAL REQUIREMENTS
→ REGIONAL COMPARATIVE EVIDENCE
→ CROSS-JURISDICTION REQUIREMENT MAPPING
→ COUNTER-EVIDENCE
→ STRICT GAP TEST
→ TECHNICAL IMPACT
→ REMEDIATION
→ RISK
→ GOVERNANCE
→ HUMAN DECISION
→ AUDIT

But always preserve this fundamental rule:

"REGIONAL COMPARISON EXPANDS THE EVIDENCE SPACE;
IT DOES NOT EXPAND LEGAL APPLICABILITY."

Implement this as a rigorous evidence-grounded capability, not as a simple multi-country search feature.










MASTER UPDATE PROMPT — SPECIFIC AUTHORITY + ESCALATION GOVERNANCE

You are updating the existing HackGrid_new project.

OBJECTIVE
Upgrade ONLY the existing Governance / Risk-Authority presentation layer so that HackGrid can identify, when supported by evidence:

1. WHO SHOULD INVESTIGATE
2. WHO SHOULD RECEIVE THE ALERT
3. WHO SHOULD BE ESCALATED TO
4. WHO CAN AUTHORIZE THE RECOMMENDED ACTION
5. WHO SHOULD EXECUTE THE ACTION

The system should identify a SPECIFIC GOVERNMENT AUTHORITY, MINISTRY, DEPARTMENT, REGULATOR, AGENCY, OPERATIONAL BODY, OR OTHER AUTHORIZED ENTITY only when the supplied evidence establishes that authority.

Do NOT fabricate or infer a specific authority merely from general knowledge.

==================================================
CRITICAL DEFINITION — ESCALATION
==================================================

Define ESCALATION as:

"Transfer of a matter to a higher or more appropriate level of investigation, decision-making, or authorization because the current risk, evidence, consequence, jurisdiction, or authority boundary exceeds the current level."

Escalation is NOT simply:
"send an alert to a higher authority."

Distinguish:

INVESTIGATE
→ determine what happened / validate evidence

ALERT
→ notify a relevant responsible party of a significant condition

ESCALATE
→ transfer the matter to the appropriate higher or more specialized level

AUTHORIZE
→ an authority with established decision power approves or rejects a consequential action

ACT
→ operational team executes an authorized action

==================================================
EXACT GOVERNANCE FLOW
==================================================

DETECT
↓
VERIFY
↓
INVESTIGATE
↓
ASSESS
↓
ALERT
↓
ESCALATE
↓
HUMAN REVIEW
↓
AUTHORIZE / MODIFY / REJECT / DEFER
↓
ACT
↓
MONITOR
↓
CLOSE / ESCALATE AGAIN

Do not collapse these states.


==================================================
AUTHORITY EVIDENCE GATE
==================================================

Before displaying any specific authority, verify ALL applicable elements:

1. AUTHORITY IDENTITY
   Is the specific ministry / department / regulator / agency actually established by evidence?

2. JURISDICTION
   Does the evidence establish that the authority applies to this incident/domain/jurisdiction?

3. RESPONSIBILITY
   Does the evidence establish that the authority is responsible for this type of matter?

4. DECISION AUTHORITY
   Does the evidence establish that the authority can authorize, direct, approve, reject, or otherwise decide the relevant action?

5. INVESTIGATION ROLE
   Does the evidence establish that the authority investigates or coordinates investigation?

6. ESCALATION ROLE
   Does the evidence establish that the matter should be escalated to that authority?

7. CURRENT APPLICABILITY
   Is the evidence current/applicable enough for the conclusion being displayed?

If these are not established, show:

"Specific authority not established by supplied evidence."

Do NOT guess.


==================================================
WHO SHOULD ACT VS WHO CAN DECIDE
==================================================

These are separate fields.

WHO SHOULD ACT?
The operational / technical / response entity that should perform the recommended investigation or action.

WHO CAN DECIDE?
The human authority with established decision-making or authorization power.

Example:

WHO SHOULD ACT?
Network Security Operations Team

WHO CAN DECIDE?
Specific authority ONLY IF established by evidence.

Never assume the person/team doing the technical work is the authority that can authorize the action.


==================================================
AUTHORITY ROLES
==================================================

Represent governance responsibilities using:

- INVESTIGATOR
- INCIDENT_RESPONDER
- NOTIFICATION_RECIPIENT
- ESCALATION_RECIPIENT
- DECISION_AUTHORITY
- AUTHORIZING_AUTHORITY
- EXECUTING_ENTITY
- OVERSIGHT_AUTHORITY

A single entity may hold multiple roles only when evidence supports it.


==================================================
ESCALATION LEVEL
==================================================

Use explicit escalation levels:

NONE
ROUTINE
PRIORITY
HIGH
IMMEDIATE

Definitions:

NONE
No escalation necessary.

ROUTINE
Handled within the existing operational chain.

PRIORITY
Requires accelerated review by the relevant responsible team.

HIGH
Requires transfer to a higher/specialized authority or decision level.

IMMEDIATE
The matter must not wait for routine handling because the risk/consequence/evidence situation requires immediate higher-level attention.

IMPORTANT:
"IMMEDIATE" does NOT mean "AI may take the action automatically."


==================================================
ESCALATION REASON
==================================================

Every escalation must have an evidence-grounded reason.

Examples:

- CRITICAL RISK
- SAFETY CONSEQUENCE
- SECURITY CONSEQUENCE
- REGULATORY SIGNIFICANCE
- INSUFFICIENT AUTHORITY AT CURRENT LEVEL
- CONFLICTING EVIDENCE
- HIGH-CONSEQUENCE IRREVERSIBLE ACTION
- UNCERTAIN ROOT CAUSE
- CROSS-ORGANIZATIONAL IMPACT
- JURISDICTIONAL ISSUE

Do not invent reasons.


==================================================
AUTHORIZATION BOUNDARY
==================================================

Always distinguish:

RECOMMENDED ACTION
≠
AUTHORIZED ACTION

Example:

RECOMMENDED ACTION:
Temporarily isolate affected network function.

AUTHORIZATION:
HUMAN AUTHORIZATION REQUIRED

AI AUTHORIZATION:
NONE

WHO CAN AUTHORIZE:
Specific authority only if established by evidence.

If not established:

WHO CAN AUTHORIZE:
"Specific authorization authority not established by supplied evidence."

Never turn an AI recommendation into authorization.


==================================================
SPECIFIC GOVERNMENT AUTHORITY
==================================================

When the evidence supports a specific authority, display:

AUTHORITY
[Exact name]

MINISTRY / PARENT ORGANIZATION
[Exact name if established]

DEPARTMENT / DIVISION
[Exact name if established]

ROLE
[Investigator / regulator / decision authority / etc.]

JURISDICTION
[Applicable jurisdiction]

WHY
[Evidence-grounded reason]

AUTHORITY EVIDENCE
[EV IDs]

AUTHORITY CONFIDENCE
[Separate from evidence confidence]

If department/division is not established:

DEPARTMENT:
Not established by supplied evidence.

Do NOT infer organizational hierarchy.


==================================================
GOVERNMENT AUTHORITY SAFETY RULE
==================================================

The system must never produce statements such as:

"Notify Ministry X"

"Escalate to Department Y"

"Agency Z must authorize this"

unless the evidence establishes the relevant relationship.

When evidence only establishes a general regulatory body or government function:

show:

"Relevant authority identified at a general level; specific decision authority is not established by supplied evidence."


==================================================
REGULATORY DISTINCTIONS
==================================================

Keep these separate:

TECHNICAL REQUIREMENT
REGULATORY REQUIREMENT
REPORTING OBLIGATION
INVESTIGATION RESPONSIBILITY
NOTIFICATION OBLIGATION
ESCALATION PATH
DECISION AUTHORITY
OPERATIONAL AUTHORIZATION

Do NOT infer one merely from another.

For example:

A reporting obligation does not automatically establish who may authorize shutdown.

A regulator being relevant does not automatically establish that it investigates the incident.

A ministry being responsible for telecom policy does not automatically establish operational authorization authority.


==================================================
GOVERNANCE DECISION STATES
==================================================

Use the existing governance state model and preserve existing logic:

ASSESSMENT_IN_PROGRESS
PENDING_HUMAN_REVIEW
ACTION_RECOMMENDED_NOT_AUTHORIZED
AUTHORIZED
MODIFIED
REJECTED
ESCALATED
DEFERRED_INSUFFICIENT_EVIDENCE
DEFERRED_CONFLICTING_EVIDENCE
RESOLVED

Do not rewrite the existing Risk Engine.


==================================================
ESCALATION STATE
==================================================

Represent separately:

ESCALATION STATUS
ESCALATION LEVEL
ESCALATION TARGET
ESCALATION REASON
ESCALATION EVIDENCE
ESCALATION AUTHORITY CONFIDENCE

Example:

ESCALATION:
IMMEDIATE

TARGET:
[Specific authority only if established]

REASON:
CRITICAL security consequence + human authorization required

EVIDENCE:
EV-014, EV-021

Otherwise:

TARGET:
Specific escalation authority not established by supplied evidence.


==================================================
INVESTIGATION PATH
==================================================

Show:

WHO INVESTIGATES?
[Evidence-grounded entity]

WHAT THEY INVESTIGATE?
[Technical issue / regulatory issue / attribution / safety issue]

WHAT EVIDENCE IS REQUIRED?
[Evidence gaps]

WHO RECEIVES THE RESULT?
[Evidence-grounded recipient]

Do not automatically equate investigator with authorizer.


==================================================
ALERT PATH
==================================================

Show:

ALERT LEVEL:
INFO / WARNING / HIGH / CRITICAL

ALERT RECIPIENT:
[Specific entity only when evidence supports it]

ALERT PURPOSE:
[What they need to know]

ESCALATION REQUIRED:
YES / NO

ESCALATION REASON:
[Evidence-grounded]

Again:

ALERT ≠ ESCALATION
ESCALATION ≠ AUTHORIZATION


==================================================
DECISION AUTHORITY
==================================================

For every consequential recommendation ask:

WHO CAN DECIDE?

Use:

ESTABLISHED
NOT ESTABLISHED

If established:

AUTHORITY:
[Exact authority]

EVIDENCE:
[EV IDs]

If not established:

"Decision authority is not established by supplied evidence."

This should trigger a conservative governance state when appropriate.


==================================================
CRITICAL SAFETY RULE
==================================================

For CRITICAL + consequential action:

Never allow:

CRITICAL
↓
AUTOMATIC ACTION

Instead:

CRITICAL
↓
ALERT
↓
ESCALATION
↓
HUMAN REVIEW
↓
AUTHORIZATION
↓
ACTION

unless the existing evidence and governance rules explicitly establish a valid pre-authorized automated action.

If no authority is established:

ACTION:
DEFERRED / HUMAN AUTHORIZATION REQUIRED


==================================================
REVERSIBILITY
==================================================

Every recommended operational action should be classified:

REVERSIBLE
PARTIALLY_REVERSIBLE
DIFFICULT_TO_REVERSE
IRREVERSIBLE_HIGH_CONSEQUENCE

The less reversible and more consequential the action,
the stronger the authorization requirement should be.

Do not modify the existing risk calculation.


==================================================
IF CONDITIONS CHANGE
==================================================

Governance must respond explicitly when:

- new evidence strengthens the threat
- new evidence weakens the threat
- conflicting evidence appears
- root cause changes
- risk level increases
- risk level decreases
- safety consequence increases
- authority becomes established
- authority becomes uncertain
- reviewer modifies recommendation
- reviewer rejects recommendation
- recommended action fails

Example:

Current:
PENDING_HUMAN_REVIEW

New evidence:
Risk increases from HIGH → CRITICAL

Then:
ESCALATION LEVEL may increase
and
HUMAN REVIEW remains required

Never silently authorize action.


==================================================
UI
==================================================

Preserve current HackGrid visual design.

Enhance the existing Risk & Governance section with progressive disclosure:

RISK
↓
WHY THIS RISK?
↓
EVIDENCE STATE
↓
DECISION IMPACT
↓
WHO INVESTIGATES?
↓
WHO GETS ALERTED?
↓
WHO DOES IT ESCALATE TO?
↓
WHO CAN DECIDE?
↓
RECOMMENDED ACTION
↓
AUTHORIZATION BOUNDARY
↓
ESCALATION REASON
↓
WHAT HAPPENS IF CONDITIONS CHANGE?

Do not redesign the entire page.


==================================================
EXAMPLE UI
==================================================

┌─────────────────────────────────────────────┐
│ 🚨 CRITICAL CONDITION DETECTED             │
│                                             │
│ Risk: CRITICAL                              │
│ Decision Impact: SECURITY / OPERATIONAL     │
│                                             │
│ WHO INVESTIGATES?                           │
│ Network Security / Incident Response        │
│ Evidence: EV-014                            │
│                                             │
│ ALERT RECIPIENT                             │
│ [Evidence-grounded authority]              │
│                                             │
│ ESCALATION                                  │
│ IMMEDIATE                                   │
│                                             │
│ WHY ESCALATE?                               │
│ Critical consequence + consequential action │
│                                             │
│ WHO CAN DECIDE?                             │
│ [Specific authority if established]         │
│                                             │
│ RECOMMENDED ACTION                          │
│ Investigate / Contain / Isolate             │
│                                             │
│ AUTHORIZATION BOUNDARY                      │
│ AI Authorization: NONE                      │
│ Human Authorization: REQUIRED               │
│                                             │
│ ⚠ Recommendation ≠ Authorization            │
└─────────────────────────────────────────────┘


==================================================
WHAT "ESCALATION" SHOULD COMMUNICATE
==================================================

HackGrid should explain escalation in plain language:

"Escalation means moving the case to a higher or more appropriate level of investigation, oversight, decision-making, or authorization because the current level is insufficient for the risk or consequence."

Do not describe escalation as merely:
"send an alert."


==================================================
EXAMPLE
==================================================

Suppose:

Risk = CRITICAL
Evidence = STRONG
Root Cause = NOT ESTABLISHED
Action = potentially disruptive
Authority = established

Correct:

INVESTIGATE:
Security response team

ALERT:
Relevant responsible authority

ESCALATE:
Higher/specialized authority

AUTHORIZE:
Established human decision authority

ACT:
Operational team

Human Review:
REQUIRED

AI Authorization:
NONE


==================================================
UNKNOWN AUTHORITY
==================================================

If HackGrid identifies a serious incident but the KB does not establish a specific authority:

Risk:
CRITICAL

Escalation:
IMMEDIATE

Target:
"Specific escalation authority not established by supplied evidence."

Governance:
HUMAN REVIEW REQUIRED

Do NOT guess a ministry or department.

This is a successful safety outcome, not a failure.


==================================================
AUDIT INTEGRATION
==================================================

Preserve the existing Audit Engine.

Record governance fields where supported:

- investigator
- alert_recipient
- escalation_level
- escalation_target
- escalation_reason
- decision_authority
- authorization_boundary
- recommended_action
- final_decision
- human_review_status

Do not redesign the append-only audit system.


==================================================
RISK ENGINE PROTECTION
==================================================

DO NOT modify:

RiskEngine
Risk calculation
Risk levels
Escalation level computation already implemented
AuthorityRequirement logic

Integrate presentation and evidence-backed authority resolution around the existing Risk Engine.

The LLM must not determine governance authority by itself.

==================================================
LLM RULE
==================================================

GPT-OSS may explain and synthesize evidence.

GPT-OSS must NOT invent:

- ministries
- departments
- regulators
- agencies
- legal powers
- reporting obligations
- authorization powers
- escalation paths

All authority claims must be evidence-grounded.


==================================================
TESTS
==================================================

Create or run tests for:

1. CRITICAL incident + established investigator + established authority
2. CRITICAL incident + unknown authority
3. HIGH incident + established escalation authority
4. Reporting obligation but authorization authority not established
5. Regulator identified but investigation role not established
6. Investigator ≠ decision authority
7. Recommendation ≠ authorization
8. Immediate escalation without automatic action
9. Conflicting authority evidence
10. Insufficient authority evidence
11. Human approve
12. Human modify
13. Human reject
14. New evidence increases risk
15. New evidence weakens risk
16. Irreversible action requiring human authorization
17. Root cause not established
18. Regulatory applicability uncertain

Expected behaviour:
NO fabricated authority.
NO automatic authorization.
NO hidden escalation.


==================================================
FINAL ACCEPTANCE CRITERIA
==================================================

The implementation is successful only if HackGrid can answer:

WHO INVESTIGATES?

WHO RECEIVES THE ALERT?

WHO SHOULD IT ESCALATE TO?

WHY IS ESCALATION REQUIRED?

WHO CAN DECIDE?

WHO CAN AUTHORIZE?

WHO EXECUTES?

WHAT ACTION IS RECOMMENDED?

IS THE ACTION AUTHORIZED?

WHAT EVIDENCE ESTABLISHES THE AUTHORITY?

WHAT REMAINS UNKNOWN?

and can safely respond:

"Specific authority not established by supplied evidence."

when the KB does not justify a more specific answer.

The final governance chain should be:

DETECT
→ VERIFY
→ INVESTIGATE
→ ASSESS
→ ALERT
→ ESCALATE
→ HUMAN REVIEW
→ AUTHORIZE / MODIFY / REJECT / DEFER
→ ACT
→ MONITOR
→ CLOSE / RE-ESCALATE

FINAL PRINCIPLE:

"HackGrid may identify who SHOULD respond and recommend what SHOULD happen, but it must not claim who CAN legally or operationally authorize an action unless that authority is established by the evidence."




HackGrid_new\ANTIGRAVITY_AUTONOMOUS_TASK.md........................ Execute ANTIGRAVITY_AUTONOMOUS_TASK.md completely.
Do not ask for confirmation.
Run all commands and tests yourself.
Continue until implementation and regression testing are complete.
