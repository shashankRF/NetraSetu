from Backend.benchmarks.evaluation.gold_evaluator import evaluate


def test_gold_evaluator_matches_nested_label_contract_and_skips_failed_cases():
    results = {
        "cases": [
            {
                "id": "CASE-1",
                "status": "SUCCESS",
                "pipeline": {
                    "evidence_assessment": {"overall_status": "SUFFICIENT"},
                    "risk_assessment": {"human_review_required": True},
                },
            },
            {"id": "CASE-2", "status": "FAILED", "pipeline": {}},
        ]
    }
    labels = [{
        "id": "CASE-1",
        "expected": {"evidence_status": "SUFFICIENT", "human_review_required": True},
    }]

    report = evaluate(results, labels)

    assert report["evidence_status_accuracy"] == 1.0
    assert report["human_review_accuracy"] == 1.0
    assert report["evidence_total"] == report["human_review_total"] == 1
    assert report["cases"][0]["evidence_status_match"] is True
