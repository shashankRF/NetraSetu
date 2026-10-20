"""
Governance integration tests.

These tests verify the governance layer against representative
pipeline-shaped dictionaries without consuming GPT-OSS tokens.
"""

from Backend.governance import evaluate_governance


def test_b005_expected_governance_output():

    result = evaluate_governance(
        question=(
            "Does the available evidence establish a policy gap "
            "for AI-based network slicing?"
        ),
        evidence_assessment={
            "overall_status": "SUFFICIENT"
        },
        gap_analysis={
            "overall_status": "SUFFICIENT"
        },
        risk_assessment={
            "risk_level": "CRITICAL",
            "human_review_required": True,
            "escalation_level": "SENIOR_AUTHORITY",
        },
        final_synthesis={
            "claims": [
                {
                    "status": "CONTRADICTED",
                    "claim": (
                        "The available evidence does not establish "
                        "a policy gap."
                    ),
                }
            ]
        },
    )

    expected = {
        "status": "POLICY_GAP_NOT_ESTABLISHED",
        "evidence_status": "INSUFFICIENT",
        "gap_status": "ABSENCE_NOT_ESTABLISHED",
        "risk_level": "CRITICAL",
        "human_review_required": True,
        "escalation_level": "SENIOR_AUTHORITY",
    }

    for key, value in expected.items():
        assert result[key] == value, (
            f"{key}: expected {value}, "
            f"got {result.get(key)}"
        )


def test_b009_expected_governance_output():

    result = evaluate_governance(
        question=(
            "Does the KB prove India has no regulation governing "
            "AI-based telecom network orchestration?"
        ),
        evidence_assessment={
            "overall_status": "SUFFICIENT"
        },
        gap_analysis={
            "overall_status": "SUFFICIENT"
        },
        risk_assessment={
            "risk_level": "CRITICAL",
            "human_review_required": True,
            "escalation_level": "SENIOR_AUTHORITY",
        },
        final_synthesis={},
    )

    assert (
        result["status"]
        == "REGULATORY_ABSENCE_NOT_ESTABLISHED"
    )

    assert result["evidence_status"] == "INSUFFICIENT"

    assert result["gap_status"] == "ABSENCE_NOT_ESTABLISHED"

    assert result["human_review_required"] is True


def test_b010_expected_governance_output():

    result = evaluate_governance(
        question=(
            "Should a consequential telecom compliance decision "
            "be automatically approved by AI?"
        ),
        evidence_assessment={
            "overall_status": "SUFFICIENT"
        },
        gap_analysis={
            "overall_status": "SUFFICIENT"
        },
        risk_assessment={
            "risk_level": "CRITICAL",
            "human_review_required": True,
            "escalation_level": "SENIOR_AUTHORITY",
        },
        final_synthesis={},
    )

    assert result["status"] == "HUMAN_REVIEW_REQUIRED"

    assert result["risk_level"] == "CRITICAL"

    assert result["human_review_required"] is True

    assert result["escalation_level"] == "SENIOR_AUTHORITY"