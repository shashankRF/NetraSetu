import json
import os
from collections import Counter


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

RESULTS_FILE = os.path.join(
    BASE_DIR,
    "benchmarks",
    "results",
    "benchmark_results.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "benchmarks",
    "results",
    "benchmark_metrics.json"
)


def safe_rate(numerator, denominator):
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def calculate_metrics(data):
    cases = data.get("cases", [])

    successful = [
        c for c in cases
        if c.get("status") == "SUCCESS"
    ]

    failed = [
        c for c in cases
        if c.get("status") == "FAILED"
    ]

    evidence_statuses = Counter()
    evidence_strengths = Counter()
    risk_levels = Counter()
    escalations = Counter()

    total_claims = 0
    grounded_claims = 0
    unsupported_claims = 0

    human_review_required = 0

    runtimes = []

    for case in successful:
        pipeline = case.get("pipeline", {})

        runtime = case.get("runtime_seconds")
        if runtime is not None:
            runtimes.append(runtime)

        # Evidence assessment
        assessment = pipeline.get("evidence_assessment", {})

        status = assessment.get("overall_status")
        strength = assessment.get("overall_strength")

        if status:
            evidence_statuses[status] += 1

        if strength:
            evidence_strengths[strength] += 1

        # Risk
        risk = pipeline.get("risk_assessment", {})

        risk_level = risk.get("risk_level")
        escalation = risk.get("escalation_level")

        if risk_level:
            risk_levels[risk_level] += 1

        if escalation:
            escalations[escalation] += 1

        if risk.get("human_review_required") is True:
            human_review_required += 1

        # Final synthesis
        synthesis = pipeline.get("final_synthesis", {})

        claims = synthesis.get("claims", [])

        for claim in claims:
            total_claims += 1

            evidence_ids = claim.get("evidence_ids", [])

            if evidence_ids:
                grounded_claims += 1
            else:
                unsupported_claims += 1

    average_runtime = (
        round(sum(runtimes) / len(runtimes), 2)
        if runtimes
        else 0.0
    )

    metrics = {
        "benchmark_version": data.get("benchmark_version"),

        "total_cases": len(cases),

        "successful_cases": len(successful),

        "failed_cases": len(failed),

        "pipeline_success_rate": safe_rate(
            len(successful),
            len(cases)
        ),

        "average_runtime_seconds": average_runtime,

        "evidence_status_distribution":
            dict(evidence_statuses),

        "evidence_strength_distribution":
            dict(evidence_strengths),

        "risk_level_distribution":
            dict(risk_levels),

        "escalation_distribution":
            dict(escalations),

        "human_review_cases":
            human_review_required,

        "human_review_rate":
            safe_rate(
                human_review_required,
                len(successful)
            ),

        "total_final_claims":
            total_claims,

        "grounded_claims":
            grounded_claims,

        "unsupported_claims":
            unsupported_claims,

        "claim_grounding_rate":
            safe_rate(
                grounded_claims,
                total_claims
            ),

        "unsupported_claim_rate":
            safe_rate(
                unsupported_claims,
                total_claims
            )
    }

    return metrics


def main():
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    metrics = calculate_metrics(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            metrics,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("=" * 80)
    print("HACKGRID — MISSION 16 METRICS")
    print("=" * 80)

    for key, value in metrics.items():
        print(f"{key}: {value}")

    print("=" * 80)
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()