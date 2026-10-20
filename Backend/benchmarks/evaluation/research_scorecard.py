from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[2]

RESULTS_DIR = BASE_DIR / "benchmarks" / "results"

BENCHMARK_FILE = RESULTS_DIR / "benchmark_results.json"
GROUNDING_FILE = RESULTS_DIR / "grounding_validation.json"
GOLD_FILE = RESULTS_DIR / "gold_evaluation.json"

OUTPUT_FILE = RESULTS_DIR / "research_scorecard.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 4)


def evaluate_pipeline(results: Dict[str, Any]) -> Dict[str, Any]:

    cases: List[Dict[str, Any]] = results.get("cases", [])

    total = len(cases)

    completed = 0
    successful = 0
    failed = 0

    evidence_statuses = Counter()
    evidence_strengths = Counter()
    risk_levels = Counter()
    escalation_levels = Counter()

    human_review_required = 0

    total_claims = 0
    claims_with_evidence = 0
    unsupported_claims = 0

    audit_ids = []

    for case in cases:

        if case.get("completed"):
            completed += 1

        if case.get("success"):
            successful += 1
        else:
            failed += 1

        pipeline = case.get("pipeline") or {}

        evidence = pipeline.get("evidence_assessment") or {}
        risk = pipeline.get("risk_assessment") or {}
        synthesis = pipeline.get("final_synthesis") or {}

        status = evidence.get("overall_status")

        if status:
            evidence_statuses[status] += 1

        strength = evidence.get("overall_strength")

        if strength:
            evidence_strengths[strength] += 1

        risk_level = risk.get("risk_level")

        if risk_level:
            risk_levels[risk_level] += 1

        escalation = risk.get("escalation_level")

        if escalation:
            escalation_levels[escalation] += 1

        if risk.get("human_review_required") is True:
            human_review_required += 1

        claims = synthesis.get("claims") or []

        total_claims += len(claims)

        for claim in claims:

            evidence_ids = claim.get("evidence_ids") or []

            if evidence_ids:
                claims_with_evidence += 1
            else:
                unsupported_claims += 1

        audit_id = pipeline.get("audit_id")

        if audit_id:
            audit_ids.append(audit_id)

    return {
        "pipeline": {
            "total_cases": total,
            "completed_cases": completed,
            "successful_cases": successful,
            "failed_cases": failed,
            "completion_rate": safe_rate(completed, total),
            "success_rate": safe_rate(successful, total),
        },
        "evidence": {
            "status_distribution": dict(evidence_statuses),
            "strength_distribution": dict(evidence_strengths),
        },
        "risk": {
            "risk_distribution": dict(risk_levels),
            "escalation_distribution": dict(escalation_levels),
            "human_review_cases": human_review_required,
            "human_review_rate": safe_rate(
                human_review_required,
                total,
            ),
        },
        "claims": {
            "total_claims": total_claims,
            "claims_with_evidence": claims_with_evidence,
            "unsupported_claims": unsupported_claims,
            "claim_grounding_rate": safe_rate(
                claims_with_evidence,
                total_claims,
            ),
            "unsupported_claim_rate": safe_rate(
                unsupported_claims,
                total_claims,
            ),
        },
        "audit": {
            "cases_with_audit_id": len(audit_ids),
            "audit_coverage": safe_rate(
                len(audit_ids),
                total,
            ),
            "unique_audit_ids": len(set(audit_ids)),
        },
    }


def evaluate_grounding(
    grounding: Dict[str, Any],
) -> Dict[str, Any]:

    total = grounding.get("total_claims", 0)
    grounded = grounding.get("grounded_claims", 0)
    unsupported = grounding.get("unsupported_claims", 0)
    invalid = grounding.get("invalid_evidence_claims", 0)

    return {
        "total_claims": total,
        "grounded_claims": grounded,
        "unsupported_claims": unsupported,
        "invalid_evidence_claims": invalid,
        "grounding_rate": grounding.get(
            "grounding_rate",
            safe_rate(grounded, total),
        ),
        "unsupported_claim_rate": grounding.get(
            "unsupported_claim_rate",
            safe_rate(unsupported, total),
        ),
        "invalid_reference_rate": grounding.get(
            "invalid_evidence_reference_rate",
            safe_rate(invalid, total),
        ),
    }


