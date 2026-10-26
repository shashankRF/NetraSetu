from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import Backend.audit.recorder as recorder
from Backend import coordination_api
from Backend.audit.recorder import append_audit_record, create_audit_record
from Backend.server import app


def _client() -> TestClient:
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    return client


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api/auth/session").json()["csrf_token"]}


def test_coordination_messages_are_persisted_with_ist_and_speaker(monkeypatch, tmp_path):
    path = tmp_path / "coordination.jsonl"
    monkeypatch.setattr(coordination_api, "MESSAGES_FILE", path)
    monkeypatch.setattr(recorder, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(recorder, "REVIEW_EVENTS_FILE", tmp_path / "reviews.jsonl")
    monkeypatch.setattr(recorder, "AUDIT_DIR", tmp_path)
    client = _client()
    headers = _csrf(client)
    for speaker, body in (("NETRASETU", "Please confirm the reported road status."), ("AGENCY_DEMO", "Demonstration reply: field confirmation pending.")):
        response = client.post("/api/coordination/messages", headers=headers, json={
            "agency": "District Administration", "speaker": speaker, "body": body,
            "scenario_id": "HG-DISASTER-FLOOD-010",
        })
        assert response.status_code == 200, response.text
        assert response.json()["created_at_ist"].endswith("+05:30")
    loaded = client.get("/api/coordination/messages", params={"agency": "District Administration"})
    assert loaded.status_code == 200
    assert [m["speaker"] for m in loaded.json()["messages"]] == ["NETRASETU", "AGENCY_DEMO"]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    audit_rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(row["event_type"] == "COORDINATION_MESSAGE" for row in audit_rows)
    assert "not delivered" in loaded.json()["notice"].lower()


def test_audit_pending_contract_and_decision_update_expiry(monkeypatch, tmp_path):
    monkeypatch.setattr(recorder, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(recorder, "REVIEW_EVENTS_FILE", tmp_path / "reviews.jsonl")
    monkeypatch.setattr(recorder, "AUDIT_DIR", tmp_path)
    record = create_audit_record(question="Test decision trace", human_review_required=True,
                                 final_synthesis={"assessment": "Test analysis"},
                                 execution_status="COMPLETED")
    audit_id = append_audit_record(record)
    client = _client()
    pending = client.get(f"/api/audits/{audit_id}").json()
    assert (pending["scenario_decision_status"], pending["analysis_status"], pending["human_decision"],
            pending["required_action"], pending["audit_status"]) == (
                "Pending decision", "Completed", "Not recorded", "Awaiting authorized review", "Decision unresolved")
    headers = _csrf(client)
    first = client.post(f"/api/audits/{audit_id}/review", headers=headers, json={"action": "APPROVED"})
    assert first.status_code == 200, first.text
    assert first.json()["undo_expires_at"]
    update = client.post(f"/api/audits/{audit_id}/review", headers=headers,
                         json={"action": "REJECTED", "reason": "Escalate for senior review."})
    assert update.status_code == 200, update.text
    assert update.json()["human_action"] == "REJECTED"
    lines = (tmp_path / "reviews.jsonl").read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    event["undo_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    (tmp_path / "reviews.jsonl").write_text("\n".join(json.dumps(json.loads(line)) for line in lines[:-1] + [json.dumps(event)]) + "\n", encoding="utf-8")
    expired = client.post(f"/api/audits/{audit_id}/review", headers=headers,
                          json={"action": "APPROVED"})
    assert expired.status_code == 409
    assert "10-minute" in expired.json()["detail"]
