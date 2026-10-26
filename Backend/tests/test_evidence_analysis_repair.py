"""
NetraSetu Regression Tests: Evidence Analysis Pipeline and Governance Wiring
=============================================================================
Tests deterministic invariants and repairs for:
1. evaluate_governance handles evidence_analysis cleanly without UnboundLocalError
2. evaluate_governance works when evidence_analysis is omitted (defaults safely)
3. _build_empty_evidence_response creates complete structured evidence_analysis ('NO_EVIDENCE')
4. run_pipeline falls back safely if evidence analysis raises an exception ('ANALYSIS_FAILED')
5. Full end-to-end scenario execution for 5G Network Slice Security Incident (T1 - Slice anomaly, India)
6. Scenario lookup by slug ('5g-network-slice-security-incident') and canonical ID ('HG-5G-003')
"""

import pytest
from unittest.mock import patch, MagicMock
from Backend.governance import evaluate_governance
from Backend.orchestrator import _build_empty_evidence_response, run_pipeline
from Backend.demo_scenarios.library import get_scenario


def test_governance_with_valid_evidence_analysis():
    """Verify that passing valid structured evidence_analysis enriches decision governance and extracts evidence roles cleanly."""
    mock_evidence_analysis = {
        "status": "COMPLETED",
        "candidate_count": 3,
        "supporting_count": 2,
        "contradicting_count": 1,
        "contextual_count": 0,
        "supporting_evidence": [
            {"evidence_id": "EV-001", "citation_key": "3GPP-TS-33501", "excerpt": "Slice isolation required"},
            {"evidence_id": "EV-003", "citation_key": "DOT-SEC-5G", "excerpt": "Indian telecom slice policy"}
        ],
        "contradicting_evidence": [
            {"evidence_id": "EV-002", "citation_key": "CLAIM-002", "excerpt": "No isolation necessary"}
        ],
        "contextual_evidence": []
    }

    gov = evaluate_governance(
        question="What 3GPP requirements apply to 5G slice isolation?",
        evidence_assessment={"overall_status": "SUFFICIENT"},
        gap_analysis={"overall_status": "SUFFICIENT"},
        risk_assessment={
            "risk_level": "MEDIUM",
            "human_review_required": False,
            "escalation_level": "OPERATIONAL",
        },
        final_synthesis={
            "claims": [
                {
                    "claim": "5G network slices mandate cryptographically verified isolation.",
                    "status": "SUPPORTED",
                    "confidence_score": 0.95
                }
            ]
        },
        evidence_analysis=mock_evidence_analysis
    )

    assert "decision_governance" in gov
    dg = gov["decision_governance"]
    assert "evidence_state" in dg
    assert dg["evidence_state"]["analysis_candidate_count"] == 3
    assert dg["evidence_state"]["analysis_supporting_count"] == 2
    assert dg["evidence_state"]["analysis_contradicting_count"] == 1
    assert "EV-001" in dg["evidence_state"]["supporting_evidence_ids"]
    assert "EV-002" in dg["evidence_state"]["contradicting_evidence_ids"]


def test_governance_without_evidence_analysis():
    """Verify that calling evaluate_governance without evidence_analysis does not raise UnboundLocalError."""
    gov = evaluate_governance(
        question="General query without prior evidence analysis",
        evidence_assessment={"overall_status": "SUFFICIENT"},
        gap_analysis={"overall_status": "SUFFICIENT"},
        risk_assessment={
            "risk_level": "LOW",
            "human_review_required": False,
            "escalation_level": "STANDARD",
        },
        final_synthesis={
            "claims": [
                {
                    "claim": "General telecom advisory.",
                    "status": "SUPPORTED",
                    "confidence_score": 0.88
                }
            ]
        }
    )

    assert "decision_governance" in gov
    assert gov["decision_governance"]["evidence_state"]["analysis_candidate_count"] is None
    assert gov["decision_governance"]["evidence_state"]["analysis_supporting_count"] == 0


def test_build_empty_evidence_response_structure():
    """Verify _build_empty_evidence_response builds a canonical NO_EVIDENCE dictionary with valid governance."""
    resp = _build_empty_evidence_response(
        question="Unknown query",
        exec_id="EXEC-TEST-001",
        scenario_id="HG-5G-003",
        step_id="T1"
    )

    assert resp["status"] == "COMPLETED"
    assert "evidence_analysis" in resp
    ea = resp["evidence_analysis"]
    assert ea["status"] == "NO_EVIDENCE"
    assert ea["candidate_count"] == 0
    assert ea["supporting_count"] == 0
    assert ea["contradicting_count"] == 0
    assert ea["supporting_evidence"] == []
    assert ea["contradicting_evidence"] == []

    assert "governance" in resp
    assert resp["governance"]["human_review_required"] is True
    assert "audit_record" in resp


def test_orchestrator_evidence_analysis_exception_fallback():
    """Verify run_pipeline falls back to status ANALYSIS_FAILED if analyze_evidence encounters an exception."""
    with patch("Backend.orchestrator.retrieve") as mock_retriever, \
         patch("Backend.orchestrator.analyze_evidence", side_effect=Exception("Simulated evidence analysis engine crash")):

        mock_retriever.return_value = [
            {"id": "doc1", "text": "3GPP slice specs", "content": "3GPP slice specs", "score": 0.9, "metadata": {"source": "3GPP"}}
        ]

        result = run_pipeline(
            "What 3GPP and Indian requirements apply to security and isolation of 5G network slices?",
            jurisdiction="India",
            demo_mode=True,
            execution_id="EXEC-TEST-FAIL-001",
            time_budget_seconds=10.0
        )

        assert "evidence_analysis" in result
        assert result["evidence_analysis"]["status"] == "ANALYSIS_FAILED"
        assert result["evidence_analysis"]["candidate_count"] >= 1
        assert "governance" in result


def test_scenario_t1_slice_anomaly_execution():
    """Test full execution of the exact scenario: 5G Network Slice Security Incident (T1 - Slice anomaly)."""
    sc = get_scenario("HG-5G-003")
    assert sc is not None
    step = sc["steps"][0]
    assert step["step_id"] == "T1"
    prompt = step["evidence_prompt"]

    result = run_pipeline(
        prompt,
        jurisdiction="India",
        demo_mode=True,
        scenario_id="HG-5G-003",
        scenario_title=sc["title"],
        step_id="T1",
        step_title=step["title"],
        time_budget_seconds=38.0
    )

    assert result is not None
    assert "evidence_analysis" in result
    assert result["evidence_analysis"]["status"] in ("COMPLETED", "NO_EVIDENCE", "ANALYSIS_FAILED")
    assert "governance" in result
    assert "decision_governance" in result["governance"]
    assert "claims" in result["final_synthesis"]
    assert "claim_evidence_mappings" in result


def test_scenario_lookup_by_slug_and_id():
    """Verify that both slug 5g-network-slice-security-incident and ID HG-5G-003 locate the scenario."""
    sc_by_id = get_scenario("HG-5G-003")
    sc_by_slug = get_scenario("5g-network-slice-security-incident")
    assert sc_by_id is not None
    assert sc_by_slug is not None
    assert sc_by_id["scenario_id"] == sc_by_slug["scenario_id"]
    assert sc_by_id["title"] == sc_by_slug["title"]
