from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from Backend import aftermath_api
from Backend.authentication import requires_session

app = FastAPI()
app.include_router(aftermath_api.router)
client = TestClient(app)


def _ledger(monkeypatch):
    records = []
    monkeypatch.setattr(aftermath_api, "load_audit_records", lambda: list(records))
    def append(record):
        records.append(dict(record))
        return record["audit_id"]
    monkeypatch.setattr(aftermath_api, "append_audit_record", append)
    monkeypatch.setattr(aftermath_api, "_actor", lambda request: "test-reviewer")
    return records


def test_scenarios_are_deterministic_synthetic_and_derive_metrics_from_records():
    listed = client.get("/api/aftermath/scenarios")
    assert listed.status_code == 200
    assert listed.json()["count"] == 3
    assert listed.json()["source_type"] == "SIMULATED"

    response = client.get("/api/aftermath/scenarios/AFTER-UTT-001")
    assert response.status_code == 200
    data = response.json()
    assert data["overview"]["estimated_population"] == sum(row["population_estimate"] for row in data["settlements"])
    assert data["overview"]["telecom_site_status"]["UNAVAILABLE"] >= 1
    assert data["overview"]["evidence_completeness"]["source_verified_count"] == 0
    assert all(asset["verification_status"] != "SOURCE_VERIFIED" for asset in data["assets"])
    assert all("priority_analysis" in action and action["priority_analysis"]["governance"]["human_review_required"] for action in data["actions"])
    assert data["actions"][0]["priority_analysis"]["factors"]["critical_service"]["weight"] == 0.3


def test_request_resolution_and_action_dependencies_are_validated_and_audited(monkeypatch):
    records = _ledger(monkeypatch)
    base = "/api/aftermath"
    # An action cannot skip mandatory human review.
    bad = client.post(base + "/actions/ACT-TWR-01-POWER/transition?scenario_id=AFTER-UTT-001",
                      json={"new_status": "APPROVED", "reason": "skip review"})
    assert bad.status_code == 409

    for state in ("UNDER_REVIEW", "APPROVED", "IN_PROGRESS"):
        response = client.post(base + "/actions/ACT-BH-01-ACCESS/transition?scenario_id=AFTER-UTT-001",
                               json={"new_status": state, "reason": "reviewed in test"})
        assert response.status_code == 200, response.text

    blocked = client.post(base + "/actions/ACT-BH-01-ACCESS/transition?scenario_id=AFTER-UTT-001",
                          json={"new_status": "COMPLETED", "reason": "dependency remains open"})
    assert blocked.status_code == 409

    resolved = client.post(base + "/requests/REQ-ROAD-01/transition?scenario_id=AFTER-UTT-001",
                           json={"new_status": "RESOLVED", "reason": "access confirmed in simulation"})
    assert resolved.status_code == 200, resolved.text
    done = client.post(base + "/actions/ACT-BH-01-ACCESS/transition?scenario_id=AFTER-UTT-001",
                       json={"new_status": "COMPLETED", "reason": "dependency resolved"})
    assert done.status_code == 200
    assert done.json()["real_world_operation"] is False
    assert len([row for row in records if row.get("event_type", "").startswith("AFTERMATH_")]) >= 5


def test_compare_timeline_and_protected_route_policy(monkeypatch):
    _ledger(monkeypatch)
    comparison = client.post("/api/aftermath/scenarios/AFTER-UTT-001/compare?comparison=AFTER-UTT-002")
    assert comparison.status_code == 200
    assert comparison.json()["provenance"] == "SYNTHETIC_FIXTURE_COMPARISON"
    timeline = client.get("/api/aftermath/scenarios/AFTER-UTT-003/timeline")
    assert timeline.status_code == 200
    assert timeline.json()["fixture_events_are_simulated"] is True
    assert requires_session("/api/aftermath/scenarios/AFTER-UTT-001", "GET") is True

def test_existing_multi_failure_engine_is_called_for_aftermath_and_persisted(monkeypatch):
    records = _ledger(monkeypatch)
    response = client.post("/api/aftermath/scenarios/AFTER-UTT-001/network-analysis")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["records_are_simulated"] is True
    assert data["real_network_measurements"] is False
    assert data["report"]["results"]
    assert any(row.get("event_type") == "AFTERMATH_NETWORK_ANALYSIS" for row in records)


def test_dharali_source_catalog_identifies_incident_and_four_evidence_bounded_targets():
    response = client.get("/api/aftermath/incident-sources/dharali-2025")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_date"] == "2025-08-05"
    assert data["analysis_window"] == {"start": "2025-08-01", "end": "2025-08-30"}
    assert len(data["assessment_targets"]) == 4
    assert data["assessment_targets"][3]["status"] == "NAMED_ON_SOURCE_MAP_CONDITION_NOT_RETRIEVED"
    assert all(source["available"] for source in data["sources"])


def test_dharali_search_returns_exact_source_locations_and_full_governance_parameters(monkeypatch):
    records = _ledger(monkeypatch)
    response = client.post("/api/aftermath/incident-analysis", json={
        "location": "Dharali, Uttarkashi, Uttarakhand",
        "incident_start": "2025-08-01",
        "incident_end": "2025-08-30",
        "incident_details": "Kheer Gad flash flood and debris flow at about 13:40 on 5 August 2025; assess damage and rehabilitation evidence.",
        "analysis_focus": "Identify documented damage, current unknowns, and verification steps before recovery planning.",
        "elevation_or_terrain_input": "GSI describes steep-gradient stream; no DEM supplied.",
        "facility_or_asset_ids": ["DHARALI-SETTLEMENT", "KHEER-GAD-RUNOUT", "BHAGIRATHI-CONFLUENCE", "DHARALI-MUKHBA-ACCESS"],
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["citations"]
    assert all(row.get("document_title") and row.get("page") and row.get("extracted_line_range") for row in data["citations"])
    assert data["governance"]["analysis_parameters"]["incident_details_user_supplied"].startswith("Kheer Gad")
    assert data["governance"]["analysis_parameters"]["facility_level_operational_status"] == "NOT_RETRIEVED"
    assert data["governance"]["decision_authorized"] is False
    assert len(records) == 1
    assert records[0]["event_type"] == "AFTERMATH_INCIDENT_ANALYSIS"
    assert records[0]["analysis_parameters"] == data["analysis_parameters"]


def test_dharali_analysis_rejects_out_of_coverage_dates_and_other_locations():
    base = {"incident_details": "Assess documented Kheer Gad event impacts and post-event recovery needs."}
    outside = client.post("/api/aftermath/incident-analysis", json={**base, "incident_start": "2025-07-31"})
    assert outside.status_code == 422
    other = client.post("/api/aftermath/incident-analysis", json={**base, "location": "Somewhere else"})
    assert other.status_code == 422


def test_frontend_incident_form_calls_registered_api_with_session_and_all_user_inputs():
    frontend = (Path(__file__).resolve().parents[2] / "Frontend" / "index.html").read_text(encoding="utf-8")
    assert "aftermathApi('/incident-analysis'" in frontend
    assert "incident_start:$('aftermath-incident-start').value" in frontend
    assert "incident_end:$('aftermath-incident-end').value" in frontend
    assert "incident_details:$('aftermath-incident-details').value" in frontend
    assert "analysis_focus:$('aftermath-analysis-focus').value" in frontend
    assert "elevation_or_terrain_input:$('aftermath-terrain-input').value" in frontend
    assert "options.credentials = 'include'" in frontend
