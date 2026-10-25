"""
NetraSetu Architecture Decisions & 5G Performance Test Suite.

Verifies:
1. 5G telemetry & simulation is 100% deterministic (NO LLM in loop).
2. Rule-based SLO evaluation (URLLC, eMBB, mMTC) and deterministic recovery triggers.
3. Anomaly detection component with false alarm tracking.
4. Data provenance correctly distinguishes SIMULATION from real testbed.
5. Qwen2.5-0.5B-Instruct adapter configuration, verbatim source validation, and limitation reporting.
6. Change-Impact dependency tracking and re-evaluation planning without false completion claims.
7. Endpoints /api/5g/profiles, /api/5g/test, /api/change_impact/revisions, /api/change_impact/plan.
"""

import pytest
from fastapi.testclient import TestClient
from Backend.server import app
from Backend.telemetry_5g.models import (
    NetworkProfileType,
    ImpairmentType,
    SLO_PROFILES,
    HealthStatus,
)
from Backend.telemetry_5g.slo_evaluator import SLOEvaluator
from Backend.telemetry_5g.anomaly_detector import NetworkAnomalyDetector
from Backend.telemetry_5g.simulator import NetworkSimulator5G
from Backend.telemetry_5g.engine import get_5g_telemetry_engine
from Backend.evidence_engine.qwen_analyzer import QwenEvidenceAnalyzer
from Backend.change_impact.engine import get_change_impact_engine


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.get("/api/auth/session").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def test_5g_slo_evaluator_deterministic_nominal():
    evaluator = SLOEvaluator(NetworkProfileType.URLLC)
    sim = NetworkSimulator5G(seed=42)
    # Generate nominal trace without impairments
    samples = sim.generate_trace(profile=NetworkProfileType.URLLC, impairments=[], num_samples=10)
    for s in samples:
        status, vios = evaluator.evaluate_sample(s)
        assert status == HealthStatus.HEALTHY
        assert len(vios) == 0


def test_5g_slo_evaluator_deterministic_violations_and_recovery():
    evaluator = SLOEvaluator(NetworkProfileType.URLLC)
    sim = NetworkSimulator5G(seed=42)
    # Inject latency spike and packet loss
    samples = sim.generate_trace(
        profile=NetworkProfileType.URLLC,
        impairments=[ImpairmentType.LATENCY_SPIKE, ImpairmentType.PACKET_LOSS],
        num_samples=70,
    )

    impaired_sample = samples[45]  # Inside impaired window
    status, vios = evaluator.evaluate_sample(impaired_sample)
    assert status in [HealthStatus.DEGRADED, HealthStatus.VIOLATING]
    assert len(vios) > 0

    # Deterministic recovery actions (No LLM in decision loop)
    actions = evaluator.determine_deterministic_recovery(samples, vios)
    assert len(actions) >= 2
    action_types = [a.action_type for a in actions]
    assert "DUAL_CONNECTIVITY_PACKET_DUPLICATION" in action_types
    assert "RLC_AM_RETRANSMISSION_BOOST" in action_types
    for a in actions:
        assert a.execution_status == "DETERMINISTIC_TRIGGERED"
        assert a.expected_recovery_ms > 0


def test_5g_anomaly_detector_component():
    detector = NetworkAnomalyDetector(z_threshold=2.5, min_history_size=5)
    sim = NetworkSimulator5G(seed=101)
    samples = sim.generate_trace(
        profile=NetworkProfileType.URLLC,
        impairments=[ImpairmentType.LATENCY_SPIKE],
        num_samples=50,
    )

    detected_anomalies = []
    for i, s in enumerate(samples):
        is_impaired = 30 <= i <= 48
        res = detector.detect_sample(s, ground_truth_impaired=is_impaired)
        for r in res:
            if r.is_anomaly:
                detected_anomalies.append(r)

    # Must detect anomalies during the latency spike window
    assert len(detected_anomalies) > 0
    first_anom = detected_anomalies[0]
    assert first_anom.metric_name in ["latency_ms", "packet_loss_rate"]
    assert first_anom.anomaly_score > 0.0


def test_5g_simulator_provenance_and_metrics():
    sim = NetworkSimulator5G(seed=55)
    res = sim.run_simulation(
        profile=NetworkProfileType.URLLC,
        impairments=[ImpairmentType.LATENCY_SPIKE, ImpairmentType.CONGESTION],
        num_samples=100,
    )

    assert res.total_samples == 100
    assert res.delivery_success_rate > 0.0
    assert res.tail_latency_p95_ms >= res.average_latency_ms
    assert res.tail_latency_p99_ms >= res.tail_latency_p95_ms
    assert res.resource_overhead_pct > 0.0
    assert res.slo_compliance_status in ["DEGRADED", "VIOLATED"]

    # Provenance requirements
    assert res.provenance["source"] == "SIMULATION"
    assert res.provenance["is_simulated"] is True
    assert res.provenance["real_testbed"] is False
    assert res.provenance["llm_in_decision_loop"] is False


