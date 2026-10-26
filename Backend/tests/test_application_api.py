from fastapi.testclient import TestClient

from Backend.server import app


client = TestClient(app)
login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
assert login_response.status_code == 200
client.headers.update({"X-CSRF-Token": login_response.json()["csrf_token"]})


def csrf_headers():
    return {"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]}


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "online"
    assert data["project"] == "NetraSetu"


def test_health():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["risk_engine"] == "available"
    assert data["scenario_count"] >= 7


def test_jurisdictions():
    response = client.get("/api/jurisdictions")

    assert response.status_code == 200

    data = response.json()

    names = {
        item["name"]
        for item in data["jurisdictions"]
    }

    assert "India" in names
    assert "European Union" in names


def test_scenarios():
    response = client.get("/api/scenarios")

    assert response.status_code == 200

    data = response.json()

    assert len(data["scenarios"]) >= 7


def test_scenario_detail():
    response = client.get(
        "/api/scenarios/HG-DEFENCE-001"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["scenario_id"] == "HG-DEFENCE-001"
    assert data["domain"] == "Defence"
    assert data["simulated"] is True


def test_unknown_scenario():
    response = client.get(
        "/api/scenarios/DOES-NOT-EXIST"
    )

    assert response.status_code == 404


def test_invalid_jurisdiction():
    response = client.get("/api/jurisdictions")

    assert response.status_code == 200

    # Endpoint itself is valid; validation is performed
    # on query/scenario execution.
    assert "jurisdictions" in response.json()


def test_query_rejects_invalid_jurisdiction():
    response = client.post(
        "/api/query",
        json={
            "question": "5G security",
            "jurisdiction": "United States",
        },
        headers=csrf_headers(),
    )

    assert response.status_code == 400

    assert "Unsupported jurisdiction profile" in response.json()["detail"]


def test_scenario_rejects_unknown_id():
    response = client.post(
        "/api/scenarios/run",
        json={
            "scenario_id": "DOES-NOT-EXIST",
            "jurisdiction": "India",
        },
        headers=csrf_headers(),
    )

    assert response.status_code == 404


def test_scenario_run_route_returns_pipeline_response(monkeypatch):
    import time

    def fake_run_pipeline(question, **kwargs):
        time.sleep(0.05)
        return {"question": question, "audit_id": "AUD-regression", "final_synthesis": "verified test response"}

    monkeypatch.setattr("Backend.server.run_pipeline", fake_run_pipeline)
    response = client.post(
        "/api/scenarios/run",
        json={"scenario_id": "HG-5G-003", "step_id": "T1", "jurisdiction": "India"},
        headers={"X-Request-ID": "RUN-testtrace-01"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario"]["scenario_id"] == "HG-5G-003"
    assert payload["trace_id"] == "RUN-testtrace-01"
    assert payload["scenario_step"]["step_id"] == "T1"
    assert payload["pipeline_result"]["performance"]["scenario_validation_ms"] >= 0
    assert payload["pipeline_result"]["performance"]["scenario_route_total_ms"] >= 50
    assert payload["pipeline_result"]["audit_id"] == "AUD-regression"
    assert payload["pipeline_result"]["final_synthesis"] == "verified test response"


def test_scenario_pipeline_exception_is_reported_and_audited(monkeypatch):
    audit_rows = []
    monkeypatch.setattr("Backend.server.run_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("classification provider unavailable")))
    monkeypatch.setattr("Backend.server.append_audit_record", audit_rows.append)

    response = client.post(
        "/api/scenarios/run",
        json={"scenario_id": "HG-5G-003", "step_id": "T1", "jurisdiction": "India"},
        headers={"X-Request-ID": "RUN-error-trace-01"},
    )

    assert response.status_code == 500
    assert "classification provider unavailable" in response.json()["detail"]
    assert audit_rows[0]["execution_status"] == "FAILED"
    assert audit_rows[0]["execution_id"] == "RUN-error-trace-01"
