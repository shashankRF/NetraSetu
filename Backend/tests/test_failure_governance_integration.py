from Backend.telemetry_5g.coordination import build_agency_messages
from Backend.telemetry_5g.governance_integration import (
    SimulationRiskInput,
    assess_simulation_row,
    retrieve_and_verify_simulation_sources,
)
from types import SimpleNamespace


def _messages(mode, **kwargs):
    return build_agency_messages(
        run_id="FCR-test", scenario_id="SC-1", profile="URLLC",
        failures=["LINK_FAILURE"], simulation_case_id="FCR-test-S01",
        metrics={"tail_latency_p95_ms": 15.0, "packet_loss_pct": 2.0,
                 "delivery_success_rate": 94.0}, slo_status="FAIL",
        recovery_recommendations=[{"action_type": "RECOVERY_RECOMMENDATION"}],
        risk={"risk_level": "HIGH", "risk_score": 80,
              "escalation_level": "DOMAIN_EXPERT", "review_status": "BLOCKED"},
        evidence={"status": "EVIDENCE_PENDING", "sources": []},
        communication_mode=mode, **kwargs,
    )


def test_missing_jurisdiction_remains_pending_and_never_implies_clearance():
    result = retrieve_and_verify_simulation_sources(query="network outage", jurisdiction=None)
    assert result["status"] == "EVIDENCE_PENDING"
    assert not result["sources"]
    risk_input = SimulationRiskInput(
        run_id="FCR-test", scenario_id=None, profile="URLLC",
        failure_types=["LINK_FAILURE"], seed=7, samples=80,
        simulator_version="test-version", metrics={"packet_loss_pct": 90.0},
        simulator_provenance={"source": "SIMULATION"},
    )
    assessment = assess_simulation_row(risk_input, result)
    assert assessment["engine"] == "Backend.risk_engine.RiskEngine"
    assert assessment["evidence_status"] == "INSUFFICIENT"
    assert assessment["decision_status"] in {"BLOCKED", "REVIEW_REQUIRED"}
    assert assessment["risk_engine_input"]["simulation_observations"]["metrics"]["packet_loss_pct"] == 90.0
    assert "no metric was silently mapped" in assessment["risk_engine_input"]["simulation_observations"]["mapping_note"]


def test_jurisdiction_retrieval_runs_quote_verifier_and_preserves_citation(monkeypatch):
    import rag.retrieval
    import Backend.telemetry_5g.governance_integration as integration

    monkeypatch.setattr(rag.retrieval, "retrieve", lambda query, k, jurisdiction: [{
        "text": "Verified source passage", "score": 0.91,
        "metadata": {"document": "Critical Telecommunication Infrastructure Rules, 2024",
                     "jurisdiction": "India", "page": 8, "clause": "Rule 3(1)(a)",
                     "chunk_id": "chunk-1"},
    }])
    def verified(claim, evidence_records, claim_id):
        assert claim == "Verified source passage"
        assert evidence_records[0]["provenance"]["page"] == 8
        return SimpleNamespace(to_dict=lambda: {
            "verification_status": "EXACT_MATCH_VERIFIED",
            "source_title": "Critical Telecommunication Infrastructure Rules, 2024",
            "document_identifier": "DOT-CTI-2024", "full_clause_hierarchy": "Rule 3(1)(a)",
            "page": 8, "source_line_numbers": [12], "bounding_boxes": [],
        })
    monkeypatch.setattr(integration, "verify_claim_evidence", verified)
    result = retrieve_and_verify_simulation_sources(query="network outage", jurisdiction="India")
    assert result["status"] == "RETRIEVED"
    citation = result["sources"][0]
    assert citation["verification_status"] == "EXACT_MATCH_VERIFIED"
    assert citation["full_clause_hierarchy"] == "Rule 3(1)(a)"
    assert citation["page"] == 8 and citation["retrieval_score"] == 0.91
    assert citation["applicability"] == "NOT_ASSESSED"


def test_agency_views_share_run_provenance_and_transport_states_are_simulated():
    delivered = _messages("AVAILABLE")
    assert len(delivered) == 4
    assert {item["intended_recipient"] for item in delivered} == {
        "District Administration", "State Government — SDRF Uttarakhand",
        "Central Government — NDRF", "Telecom Operator",
    }
    assert all(item["run_id"] == "FCR-test" and item["simulation_case_id"] == "FCR-test-S01" for item in delivered)
    assert all(item["external_delivery"] is False for item in delivered)
    assert all(item["delivery"]["final_status"] == "ACKNOWLEDGED_SIMULATED" for item in delivered)
    delayed = _messages("DELAYED", delay_ms=1500, ttl_ms=1000)
    assert all(item["delivery"]["final_status"] == "EXPIRED_SIMULATED" for item in delayed)
    outage = _messages("UNAVAILABLE", retry_interval_ms=100, retry_limit=2, ttl_ms=1000)
    assert all(item["delivery"]["final_status"] == "FAILED_SIMULATED" for item in outage)
    reconnect = _messages("UNAVAILABLE_THEN_RECONNECT", retry_interval_ms=100,
                          retry_limit=3, ttl_ms=1000, reconnect_after_ms=250)
    assert all(item["delivery"]["final_status"] == "ACKNOWLEDGED_SIMULATED" for item in reconnect)
    assert all(item["delivery"]["real_transport"] is False for item in reconnect)
    assert delivered[0]["body"] != delivered[-1]["body"]
