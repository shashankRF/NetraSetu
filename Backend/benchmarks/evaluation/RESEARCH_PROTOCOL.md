# HackGrid Research Evaluation Protocol

## Objective

Evaluate whether HackGrid can produce evidence-grounded,
uncertainty-aware, risk-aware assessments from a regulatory and
technical knowledge base.

## Primary Research Questions

### RQ1 — Retrieval

Can HackGrid retrieve evidence relevant to a technical or
regulatory question?

### RQ2 — Evidence

Can HackGrid distinguish sufficient, insufficient, conflicting,
limiting, and contextual evidence?

### RQ3 — Grounding

Can substantive claims be mapped to retrieved evidence?

### RQ4 — Absence

Can HackGrid avoid interpreting retrieval failure as proof
of regulatory or policy absence?

### RQ5 — Gap Analysis

Can HackGrid distinguish a genuine gap from insufficient evidence?

### RQ6 — Risk

Can HackGrid account for consequence and evidence quality when
assessing decision risk?

### RQ7 — Human Oversight

Can HackGrid prevent high-impact regulatory or security decisions
from being automatically finalized?

### RQ8 — Auditability

Can each assessment be reconstructed from its evidence,
classification, risk, synthesis, and audit record?

## Evaluation Metrics

- Pipeline success rate
- Evidence status accuracy
- Evidence strength accuracy
- Claim grounding rate
- Unsupported claim rate
- Invalid evidence reference rate
- Absence handling accuracy
- Gap analysis accuracy
- Risk classification accuracy
- Escalation accuracy
- Human-review accuracy
- Audit coverage

## Safety Principles

1. Retrieved evidence is the factual basis.
2. The language model is not the source of truth.
3. Retrieval failure does not prove absence.
4. Uncertainty must be preserved.
5. High-impact decisions require appropriate human authority.
6. AI output is not legally authoritative.

## Benchmark Version

research-evaluation-v1