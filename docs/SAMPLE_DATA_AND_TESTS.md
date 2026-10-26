# Sample Data and Test Cases

This guide points to fixtures already in the repository; it does not introduce real-world incident claims or new synthetic observations.

## Samples available in the repository

| Example | Location | How to interpret it |
|---|---|---|
| Dashboard scenario catalogue | `Backend/demo_scenarios/library.py` | Five dashboard examples with three steps each: two telecom/5G and three disaster-management scenarios. They are explicitly marked simulated; use the Dashboard Overview selector. |
| ECR-5G traffic and outage cases | `Backend/ecr5g/scenarios.py` | Eight synthetic emulator scenarios for comparing configured schedulers. They are not live network traces or standards certification. |
| Aftermath incident-state fixtures | `Backend/aftermath_fixtures.py` | Three deterministic, synthetic Uttarakhand assessment variants. Asset, population, road, telemetry, and agency values are fictional. |
| Multi-failure cases | `Backend/telemetry_5g/combination_engine.py` | Bounded cases generated from selected failure types, sample count, seed, and trial settings. The simulator declares modeled ranges; no stored output is a field measurement. |
| Historic Dharali source documents | `knowledge_base/Dharali Incident 2025/` | Official GSI preliminary note and NRSC/ISRO NDEM damage-assessment PDF for the 5 August 2025 Kheer Gad event. These are historic source records, not current facility observations. |
| Map source snapshots and boundary inputs | `Backend/disaster_map_data/`, `Backend/disaster_map_boundaries/` | Dated report data and administrative boundaries served with source/freshness/precision metadata. A report or warning is not automatically a confirmed incident perimeter. |
| Example research questions | `Backend/benchmarks/benchmark_questions.json` | Ten question records with IDs B001–B010 for the benchmark workflow. |
| Expected-label snapshot | `Backend/benchmarks/evaluation/gold_labels.json` | Ten ID-keyed expected evidence-status / human-review labels. These are evaluation labels, not government rules or incident reports. |
| Historical benchmark output | `Backend/benchmarks/results/benchmark_results.json` and sibling result JSON files | A saved run dated 5 October 2026. It is a historical artifact, not proof of current model accuracy or a result from the current code revision. Rerun before presenting performance numbers. |

The historical result file currently yields **7/10 evidence-status matches and 8/10 human-review matches** when processed by the checked-in evaluator. These are comparisons to the small saved label set and old run only; they are not current-system accuracy claims.

`demo_data/` contains five older domain-oriented JSON artifacts; treat them as legacy sample artifacts, not as the current source of truth for the dashboard's five overview scenarios. The dashboard catalogue in `Backend/demo_scenarios/library.py` is authoritative for those current examples.

For a concrete benchmark prompt, B001 asks: “What security requirements apply to 5G network slicing in India?” B002 asks: “What is network slicing in a 5G network?” The stored gold labels cover only evidence status and whether human review is expected; they are not a comprehensive legal-ground-truth set.

## Reproducible checks

Install runtime and test dependencies as described in the root [README](../README.md), then run from the repository root:

```powershell
# Scenario catalogue and synthetic-data contract
python -m pytest Backend/tests/test_demo_scenarios.py -q

# Historic Dharali source search, citations, and governance integration
python -m pytest Backend/tests/test_aftermath_api.py -q

# Multi-failure engine, API contract, persistence, and simulator metrics
python -m pytest Backend/tests/test_failure_combination_engine.py -q

# Citation verification and PDF viewer resolution
python -m pytest Backend/tests/test_source_clause_verification.py Backend/tests/test_document_viewer_resolution.py -q

# Browser-side dashboard, map, ECR-5G, gap, and p95 rendering contracts
node --test Frontend/tests/disaster_map.test.js Frontend/tests/ecr5g.test.js Frontend/tests/gap_analysis.test.js Frontend/tests/latency_chart.test.js
```

Tests that initialize embedding/reranking models can take longer and may need cached model weights. Provider-backed tests are opt-in and require `NETRASETU_RUN_LIVE_API_TESTS=1` plus `GROQ_API_KEY`; keep credentials out of logs and source control.

## Evaluation limits

- The checked-in benchmark output represents a past run. It must not be described as a current pass rate without rerunning it against the current code, corpus, and configuration.
- A label measures agreement with the provided expected field; it does not establish legal correctness or incident truth.
- Synthetic cases support repeatable software checks only. They do not represent real Uttarakhand facilities, telecom operators, affected populations, or agency messages.
- Historic PDFs support claims only within the dates, pages, and statements they contain. Verify the original document and current authoritative information before operational use.
