from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from Backend.server import app
from Backend.telemetry_5g.combination_engine import (
    CombinationValidationError,
    evaluate_policy,
    run_combination_search,
    scenario_count,
)
from Backend.telemetry_5g.models import ImpairmentType


FAILURES = [ImpairmentType.LATENCY_SPIKE.value,
            ImpairmentType.PACKET_LOSS.value,
            ImpairmentType.CONGESTION.value]


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.get("/api/auth/session").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def test_bounded_scenario_count_and_invalid_inputs():
    assert scenario_count(FAILURES, 2, 2) == 14
    with pytest.raises(CombinationValidationError):
        scenario_count(FAILURES, 4)
    with pytest.raises(CombinationValidationError):
        run_combination_search(failure_types=["NOT_A_FAILURE"], samples=100)
    with pytest.raises(CombinationValidationError):
        run_combination_search(failure_types=FAILURES, samples=20)


def test_reproducible_baseline_and_failure_combinations():
    one = run_combination_search(failure_types=FAILURES[:2], combination_depth=2,
                                 max_scenarios=4, samples=80, seed=17, trials=2)
    two = run_combination_search(failure_types=FAILURES[:2], combination_depth=2,
                                 max_scenarios=4, samples=80, seed=17, trials=2)
    assert one["status"] == "COMPLETED"
    assert len(one["results"]) == 8
    assert one["results"][0]["configuration"]["failure_types"] == []
    assert [x["metrics"] for x in one["results"]] == [x["metrics"] for x in two["results"]]
    assert one["results"][0]["scenario_id"] != two["results"][0]["scenario_id"]
    assert len({x["configuration"]["seed"] for x in one["results"] if x["trial"] == 1}) == 1
    assert len({x["configuration"]["seed"] for x in one["results"] if x["trial"] == 2}) == 1
    assert one["results"][0]["configuration"]["seed"] != one["results"][4]["configuration"]["seed"]
    assert any(x["trials"] == 2 and x["standard_deviation"] is not None for x in one["trial_summary"])
    assert one["provenance"]["real_testbed"] is False


def test_bounded_subset_is_explicitly_incomplete_and_interactions_declared():
    result = run_combination_search(failure_types=FAILURES, combination_depth=2,
                                    max_scenarios=4, samples=80, seed=4)
    assert result["status"] == "INCOMPLETE"
    assert result["search"]["complete"] is False
    assert result["search"]["omitted_scenarios"] == 3
    assert result["interaction_analysis"] == []  # bounded prefix has no pair with both singles
    full = run_combination_search(failure_types=FAILURES[:2], combination_depth=2,
                                  max_scenarios=4, samples=80, seed=4)
    assert full["interaction_analysis"]
    assert all(x["comparison_model"].startswith("ADDITIVE") for x in full["interaction_analysis"])
    assert all(x["unit"] for x in full["interaction_analysis"])


def test_user_policy_is_deterministic_and_missing_values_not_success():
    policy = evaluate_policy({"tail_latency_p95_ms": 12.0}, {"max_tail_latency_p95_ms": 10})
    assert policy["status"] == "THRESHOLD_EXCEEDED"
    assert policy["rules"][0]["origin"] == "USER_DEFINED"
    missing = evaluate_policy({}, {"max_packet_loss_pct": 1})
    assert missing["status"] == "NOT_EVALUATED"
    assert missing["rules"][0]["status"] == "NOT_EVALUATED"
    assert evaluate_policy({}, {})["status"] == "NOT_EVALUATED"
    with pytest.raises(CombinationValidationError):
        evaluate_policy({}, {"invented_metric": 4})


