from __future__ import annotations

from fastapi.testclient import TestClient

from Backend.server import app
from Backend.ecr5g import api as ecr_api
from Backend.ecr5g.controllers import select_packet
from Backend.ecr5g.models import ControllerStrategy, ECACPolicyLimits, NetworkChange
from Backend.ecr5g.scenarios import get_scenario, list_scenarios
from Backend.ecr5g.simulator import run_simulation


def csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]}


def authenticated_client() -> TestClient:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return client


def test_ecr5g_routes_are_registered_and_protected():
    client = TestClient(app)
    assert client.get("/api/ecr5g/health").status_code == 401
    assert client.get("/api/ecr5g/scenarios").status_code == 401
    assert client.post("/api/ecr5g/simulations/run", json={"scenario_id": "HG-ECAC-001"}).status_code == 401
    client = authenticated_client()
    assert client.get("/api/ecr5g/health").json()["simulated_only"] is True
    scenarios = client.get("/api/ecr5g/scenarios").json()
    assert scenarios["count"] == 8
    assert {item["scenario_id"] for item in scenarios["scenarios"]} == {
        f"HG-ECAC-{number:03d}" for number in range(1, 9)
    }


def test_ecr5g_run_request_persists_and_returns_comparable_report(monkeypatch):
    records = []
    monkeypatch.setattr(ecr_api, "append_audit_record", lambda record: records.append(record) or record["audit_id"])
    monkeypatch.setattr(ecr_api, "load_audit_records", lambda: records)
    client = authenticated_client()
    response = client.post("/api/ecr5g/simulations/run", json={
        "scenario_id": "HG-ECAC-001", "seed": 991,
    }, headers=csrf(client))
    assert response.status_code == 200, response.text
    body = response.json()
    report = body["report"]
    assert body["status"] == "COMPLETED"
    assert report["seed"] == 991
    assert report["configuration"]["scenario_id"] == "HG-ECAC-001"
    assert report["simulation_assumptions"]["event_time_only_no_sleep"] is True
    assert [item["strategy"] for item in report["strategy_results"]] == [
        "FIFO_BASELINE", "STATIC_QOS_BASELINE", "ECAC_CONTROLLER"
    ]
    assert len({item["trace_sha256"] for item in report["strategy_results"]}) == 1
    for result in report["strategy_results"]:
        assert result["invariants"]["real_actions_authorized"] is False
        assert result["invariants"]["stale_evidence_accepted"] == 0
        assert result["invariants"]["conflicting_evidence_accepted"] == 0
    fetched = client.get(f"/api/ecr5g/simulations/{body['run_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["report"]["run_id"] == body["run_id"]
    report_response = client.get(f"/api/ecr5g/simulations/{body['run_id']}/report")
    assert report_response.status_code == 200
    assert report_response.json()["provenance"]["real_5g"] is False
    assert records[0]["event_type"] == "ECR5G_SIMULATION"


def test_ecr5g_requires_csrf_for_run_and_validates_request(monkeypatch):
    monkeypatch.setattr(ecr_api, "append_audit_record", lambda record: record["audit_id"])
    client = authenticated_client()
    missing_csrf = client.post("/api/ecr5g/simulations/run", json={"scenario_id": "HG-ECAC-001"})
    assert missing_csrf.status_code == 403
    invalid_scenario = client.post("/api/ecr5g/simulations/run", json={"scenario_id": "NOT-A-SCENARIO"}, headers=csrf(client))
    assert invalid_scenario.status_code == 404
    duplicate_strategy = client.post("/api/ecr5g/simulations/run", json={
        "scenario_id": "HG-ECAC-001", "strategies": ["FIFO_BASELINE", "FIFO_BASELINE"]
    }, headers=csrf(client))
    assert duplicate_strategy.status_code == 422


def test_all_scenario_models_validate_and_have_safety_gates():
    client = authenticated_client()
    response = client.get("/api/ecr5g/scenarios", headers=csrf(client))
    assert response.status_code == 200
    for scenario in response.json()["scenarios"]:
        assert scenario["expected_safety_invariants"]
        assert all(action["human_approval_required"] for action in scenario["decision_requirements"])


def test_fixed_seed_repeats_and_three_controllers_use_identical_trace():
    scenario = get_scenario("HG-ECAC-002")
    assert scenario is not None
    results = [run_simulation(scenario, strategy, seed=6060)
               for strategy in ControllerStrategy]
    assert len({item["trace_sha256"] for item in results}) == 1
    first = run_simulation(scenario, ControllerStrategy.ECAC_CONTROLLER, seed=6060)
    second = run_simulation(scenario, ControllerStrategy.ECAC_CONTROLLER, seed=6060)
    assert first["packet_outcomes"] == second["packet_outcomes"]
    for key in ("message_loss_rate", "deadline_success_rate", "bytes_transmitted", "bottleneck_utilization_rate"):
        assert first[key] == second[key]


def test_capacity_serialization_processing_and_queue_metrics_are_separate():
    scenario = get_scenario("HG-ECAC-001")
    assert scenario is not None
    result = run_simulation(scenario, ControllerStrategy.FIFO_BASELINE)
    segments = sorted((segment["start_ms"], segment["end_ms"], segment["bits"], segment["capacity_mbps"])
                      for outcome in result["packet_outcomes"] for segment in outcome["serialization_segments"])
    for index, (start, end, bits, capacity_mbps) in enumerate(segments):
        assert end >= start
        assert bits <= capacity_mbps * 1000 * (end - start) + 1e-5
        if index:
            assert start >= segments[index - 1][1] - 1e-6
    for outcome in result["packet_outcomes"]:
        if outcome["delivered"]:
            assert outcome["network_delivery_latency_ms"] == (
                outcome["serialization_complete_ms"] - outcome["transmission_start_ms"]
                + outcome["propagation_delay_ms"] + outcome["processing_delay_ms"]
            )
    assert result["queueing_delay_ms"]["maximum"] >= result["queueing_delay_ms"]["mean"]
    assert result["controller_computation_ms"] >= 0
    assert result["evidence_validation_computation_ms"] >= 0
    assert result["api_request_latency_ms"] is None


def test_serialization_pauses_during_mid_packet_disconnect_and_resumes():
    scenario = get_scenario("HG-ECAC-001")
    assert scenario is not None
    changed = scenario.model_copy(update={"network_changes": [
        NetworkChange(start_offset_ms=1, end_offset_ms=2, link_available=False, bottleneck_capacity_mbps=0),
        NetworkChange(start_offset_ms=2, end_offset_ms=scenario.simulation_duration_ms,
                      link_available=True, bottleneck_capacity_mbps=8, processing_delay_ms=9),
    ]})
    result = run_simulation(changed, ControllerStrategy.FIFO_BASELINE)
    first = min(result["packet_outcomes"], key=lambda item: item["sequence"])
    assert len(first["serialization_segments"]) >= 2
    assert first["serialization_segments"][0]["end_ms"] <= 1.000001
    assert first["serialization_segments"][1]["start_ms"] >= 2
    assert first["processing_delay_ms"] == 9


def test_missing_stale_conflicting_and_undelivered_evidence_are_blocked():
    missing = run_simulation(get_scenario("HG-ECAC-005"), ControllerStrategy.ECAC_CONTROLLER)
    missing_route = next(item for item in missing["evidence_completeness"]["requirement_results"]
                         if item["requirement_id"] == "REQ-ROUTE")
    assert not missing_route["complete"]
    assert "MANDATORY_EVIDENCE_NOT_PROVIDED" in missing_route["reason_codes"]
    assert missing["schedule_status"] == "INFEASIBLE"
    assert missing["infeasible_schedule_count"] == 1

    stale_conflict = run_simulation(get_scenario("HG-ECAC-004"), ControllerStrategy.ECAC_CONTROLLER)
    assert stale_conflict["stale_evidence_objects_rejected"] >= 1
    assert stale_conflict["unresolved_conflict_objects"] >= 1
    assert stale_conflict["invariants"]["stale_evidence_accepted"] == 0
    assert stale_conflict["invariants"]["conflicting_evidence_accepted"] == 0

    normal = get_scenario("HG-ECAC-001")
    disconnected = normal.model_copy(update={
        "initial_network_state": normal.initial_network_state.model_copy(update={
            "link_available": False, "bottleneck_capacity_mbps": 0,
        }),
        "network_changes": [],
    })
    no_delivery = run_simulation(disconnected, ControllerStrategy.ECAC_CONTROLLER)
    assert no_delivery["delivered_messages"] == 0
    assert no_delivery["evidence_completeness"]["completeness_rate"] == 0
    assert no_delivery["invariants"]["undelivered_evidence_accepted"] == 0


def test_configured_conflict_resolution_reference_is_required_and_can_resolve():
    scenario = get_scenario("HG-ECAC-004")
    assert scenario is not None
    evidence = [item.model_copy(update={"conflict_resolution_reference": "RESOLUTION-REVIEW-17"})
                if item.evidence_id == "EVID-ROUTE-NEW" else item for item in scenario.evidence_objects]
    resolved_scenario = scenario.model_copy(update={"evidence_objects": evidence})
    result = run_simulation(resolved_scenario, ControllerStrategy.ECAC_CONTROLLER)
    route = next(item for item in result["evidence_completeness"]["requirement_results"]
                 if item["requirement_id"] == "REQ-ROUTE")
    assert route["complete"]


def test_deadline_and_percentiles_account_for_undelivered_messages():
    scenario = get_scenario("HG-ECAC-003")
    assert scenario is not None
    result = run_simulation(scenario, ControllerStrategy.STATIC_QOS_BASELINE)
    assert result["failed_deadlines"]
    assert result["delivery_latency_ms"]["p95"] >= result["delivery_latency_ms"]["p50"]
    assert result["delivery_latency_ms"]["maximum"] >= result["delivery_latency_ms"]["p99"]
    assert result["delivery_latency_ms"]["mean_including_undelivered_penalty"] >= (
        result["delivery_latency_ms"]["delivered_only_mean"] or 0
    )
    assert result["safety_invariant_violations"] == 0


def test_disconnection_waits_for_recovery_and_failed_run_has_actionable_reasons():
    scenario = get_scenario("HG-ECAC-006")
    assert scenario is not None
    result = run_simulation(scenario, ControllerStrategy.ECAC_CONTROLLER)
    first = min(result["packet_outcomes"], key=lambda item: item["sequence"])
    assert first["transmission_start_ms"] >= 1000
    assert result["schedule_status"] in {"INFEASIBLE", "FEASIBLE_FOR_HUMAN_REVIEW"}
    assert result["infeasible_reasons"] == [] or all(
        item.get("reason") or item.get("reason_code") or item.get("reason_codes")
        for item in result["infeasible_reasons"]
    )


def test_ecac_mandatory_evidence_preempts_optional_with_a_configured_burst_limit():
    scenario = get_scenario("HG-ECAC-001")
    assert scenario is not None
    ready = [
        {"sequence": 1, "flow_id": "FLOW-BACKGROUND", "arrival_ms": 0, "payload_bytes": 1024},
        {"sequence": 2, "flow_id": "FLOW-INCIDENT", "arrival_ms": 0, "payload_bytes": 2048},
    ]
    selected, promoted, mandatory = select_packet(ready, ControllerStrategy.ECAC_CONTROLLER,
                                                   scenario, 100)
    assert selected["flow_id"] == "FLOW-INCIDENT"
    assert mandatory and promoted
    capped = scenario.model_copy(update={"ecac_policy_limits": ECACPolicyLimits(
        max_consecutive_mandatory_messages=1,
    )})
    selected_after_burst, _, mandatory_after_burst = select_packet(
        ready, ControllerStrategy.ECAC_CONTROLLER, capped, 100, consecutive_mandatory=1,
    )
    assert selected_after_burst["flow_id"] == "FLOW-BACKGROUND"
    assert not mandatory_after_burst


def test_fifo_and_static_qos_have_distinct_documented_fixed_ordering():
    scenario = get_scenario("HG-ECAC-001")
    assert scenario is not None
    ready = [
        {"sequence": 1, "flow_id": "FLOW-BACKGROUND", "arrival_ms": 0, "payload_bytes": 1024},
        {"sequence": 2, "flow_id": "FLOW-ROUTE", "arrival_ms": 100, "payload_bytes": 2048},
    ]
    fifo, _, _ = select_packet(ready, ControllerStrategy.FIFO_BASELINE, scenario, 150)
    static, _, _ = select_packet(ready, ControllerStrategy.STATIC_QOS_BASELINE, scenario, 150)
    assert fifo["flow_id"] == "FLOW-BACKGROUND"
    assert static["flow_id"] == "FLOW-ROUTE"


def test_all_eight_scenarios_execute_as_calculated_results():
    assert len(list_scenarios()) == 8
    for scenario in list_scenarios():
        results = [run_simulation(scenario, strategy) for strategy in ControllerStrategy]
        assert len({item["trace_sha256"] for item in results}) == 1
        assert all(item["generated_messages"] > 0 for item in results)
        assert all(item["safety_invariant_violations"] == 0 for item in results)
        assert all(item["simulation_execution_wall_clock_ms"] >= 0 for item in results)
