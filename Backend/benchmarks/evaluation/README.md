# Evidence Pipeline Evaluation Artifacts

This directory contains the expected-label snapshot and evaluation helpers used by the benchmark scripts. It is research tooling, not a certification suite.

## Inputs and outputs

- Questions: [`../benchmark_questions.json`](../benchmark_questions.json), IDs B001–B010.
- Expected labels: [`gold_labels.json`](gold_labels.json), joined to benchmark cases by ID. Each entry currently supplies `expected.evidence_status` and `expected.human_review_required`; `gold_schema.json` describes these fields and allowed evidence statuses.
- Evaluator: [`gold_evaluator.py`](gold_evaluator.py).
- Benchmark runner: [`../run_benchmark.py`](../run_benchmark.py), which calls the existing `Backend.orchestrator.run_pipeline`.
- Saved outputs: [`../results/`](../results/). These are generated artifacts, not source labels.

Run the benchmark from the repository root with:

```powershell
python -m Backend.benchmarks.run_benchmark
python Backend/benchmarks/evaluation/gold_evaluator.py
```

The benchmark runs retrieval/model components and can take time; provider-backed behavior depends on local model configuration. Do not run it merely to refresh numbers during documentation checks.

## Interpretation and limitations

The checked-in result snapshot dates from 5 October 2026 and carries the legacy `hackgrid-benchmark-v1` label. The active runner now writes `netrasetu-benchmark-v1`; saved metrics and scorecard artifacts do not all describe one consistent current run. Treat the checked-in results as historical artifacts, not as current accuracy or proof that all benchmark cases pass. Rerun with a recorded code revision, corpus/index version, model configuration, and label version before reporting performance.

The current expected labels are compact and do not contain independent source citations or detailed rationale per case. Agreement with these fields is not legal validation, incident verification, or operational certification. Failure to retrieve evidence does not prove that a rule or requirement does not exist.
