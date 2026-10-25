"""Persisted local coordination conversations; no external agency delivery."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .authentication import request_session
from .audit.recorder import append_audit_record, create_audit_record

router = APIRouter(prefix="/api/coordination", tags=["Inter-Agency Coordination"])
MESSAGES_FILE = Path(__file__).resolve().parent / "audit" / "records" / "coordination_messages.jsonl"
AGENCIES = {"District Administration", "State Government — SDRF Uttarakhand", "Central Government — NDRF", "Telecom Operator"}


class CoordinationMessage(BaseModel):
    agency: str
    body: str = Field(min_length=1, max_length=600)
    speaker: str = "NETRASETU"
    scenario_id: Optional[str] = None
    evidence_reference: Optional[str] = Field(default=None, max_length=300)


def _load() -> list[dict]:
    if not MESSAGES_FILE.exists():
        return []
    with MESSAGES_FILE.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


@router.get("/messages")
def list_messages(agency: str = Query(...)):
    if agency not in AGENCIES:
        raise HTTPException(422, "Unknown coordination participant.")
    rows = [row for row in _load() if row["agency"] == agency]
    return {"messages": rows, "timezone": "Asia/Kolkata", "notice": "Local demonstration conversation; messages are not delivered to an external agency."}


@router.post("/messages")
def add_message(payload: CoordinationMessage, request: Request):
    if payload.agency not in AGENCIES:
        raise HTTPException(422, "Unknown coordination participant.")
    if payload.speaker not in {"NETRASETU", "AGENCY_DEMO"}:
        raise HTTPException(422, "Speaker must be NETRASETU or AGENCY_DEMO.")
    _, session = request_session(request)
    if not session:
        raise HTTPException(401, "Sign in to add a coordination message.")
    created = datetime.now(timezone.utc)
    actor = str(session.get("display_name") or session.get("username") or "Signed-in reviewer")
    sender = actor if payload.speaker == "NETRASETU" else payload.agency + " (demo participant)"
    row = {
        "message_id": "MSG-" + uuid.uuid4().hex[:16], "agency": payload.agency,
        "scenario_id": payload.scenario_id, "speaker": payload.speaker, "sender": sender,
        "created_at_utc": created.isoformat(), "created_at_ist": created.astimezone(ZoneInfo("Asia/Kolkata")).isoformat(),
        "body": payload.body.strip(), "evidence_reference": payload.evidence_reference,
        "provenance": "LOCAL_DEMONSTRATION" if payload.speaker == "AGENCY_DEMO" else "AUTHENTICATED_USER",
        "actor": actor,
    }
    audit_record = create_audit_record(
        question=f"Coordination message · {payload.agency} · {sender}",
        event_type="COORDINATION_MESSAGE", execution_status="RECORDED",
        scenario_id=payload.scenario_id, provenance=row["provenance"],
        notes=["Persisted coordination conversation message; no external delivery."],
        domain="Inter-Agency Coordination", jurisdiction="India",
    )
    audit_record["coordination_message"] = row
    append_audit_record(audit_record)
    row["audit_id"] = audit_record["audit_id"]
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MESSAGES_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
