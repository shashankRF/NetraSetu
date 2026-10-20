import json
import os


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

GOLD_FILE = os.path.join(
    BASE_DIR,
    "benchmarks",
    "evaluation",
    "gold_labels.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "benchmarks",
    "results",
    "gold_evaluation.json"
)


def main():

    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold_labels = json.load(f)

    gold = {
        item["id"]: item["expected"]
        for item in gold_labels
    }

    evaluations = []

    evidence_correct = 0
    evidence_total = 0

    review_correct = 0
    review_total = 0

    for case in results.get("cases", []):

        case_id = case["id"]

        if case.get("status") != "SUCCESS":
            continue

        if case_id not in gold:
            continue

        expected = gold[case_id]

        pipeline = case["pipeline"]

        actual_evidence_status = (
            pipeline
            .get("evidence_assessment", {})
            .get("overall_status")
        )

        actual_review = (
            pipeline
            .get("risk_assessment", {})
            .get("human_review_required")
        )

        expected_evidence_status = expected.get(
            "evidence_status"
        )

        expected_review = expected.get(
            "human_review_required"
        )

        evidence_match = (
            actual_evidence_status
            == expected_evidence_status
        )

        review_match = (
            actual_review
            == expected_review
        )

        evidence_total += 1
        review_total += 1

        if evidence_match:
            evidence_correct += 1

        if review_match:
            review_correct += 1

        evaluations.append({
            "id": case_id,

            "expected_evidence_status":
                expected_evidence_status,

            "actual_evidence_status":
                actual_evidence_status,

            "evidence_status_match":
                evidence_match,

            "expected_human_review":
                expected_review,

            "actual_human_review":
                actual_review,

            "human_review_match":
                review_match
        })

    evidence_accuracy = (
        evidence_correct / evidence_total
        if evidence_total
        else 0
    )

    review_accuracy = (
        review_correct / review_total
        if review_total
        else 0
    )

    output = {
        "evidence_status_accuracy":
            round(evidence_accuracy, 4),

        "human_review_accuracy":
            round(review_accuracy, 4),

        "evidence_correct":
            evidence_correct,

        "evidence_total":
            evidence_total,

        "human_review_correct":
            review_correct,

        "human_review_total":
            review_total,

        "cases":
            evaluations
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2
        )

    print("=" * 80)
    print("HACKGRID — MISSION 18 GOLD EVALUATION")
    print("=" * 80)

    print(
        "Evidence status accuracy:",
        round(evidence_accuracy * 100, 2),
        "%"
    )

    print(
        "Human-review accuracy:",
        round(review_accuracy * 100, 2),
        "%"
    )

    print("=" * 80)

    print(
        f"Saved: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()