def evaluate_gold(
    gold: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "evidence_status_accuracy": gold.get(
            "evidence_status_accuracy"
        ),
        "human_review_accuracy": gold.get(
            "human_review_accuracy"
        ),
        "evidence_correct": gold.get(
            "evidence_correct"
        ),
        "evidence_total": gold.get(
            "evidence_total"
        ),
        "human_review_correct": gold.get(
            "human_review_correct"
        ),
        "human_review_total": gold.get(
            "human_review_total"
        ),
    }


def calculate_research_score(
    pipeline: Dict[str, Any],
    grounding: Dict[str, Any],
    gold: Dict[str, Any],
) -> Dict[str, Any]:

    metrics = []

    # Pipeline reliability
    metrics.append(
        pipeline["pipeline"]["success_rate"]
    )

    # Claim grounding
    metrics.append(
        grounding["grounding_rate"]
    )

    # Unsupported claims
    metrics.append(
        1.0 - grounding["unsupported_claim_rate"]
    )

    # Invalid evidence references
    metrics.append(
        1.0 - grounding["invalid_reference_rate"]
    )

    # Evidence status accuracy
    evidence_accuracy = gold.get(
        "evidence_status_accuracy"
    )

    if isinstance(evidence_accuracy, (int, float)):
        metrics.append(evidence_accuracy)

    # Human review accuracy
    review_accuracy = gold.get(
        "human_review_accuracy"
    )

    if isinstance(review_accuracy, (int, float)):
        metrics.append(review_accuracy)

    score = (
        sum(metrics) / len(metrics)
        if metrics
        else 0.0
    )

    return {
        "score_components": len(metrics),
        "components": metrics,
        "overall_research_score": round(score, 4),
    }


def main() -> None:

    print("=" * 70)
    print("HACKGRID — RESEARCH SCORECARD")
    print("=" * 70)

    benchmark = load_json(BENCHMARK_FILE)

    grounding = load_json(GROUNDING_FILE)

    gold = load_json(GOLD_FILE)

    pipeline_metrics = evaluate_pipeline(
        benchmark
    )

    grounding_metrics = evaluate_grounding(
        grounding
    )

    gold_metrics = evaluate_gold(
        gold
    )

    research_score = calculate_research_score(
        pipeline_metrics,
        grounding_metrics,
        gold_metrics,
    )

    report = {
        "benchmark": "HackGrid Evidence-Aware Pipeline",
        "evaluation_version": "research-scorecard-v1",
        "pipeline": pipeline_metrics,
        "grounding": grounding_metrics,
        "gold_evaluation": gold_metrics,
        "research_score": research_score,
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("PIPELINE SUCCESS:")
    print(
        pipeline_metrics["pipeline"]["success_rate"]
    )

    print("CLAIM GROUNDING:")
    print(
        grounding_metrics["grounding_rate"]
    )

    print("UNSUPPORTED CLAIM RATE:")
    print(
        grounding_metrics["unsupported_claim_rate"]
    )

    print("INVALID REFERENCE RATE:")
    print(
        grounding_metrics["invalid_reference_rate"]
    )

    print("EVIDENCE STATUS ACCURACY:")
    print(
        gold_metrics["evidence_status_accuracy"]
    )

    print("HUMAN REVIEW ACCURACY:")
    print(
        gold_metrics["human_review_accuracy"]
    )

    print()
    print(
        "OVERALL RESEARCH SCORE:",
        research_score["overall_research_score"],
    )

    print()
    print("Saved:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()