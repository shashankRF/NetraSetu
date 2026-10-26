from Backend.governance import evaluate_governance


def test_governance_accepts_and_records_evidence_analysis_summary():
    result = evaluate_governance(
        question="Assess an emergency communications disruption.",
        evidence_assessment={"overall_status": "INSUFFICIENT"},
        gap_analysis={"overall_status": "ABSENCE_NOT_ESTABLISHED"},
        risk_assessment={"risk_level": "HIGH", "human_review_required": True},
        final_synthesis={"assessment": "Evidence is insufficient.", "claims": []},
        evidence_analysis={
            "candidate_count": 4,
            "supporting_evidence": [{"evidence_id": "EV-1"}],
            "contradicting_evidence": [{"evidence_id": "EV-2"}],
            "contradiction_search_performed": True,
        },
    )

    evidence_state = result["decision_governance"]["evidence_state"]
    assert evidence_state["analysis_candidate_count"] == 4
    assert evidence_state["analysis_supporting_count"] == 1
    assert evidence_state["analysis_contradicting_count"] == 1
    assert evidence_state["contradiction_search_performed"] is True
