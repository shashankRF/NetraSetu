"""
HackGrid Governance Invariant Tests
====================================

These tests are deterministic and DO NOT call GPT-OSS.

They protect the core governance guarantees:

1. Absence of evidence is not proof of absence.
2. A policy gap must not be declared without positive evidence.
3. Consequential compliance decisions require human review.
"""

from Backend.governance import evaluate_governance


# ---------------------------------------------------------------------------
# B005
# ---------------------------------------------------------------------------

def test_b005_policy_gap_not_established():

    question = (
        "Does the available evidence establish a policy gap "
        "for AI-based network slicing?"
    )

    result = evaluate_governance(
        question=question,
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
        classification={
            "classifications": []
        },
    )

    assert result["status"] == "POLICY_GAP_NOT_ESTABLISHED"

    assert result["evidence_status"] == "INSUFFICIENT"

    assert result["gap_status"] == "ABSENCE_NOT_ESTABLISHED"

    assert result["human_review_required"] is True

    assert result["escalation_level"] == "SENIOR_AUTHORITY"


# ---------------------------------------------------------------------------
# B009
# ---------------------------------------------------------------------------

def test_b009_regulatory_absence_not_established():

    question = (
        "Does the KB prove India has no regulation governing "
        "AI-based telecom network orchestration?"
    )

    result = evaluate_governance(
        question=question,
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
                    "status": "INSUFFICIENT",
                    "claim": (
                        "The available knowledge base does not prove "
                        "that no regulation exists."
                    ),
                }
            ]
        },
    )

    assert (
        result["status"]
        == "REGULATORY_ABSENCE_NOT_ESTABLISHED"
    )

    assert result["evidence_status"] == "INSUFFICIENT"

    assert result["gap_status"] == "ABSENCE_NOT_ESTABLISHED"

    assert result["human_review_required"] is True

    assert result["escalation_level"] == "SENIOR_AUTHORITY"


# ---------------------------------------------------------------------------
# B010
# ---------------------------------------------------------------------------

def test_b010_human_review_required():

    question = (
        "Should a consequential telecom compliance decision "
        "be automatically approved by AI?"
    )

    result = evaluate_governance(
        question=question,
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
                        "A consequential telecom compliance decision "
                        "should not be automatically approved by AI."
                    ),
                }
            ]
        },
    )

    assert result["status"] == "HUMAN_REVIEW_REQUIRED"

    assert result["risk_level"] == "CRITICAL"

    assert result["human_review_required"] is True

    assert result["escalation_level"] == "SENIOR_AUTHORITY"


# ---------------------------------------------------------------------------
# General safety test
# ---------------------------------------------------------------------------

def test_absence_is_not_proven_by_retrieval_failure():

    question = (
        "Does the KB prove that there is no regulation "
        "for this technology?"
    )

    result = evaluate_governance(
        question=question,
        evidence_assessment={
            "overall_status": "INSUFFICIENT"
        },
        gap_analysis={
            "overall_status": "INSUFFICIENT"
        },
        risk_assessment={
            "risk_level": "HIGH",
            "human_review_required": True,
            "escalation_level": "DOMAIN_EXPERT",
        },
        final_synthesis={}
    )

    assert (
        result["status"]
        == "REGULATORY_ABSENCE_NOT_ESTABLISHED"
    )

    assert (
        result["gap_status"]
        == "ABSENCE_NOT_ESTABLISHED"
    )

    assert result["human_review_required"] is True