def test_combination_api_persists_results_and_reports_failures(monkeypatch, tmp_path: Path):
    import Backend.server as server
    import Backend.audit.recorder as recorder
    store = tmp_path / "runs.jsonl"
    monkeypatch.setattr(server, "FAILURE_COMBINATION_STORE", store)
    monkeypatch.setattr(recorder, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(recorder, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(recorder, "REVIEW_EVENTS_FILE", tmp_path / "reviews.jsonl")
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    catalog = client.get("/api/5g/failure-combinations/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["scope"].startswith("Controlled software simulation")

    response = client.post("/api/5g/failure-combinations", json={
        "profile": "URLLC", "failure_types": FAILURES[:2], "combination_depth": 2,
        "max_scenarios": 4, "samples": 80, "seed": 22,
        "thresholds": {"max_tail_latency_p95_ms": 4.0},
    }, headers=csrf_headers(client))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["results"][-1]["policy_evaluation"]["status"] in {"SATISFIED", "THRESHOLD_EXCEEDED"}
    assert data["evidence_assessment"]["status"] == "EVIDENCE_PENDING"
    assert data["integration"]["risk_engine"] == "Backend.risk_engine.RiskEngine"
    assert data["integration"]["review_gate"] in {"BLOCKED", "REVIEW_REQUIRED"}
    assert all(row["governance_assessment"]["engine"] == "Backend.risk_engine.RiskEngine"
               for row in data["results"] if row["status"] == "COMPLETED")
    assert all(row["metrics"]["simulated_post_impairment_interval_ms"] == row["metrics"]["recovery_time_ms"]
               for row in data["results"] if row["status"] == "COMPLETED")
    assert len(data["integration"]["coordination_messages"]) == 4
    assert all(message["external_delivery"] is False for message in data["integration"]["coordination_messages"])
    assert data["audit_id"] and len((tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()) == 1

    blocked_approval = client.post(f"/api/audits/{data['audit_id']}/review",
                                   json={"action": "APPROVED", "reviewer": "forged"},
                                   headers=csrf_headers(client))
    assert blocked_approval.status_code == 409
    rejected = client.post(f"/api/audits/{data['audit_id']}/review",
                           json={"action": "REJECTED", "reviewer": "forged", "reason": "Needs applicable evidence.",
                                 "accountable_authority": "Department of Telecommunications, Ministry of Communications"},
                           headers=csrf_headers(client))
    assert rejected.status_code == 200
    review_event = json.loads((tmp_path / "reviews.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert review_event["reviewer"] == "Test Name"
    assert review_event["reviewer"] != "forged"
    assert review_event["accountable_authority"] == "Department of Telecommunications, Ministry of Communications"
    from Backend.risk_engine import AIAnalysis, DecisionContext, DecisionImpact, EvidenceAssessment, EvidenceStatus, EvidenceQuality, RiskEngine
    sample = next(row for row in data["results"] if row["status"] == "COMPLETED")
    expected = RiskEngine().assess(
        DecisionContext(domain="Telecom/5G simulation", decision_impact=DecisionImpact.OPERATIONAL,
                        consequence_score=0),
        EvidenceAssessment(quality=EvidenceQuality.INSUFFICIENT, evidence_status=EvidenceStatus.INSUFFICIENT,
                           missing_evidence=["Applicability of retrieved guidance to these synthetic measurements has not been established.",
                                             "No independently verified operational requirement or incident-specific consequence assessment is available."]),
        AIAnalysis(confidence=0.0),
    )
    assert sample["governance_assessment"]["risk_score"] == expected.risk_score
    assert sample["governance_assessment"]["risk_level"] == expected.risk_level.value
    persisted_audit = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert persisted_audit["integration_record"]["full_run"]["run_id"] == data["run_id"]
    assert len(persisted_audit["integration_record"]["full_run"]["integration"]["coordination_messages"]) == 4
    from Backend.audit.recorder import generate_audit_id
    persisted_id = persisted_audit.pop("audit_id")
    assert persisted_id == generate_audit_id(persisted_audit)
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1

    run_id = data["run_id"]
    persisted = client.get(f"/api/5g/failure-combinations/{run_id}").json()
    assert persisted["run_id"] == run_id
    assert persisted["review"]["human_action"] == "REJECTED"
    assert client.get("/api/5g/failure-combinations").json()["count"] == 1
    invalid = client.post("/api/5g/failure-combinations", json={"failure_types": ["BOGUS"]},
                          headers=csrf_headers(client))
    assert invalid.status_code == 422
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1


def test_failed_simulator_cannot_be_persisted_as_success(monkeypatch, tmp_path: Path):
    import Backend.server as server
    import Backend.audit.recorder as recorder
    from Backend.telemetry_5g.simulator import NetworkSimulator5G

    store = tmp_path / "failed.jsonl"
    monkeypatch.setattr(server, "FAILURE_COMBINATION_STORE", store)
    monkeypatch.setattr(recorder, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(recorder, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(recorder, "REVIEW_EVENTS_FILE", tmp_path / "reviews.jsonl")
    def fail(*args, **kwargs):
        raise RuntimeError("simulator test failure")
    monkeypatch.setattr(NetworkSimulator5G, "run_simulation", fail)
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    response = client.post("/api/5g/failure-combinations", json={
        "failure_types": FAILURES[:1], "combination_depth": 1, "samples": 80,
    }, headers=csrf_headers(client))
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["results"][0]["status"] == "FAILED"
    assert response.json()["results"][0]["errors"] == ["RuntimeError: simulator test failure"]
    saved = json.loads(store.read_text(encoding="utf-8").splitlines()[0])
    assert saved["status"] == "FAILED"
