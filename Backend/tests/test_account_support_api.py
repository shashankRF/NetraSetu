import json

import pytest
from fastapi.testclient import TestClient

from Backend.server import app
import Backend.account_api as account_api
import Backend.authentication as authentication


def csrf_headers(client):
    token = client.get("/api/auth/session").json()["csrf_token"]
    return {"X-CSRF-Token": token}


@pytest.fixture(autouse=True)
def local_demo_auth(monkeypatch):
    monkeypatch.setenv("NETRASETU_ENV", "development")
    monkeypatch.delenv("NETRASETU_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("NETRASETU_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("NETRASETU_SUPPORT_EMAIL", raising=False)
    monkeypatch.delenv("NETRASETU_SMTP_HOST", raising=False)
    monkeypatch.delenv("NETRASETU_SMTP_FROM", raising=False)


def test_invalid_login_warning_retry_session_and_logout():
    client = TestClient(app)
    assert client.get("/api/audits").status_code == 401
    for index in range(4):
        response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401
        assert response.json()["message"] == "Username or password is incorrect."
        assert response.json()["administrator_warning"] is (index == 3)
    # Attempts continue after the warning; there is no permanent lockout.
    assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    success = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert success.status_code == 200
    assert success.json()["demo_mode"] is True
    assert client.cookies.get("netrasetu_session")
    assert client.get("/api/audits").status_code == 200
    assert client.get("/api/auth/session").json()["authenticated"] is True
    assert client.post("/api/auth/logout", headers=csrf_headers(client)).status_code == 200
    assert client.get("/api/auth/session").json()["authenticated"] is False
    assert client.get("/api/audits").status_code == 401


def test_login_configuration_fails_closed_outside_demo(monkeypatch):
    monkeypatch.setenv("NETRASETU_ENV", "production")
    monkeypatch.delenv("NETRASETU_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("NETRASETU_ADMIN_PASSWORD", raising=False)
    response = TestClient(app, base_url="https://testserver").post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 503


def test_profile_name_is_persisted_separately_from_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(authentication, "PROFILE_PATH", tmp_path / "profiles.json")
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    response = client.patch("/api/auth/profile", json={"display_name": "  Shashank Kotnala  "}, headers=csrf_headers(client))
    assert response.status_code == 200
    assert response.json()["display_name"] == "Shashank Kotnala"
    assert response.json()["persistence"] == "local server profile file"
    session = client.get("/api/auth/session").json()
    assert session["username"] == "admin"
    assert session["display_name"] == "Shashank Kotnala"
    assert json.loads((tmp_path / "profiles.json").read_text(encoding="utf-8"))["admin"] == "Shashank Kotnala"
    assert client.patch("/api/auth/profile", json={"display_name": "x"}, headers=csrf_headers(client)).status_code == 422


def test_troubleshooting_report_is_saved_without_claiming_email_delivery(monkeypatch, tmp_path):
    monkeypatch.setattr(account_api, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(account_api, "REPORT_FILE", tmp_path / "reports" / "reports.jsonl")
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    body = {
        "category": "Scenario execution",
        "title": "Scenario run failed",
        "description": "The selected demo scenario did not return a result.",
        "module": "Dashboard Overview",
        "error_message": "Authorization: Bearer supersecret",
    }
    response = client.post("/api/troubleshooting/reports", json=body, headers=csrf_headers(client))
    assert response.status_code == 200
    data = response.json()
    assert data["delivery_status"] == "SAVED_EMAIL_NOT_CONFIGURED"
    assert "saved locally" in data["message"].lower()
    record = json.loads((tmp_path / "reports" / "reports.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert record["report_id"] == data["report_id"]
    assert "supersecret" not in record["error_message"]
    retry = client.post(f"/api/troubleshooting/reports/{data['report_id']}/retry", headers=csrf_headers(client))
    assert retry.status_code == 200
    assert retry.json()["delivery_status"] == "SAVED_EMAIL_NOT_CONFIGURED"


def test_report_requires_auth_and_rejects_unsafe_attachment(monkeypatch, tmp_path):
    monkeypatch.setattr(account_api, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(account_api, "REPORT_FILE", tmp_path / "reports" / "reports.jsonl")
    client = TestClient(app)
    body = {"category": "Other", "title": "Unsafe attachment", "description": "A sufficiently detailed issue report.", "module": "Other"}
    assert client.post("/api/troubleshooting/reports", json=body).status_code == 401
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    body["attachment"] = {"filename": "payload.exe", "content_type": "application/octet-stream", "content_base64": "TVqQAAMAAAAEAAAA"}
    response = client.post("/api/troubleshooting/reports", json=body, headers=csrf_headers(client))
    assert response.status_code == 415
    assert not (tmp_path / "reports" / "reports.jsonl").exists()


def test_dashboard_data_requires_session_and_state_changes_require_csrf():
    client = TestClient(app)
    assert client.get("/api/scenarios").status_code == 401
    assert client.get("/api/documents/info").status_code == 401
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    assert login.cookies.get("netrasetu_session")
    assert login.json()["expires_in"] == 30 * 60
    assert client.get("/api/scenarios").status_code == 200
    assert client.patch("/api/auth/profile", json={"display_name": "Test Name"}).status_code == 403
    assert client.patch("/api/auth/profile", json={"display_name": "Test Name"}, headers=csrf_headers(client)).status_code == 200
