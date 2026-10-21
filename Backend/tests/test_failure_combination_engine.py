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
    store = tmp_path / "runs.jsonl"
    monkeypatch.setattr(server, "FAILURE_COMBINATION_STORE", store)
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    catalog = client.get("/api/5g/failure-combinations/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["scope"].startswith("Controlled software simulation")

    response = client.post("/api/5g/failure-combinations", json={
        "profile": "URLLC", "failure_types": FAILURES[:2], "combination_depth": 2,
        "max_scenarios": 4, "samples": 80, "seed": 22,
        "thresholds": {"max_tail_latency_p95_ms": 4.0},
    }, headers={"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["results"][-1]["policy_evaluation"]["status"] in {"SATISFIED", "THRESHOLD_EXCEEDED"}
    assert data["evidence_assessment"]["status"] == "EVIDENCE NOT RETRIEVED"
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1

    run_id = data["run_id"]
    assert client.get(f"/api/5g/failure-combinations/{run_id}").json()["run_id"] == run_id
    assert client.get("/api/5g/failure-combinations").json()["count"] == 1
    invalid = client.post("/api/5g/failure-combinations", json={"failure_types": ["BOGUS"]}, headers={"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]})
    assert invalid.status_code == 422
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1


def test_failed_simulator_cannot_be_persisted_as_success(monkeypatch, tmp_path: Path):
    import Backend.server as server
    from Backend.telemetry_5g.simulator import NetworkSimulator5G

    store = tmp_path / "failed.jsonl"
    monkeypatch.setattr(server, "FAILURE_COMBINATION_STORE", store)
    def fail(*args, **kwargs):
        raise RuntimeError("simulator test failure")
    monkeypatch.setattr(NetworkSimulator5G, "run_simulation", fail)
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    response = client.post("/api/5g/failure-combinations", json={
        "failure_types": FAILURES[:1], "combination_depth": 1, "samples": 80,
    }, headers={"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]})
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["results"][0]["status"] == "FAILED"
    assert response.json()["results"][0]["errors"] == ["RuntimeError: simulator test failure"]
    saved = json.loads(store.read_text(encoding="utf-8").splitlines()[0])
    assert saved["status"] == "FAILED"
