from fastapi.testclient import TestClient

from Backend.server import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "online"
    assert data["project"] == "HackGrid"


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
    )

    assert response.status_code == 404