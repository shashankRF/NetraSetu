"""Compare saved pipeline outputs with the checked-in expected-label set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BENCHMARK_DIR = Path(__file__).resolve().parents[1]
RESULTS_FILE = BENCHMARK_DIR / "results" / "benchmark_results.json"
GOLD_FILE = Path(__file__).resolve().parent / "gold_labels.json"
OUTPUT_FILE = BENCHMARK_DIR / "results" / "gold_evaluation.json"


def evaluate(results: dict[str, Any], gold_labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Return exact-field agreement counts; skip unsuccessful or unlabelled cases."""
    gold = {item["id"]: item["expected"] for item in gold_labels}
    evaluations = []
    evidence_correct = evidence_total = 0
    review_correct = review_total = 0

    for case in results.get("cases", []):
        case_id = case.get("id")
        if case.get("status") != "SUCCESS" or case_id not in gold:
            continue

        expected = gold[case_id]
        pipeline = case.get("pipeline") or {}
        actual_evidence = (pipeline.get("evidence_assessment") or {}).get("overall_status")
        actual_review = (pipeline.get("risk_assessment") or {}).get("human_review_required")
        expected_evidence = expected.get("evidence_status")
        expected_review = expected.get("human_review_required")
        evidence_match = actual_evidence == expected_evidence
        review_match = actual_review == expected_review
        evidence_correct += int(evidence_match)
        review_correct += int(review_match)
        evidence_total += 1
        review_total += 1
        evaluations.append({
            "id": case_id,
            "expected_evidence_status": expected_evidence,
            "actual_evidence_status": actual_evidence,
            "evidence_status_match": evidence_match,
            "expected_human_review": expected_review,
            "actual_human_review": actual_review,
            "human_review_match": review_match,
        })

    return {
        "evidence_status_accuracy": round(evidence_correct / evidence_total, 4) if evidence_total else 0,
        "human_review_accuracy": round(review_correct / review_total, 4) if review_total else 0,
        "evidence_correct": evidence_correct,
        "evidence_total": evidence_total,
        "human_review_correct": review_correct,
        "human_review_total": review_total,
        "cases": evaluations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_FILE)
    parser.add_argument("--labels", type=Path, default=GOLD_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args(argv)

    with args.results.open("r", encoding="utf-8") as stream:
        results = json.load(stream)
    with args.labels.open("r", encoding="utf-8") as stream:
        labels = json.load(stream)

    output = evaluate(results, labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("NetraSetu - expected-label agreement (not a legal or operational certification)")
    print(f"Evidence status agreement: {output['evidence_correct']}/{output['evidence_total']}")
    print(f"Human-review agreement: {output['human_review_correct']}/{output['human_review_total']}")
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
