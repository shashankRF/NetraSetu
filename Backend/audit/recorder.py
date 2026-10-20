from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


AUDIT_DIR = (
    Path(__file__).resolve().parent
    / "records"
)

AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
REVIEW_EVENTS_FILE = AUDIT_DIR / "review_events.jsonl"

PIPELINE_VERSION = "hackgrid-evidence-pipeline-v1"


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def generate_audit_id(
    record: Dict[str, Any],
) -> str:
    canonical = _canonical_json(record)
    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return f"AUD-{digest[:24]}"


def create_audit_record(
    *,
    question: str,
    model: str = "openai/gpt-oss-120b",
    retrieved_evidence: List[Dict[str, Any]] | None = None,
    evidence_classification: Dict[str, Any] | None = None,
    evidence_assessment: Dict[str, Any] | None = None,
    absence_verification: List[Dict[str, Any]] | None = None,
    gap_analysis: Dict[str, Any] | None = None,
    risk_assessment: Dict[str, Any] | None = None,
    final_synthesis: Dict[str, Any] | None = None,
    claim_evidence_mappings: List[Dict[str, Any]] | None = None,
    human_review_required: bool = False,
    human_reviewer: str = "",
    human_action: str = "",
    reviewer_modifications: str = "",
    final_decision: str = "",
    notes: List[str] | None = None,
    execution_id: str | None = None,
    event_type: str = "QUESTION_ANALYSIS",
    execution_status: str = "COMPLETED",
    error_details: str | None = None,
    scenario_id: str | None = None,
    scenario_title: str | None = None,
    step_id: str | None = None,
    step_title: str | None = None,
    workflow_stages: List[str] | None = None,
    provenance: str = "RUNTIME_EXECUTION",
    domain: str | None = None,
    jurisdiction: str | None = None,
) -> Dict[str, Any]:

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    exec_id = execution_id or f"RUN-{uuid.uuid4().hex[:12]}"

    record = {
        "timestamp": timestamp,
        "question": question,
        "pipeline_version": PIPELINE_VERSION,
        "model": model,
        "execution_id": exec_id,
        "event_type": event_type,
        "execution_status": execution_status,
        "error_details": error_details,
        "scenario_id": scenario_id,
        "scenario_title": scenario_title,
        "step_id": step_id,
        "step_title": step_title,
        "workflow_stages": workflow_stages or [],
        "provenance": provenance,
        "domain": domain,
        "jurisdiction": jurisdiction,
        "retrieved_evidence": retrieved_evidence or [],
        "evidence_classification": evidence_classification or {},
        "evidence_assessment": evidence_assessment or {},
        "absence_verification": absence_verification or [],
        "gap_analysis": gap_analysis or {},
        "risk_assessment": risk_assessment or {},
        "final_synthesis": final_synthesis or {},
        "claim_evidence_mappings": (
            claim_evidence_mappings or []
        ),
        "human_review_required": (
            human_review_required
        ),
        "human_reviewer": human_reviewer,
        "human_action": human_action,
        "reviewer_modifications": (
            reviewer_modifications
        ),
        "final_decision": final_decision,
        "notes": notes or [],
    }

    record["audit_id"] = generate_audit_id(
        record
    )

    return record


def append_audit_record(
    record: Dict[str, Any],
) -> str:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    with AUDIT_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
        )
        file.write("\n")
    return record["audit_id"]


def load_audit_records() -> List[Dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []
    records = []
    with AUDIT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(
                json.loads(line)
            )
    return records


def append_review_event(
    event: Dict[str, Any],
) -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    with REVIEW_EVENTS_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                event,
                ensure_ascii=False,
                default=str,
            )
        )
        file.write("\n")


def load_review_events() -> List[Dict[str, Any]]:
    if not REVIEW_EVENTS_FILE.exists():
        return []
    events = []
    with REVIEW_EVENTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            events.append(
                json.loads(line)
            )
    return events


def get_latest_review_event(
    audit_id: str,
) -> Dict[str, Any] | None:
    events = load_review_events()
    for ev in reversed(events):
        if ev.get("audit_id") == audit_id:
            return ev
    return None


def get_all_latest_review_events() -> Dict[str, Dict[str, Any]]:
    events = load_review_events()
    latest_map: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        aid = ev.get("audit_id")
        if aid:
            latest_map[aid] = ev
    return latest_map


def apply_review_overlay(
    record: Dict[str, Any],
    review_event: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    overlay = dict(record)

    req = bool(overlay.get("human_review_required", False))
    overlay["human_review_required"] = req

    if review_event:
        action = str(
            review_event.get("human_action")
            or review_event.get("final_decision")
            or "APPROVED"
        ).upper()

        overlay["human_review_status"] = action
        overlay["human_action"] = action
        overlay["final_decision"] = action
        overlay["human_reviewer"] = (
            review_event.get("reviewer") or "Human reviewer"
        )
        overlay["reviewer"] = overlay["human_reviewer"]
        overlay["review_timestamp"] = review_event.get("timestamp")
        overlay["reviewer_modifications"] = review_event.get("reviewer_modifications")
        overlay["reviewer_reason"] = review_event.get("reviewer_reason")
        if "execution_id" in review_event and not overlay.get("execution_id"):
            overlay["execution_id"] = review_event["execution_id"]
    else:
        overlay["human_review_status"] = "PENDING"
        overlay["human_action"] = ""
        overlay["final_decision"] = (
            "PENDING_HUMAN_REVIEW"
            if req
            else overlay.get("final_decision", "SYSTEM_RECOMMENDATION")
        )
        overlay["human_reviewer"] = overlay.get("human_reviewer", "")
        overlay["reviewer"] = overlay.get("human_reviewer", "")
        overlay["review_timestamp"] = None
        overlay["reviewer_modifications"] = None
        overlay["reviewer_reason"] = None

    return overlay