def test_network_agent_removes_llm():
    from rag.network_agent import network_agent
    result = network_agent("Assess 5G network slicing URLLC latency spikes and buffer congestion.")
    assert "Deterministic Engine" in result
    assert "Evaluation Path: Strictly Deterministic (LLM-Free)" in result
    assert "SIMULATION" in result
    assert "Tail Latency" in result
    assert "DUAL_CONNECTIVITY_PACKET_DUPLICATION" in result


def test_qwen_analyzer_source_grounding_validation():
    analyzer = QwenEvidenceAnalyzer()
    source_records = [
        {
            "evidence_id": "EV-001",
            "text": "Section 70B mandates incident reporting within six hours to CERT-In.",
            "title": "CERT-In Directions 2022",
        }
    ]

    # Valid grounded reasoning
    is_grounded, warnings = analyzer.validate_grounding_against_source(
        "Section 70B incident reporting within six hours to CERT-In",
        source_records,
    )
    assert is_grounded is True
    assert len(warnings) == 0

    # Fabricated / ungrounded hallucination
    is_grounded_bad, warnings_bad = analyzer.validate_grounding_against_source(
        "Quantum satellites orbiting Jupiter require blockchain smart contracts for holographic telepathy.",
        source_records,
    )
    assert is_grounded_bad is False
    assert len(warnings_bad) > 0


def test_qwen_analyzer_reports_explicit_limitation():
    analyzer = QwenEvidenceAnalyzer(model_name="non_existent/model_for_limitation_test")
    res = analyzer.classify_with_qwen("Sample claim", [{"evidence_id": "EV-001", "text": "Sample text"}])
    assert res["status"] in ["MODEL_UNAVAILABLE", "MODEL_LIMITATION"]
    assert "limitation" in res or "error" in res
    # Ensure it never fabricated classifications
    assert res["classifications"] == []


def test_change_impact_engine_dependency_planning():
    engine = get_change_impact_engine()
    revisions = engine.get_tracked_revisions()
    assert len(revisions) >= 3
    rev_ids = [r["revision_id"] for r in revisions]
    assert "REV-CERTIN-70B-2022" in rev_ids
    assert "REV-TELECOM-2023" in rev_ids
    assert "REV-DPDP-2023" in rev_ids

    plan = engine.build_impact_plan("REV-CERTIN-70B-2022")
    assert plan.revision_id == "REV-CERTIN-70B-2022"
    assert "HG-CERTIN-008" in plan.affected_scenarios
    assert len(plan.affected_evidence_chunks) > 0
    assert plan.implementation_status == "PLANNED_PHASE_2"
    assert plan.testing_verified is False  # Must not claim tested until implemented


def test_api_5g_and_change_impact_endpoints():
    client = TestClient(app)
    auth = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert auth.status_code == 200

    # 1. GET /api/5g/profiles
    r_prof = client.get("/api/5g/profiles")
    assert r_prof.status_code == 200
    profiles = r_prof.json()
    assert "URLLC" in profiles
    assert "eMBB" in profiles
    assert "mMTC" in profiles
    assert profiles["URLLC"]["max_latency_ms"] == 5.0
    assert "not an operator restoration event" in profiles["URLLC"]["recovery_metric_semantics"]

    # 2. POST /api/5g/test
    r_test = client.post("/api/5g/test", json={
        "profile": "URLLC",
        "impairments": ["LATENCY_SPIKE", "PACKET_LOSS"],
        "num_samples": 60,
    }, headers=csrf_headers(client))
    assert r_test.status_code == 200
    res_data = r_test.json()
    assert res_data["profile"] == "URLLC"
    assert "delivery_success_rate" in res_data
    assert "tail_latency_p95_ms" in res_data
    assert res_data["simulated_post_impairment_interval_ms"] == res_data["recovery_time_ms"]
    assert res_data["recovery_time_semantics"]["actual_restoration"] is False
    assert res_data["provenance"]["is_simulated"] is True
    assert res_data["provenance"]["llm_in_decision_loop"] is False

    # 3. GET /api/change_impact/revisions
    r_rev = client.get("/api/change_impact/revisions")
    assert r_rev.status_code == 200
    assert len(r_rev.json()) >= 3

    # 4. POST /api/change_impact/plan
    r_plan = client.post("/api/change_impact/plan", json={"revision_id": "REV-TELECOM-2023"},
                         headers=csrf_headers(client))
    assert r_plan.status_code == 200
    plan_data = r_plan.json()
    assert plan_data["plan_id"] == "PLAN-REV-TELECOM-2023"
    assert plan_data["implementation_status"] == "PLANNED_PHASE_2"
    assert plan_data["testing_verified"] is False
