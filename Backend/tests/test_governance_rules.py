from __future__ import annotations

from Backend.evidence_engine.gap_adapter import build_gap_input


class FakeEvidenceAssessment:

    overall_status = type(
        "Status",
        (),
        {"value": "SUFFICIENT"},
    )()

    overall_strength = type(
        "Strength",
        (),
        {"value": "INSUFFICIENT"},
    )()

    supporting_count = 0
    contradicting_count = 0
    primary_source_count = 0
    official_source_count = 0
    source_diversity = 0
    overall_confidence = 0.70
    missing_evidence = []


def test_explicit_absence_claim():

    evidence = FakeEvidenceAssessment()

    absence = [
        {
            "claim": (
                "Does the knowledge base prove "
                "that India has no regulation?"
            ),
            "verification_status": (
                "ABSENCE_NOT_ESTABLISHED"
            ),
        }
    ]

    result = build_gap_input(
        evidence,
        absence,
    )

    assert (
        result["overall_status"]
        == "ABSENCE_NOT_ESTABLISHED"
    )

    print("ABSENCE CLAIM TEST: PASS")


def test_normal_decision_claim():

    evidence = FakeEvidenceAssessment()

    absence = [
        {
            "claim": (
                "Should an AI system automatically "
                "approve this decision?"
            ),
            "verification_status": (
                "ABSENCE_NOT_ESTABLISHED"
            ),
        }
    ]

    result = build_gap_input(
        evidence,
        absence,
    )

    assert (
        result["overall_status"]
        == "SUFFICIENT"
    )

    print("NORMAL DECISION CLAIM TEST: PASS")


if __name__ == "__main__":

    test_explicit_absence_claim()

    test_normal_decision_claim()

    print("GOVERNANCE TESTS: PASS")