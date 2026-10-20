from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .audit.recorder import (
    append_audit_record,
    append_review_event,
    apply_review_overlay,
    create_audit_record,
    get_all_latest_review_events,
    get_latest_review_event,
    load_audit_records,
)
from .demo_scenarios.library import get_scenarios


router = APIRouter(
    prefix="/api/audits",
    tags=["Audit Trail"],
)


class ReviewActionRequest(BaseModel):
    action: str = Field(..., description="Action: APPROVED, MODIFIED, or REJECTED")
    modification: Optional[str] = Field(None, description="Mandatory qualification text for MODIFIED")
    reason: Optional[str] = Field(None, description="Mandatory explanation text for REJECTED")
    reviewer: Optional[str] = Field("Human reviewer", description="Reviewer label")


def _build_scenario_map() -> Dict[str, Dict[str, Any]]:
    scenario_map = {}
    for s in get_scenarios():
        for st in s.get("steps", []):
            prompt = st.get("evidence_prompt", "").strip()
            scenario_map[prompt] = {
                "scenario_id": s.get("scenario_id"),
                "scenario_title": s.get("title"),
                "domain": s.get("domain"),
                "step_id": st.get("step_id"),
                "step_title": st.get("title"),
                "simulated": True,
            }
    return scenario_map


def enrich_audit_record(
    r: Dict[str, Any],
    scenario_map: Dict[str, Dict[str, Any]],
    review_event: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    q = (r.get("question") or "").strip()
    sc = scenario_map.get(q)

    # Domain
    domain = r.get("domain")
    if not domain:
        if sc:
            domain = sc["domain"]
        elif "evidence_classification" in r and isinstance(r["evidence_classification"], dict):
            domain = r["evidence_classification"].get("domain")

    if not domain:
        q_lower = q.lower()
        if any(w in q_lower for w in ["vessel", "maritime", "ais", "gnss", "imo"]):
            domain = "Maritime"
        elif any(w in q_lower for w in ["5g", "slicing", "telecom", "3gpp", "core", "6g"]):
            domain = "Telecom / 5G"
        elif any(w in q_lower for w in ["uav", "tactical", "datalink", "defence", "military"]):
            domain = "Defence"
        elif any(w in q_lower for w in ["policy", "regulation", "compliance", "dpdp", "trai", "dot", "act"]):
            domain = "Policy / Compliance"
        else:
            domain = "General Evidence"

    # Jurisdiction
    jur = r.get("jurisdiction")
    if not jur:
        retrieved = r.get("retrieved_evidence") or []
        for ev in retrieved:
            if isinstance(ev, dict):
                j = ev.get("jurisdiction") or (
                    ev.get("metadata", {}).get("jurisdiction")
                    if isinstance(ev.get("metadata"), dict)
                    else None
                )
                if j:
                    jur = j
                    break
    if not jur:
        if "european union" in q.lower() or " eu " in q.lower():
            jur = "European Union"
        else:
            jur = "India"

    # Type & Execution metadata
    raw_event_type = r.get("event_type")
    if raw_event_type:
        audit_type = raw_event_type
    elif sc or r.get("scenario_id"):
        audit_type = "SCENARIO_EXECUTION"
    else:
        audit_type = "QUESTION_ANALYSIS"

    execution_id = r.get("execution_id") or "Not recorded"
    execution_status = r.get("execution_status") or "COMPLETED"
    error_details = r.get("error_details")
    workflow_stages = r.get("workflow_stages") or []

    # Provenance
    provenance = r.get("provenance")
    if not provenance:
        provenance = "RUNTIME_EXECUTION" if r.get("execution_id") else "LEGACY_UNVERIFIED"

    # Risk
    risk_info = r.get("risk_assessment") or {}
    risk_level = risk_info.get("risk_level", "MODERATE")
    risk_score = risk_info.get("risk_score", 50)

    # Evidence Status
    ev_ass = r.get("evidence_assessment") or {}
    evidence_status = ev_ass.get("overall_status", "SUFFICIENT")

    # Human Review
    human_review = bool(r.get("human_review_required", False))
    if risk_info.get("human_review_required"):
        human_review = True

    # Synthesis excerpt
    synth = r.get("final_synthesis") or {}
    gap = r.get("gap_analysis") or {}
    if execution_status == "FAILED" and error_details:
        assessment = f"Execution failed: {error_details}"
    else:
        assessment = synth.get("assessment") or gap.get("verdict") or r.get("final_decision") or "Analysis completed."

    # Effective overlay
    overlaid = apply_review_overlay(r, review_event)

    # Resolve scenario structure
    scenario_info = sc
    if not scenario_info and r.get("scenario_id"):
        scenario_info = {
            "scenario_id": r.get("scenario_id"),
            "scenario_title": r.get("scenario_title") or r.get("scenario_id"),
            "step_id": r.get("step_id") or "STEP-01",
            "step_title": r.get("step_title") or "Scenario Step",
            "domain": domain,
            "simulated": True,
        }

    return {
        "audit_id": r.get("audit_id"),
        "execution_id": execution_id,
        "event_type": audit_type,
        "execution_status": execution_status,
        "error_details": error_details,
        "workflow_stages": workflow_stages,
        "provenance": provenance,
        "timestamp": r.get("timestamp"),
        "question": q,
        "audit_type": audit_type,
        "domain": domain,
        "jurisdiction": jur,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "evidence_status": evidence_status,
        "human_review_required": human_review,
        "human_review_status": overlaid.get("human_review_status", "PENDING"),
        "human_action": overlaid.get("human_action", ""),
        "final_decision": overlaid.get("final_decision", "PENDING_HUMAN_REVIEW"),
        "review_timestamp": overlaid.get("review_timestamp"),
        "reviewer_modifications": overlaid.get("reviewer_modifications"),
        "reviewer_reason": overlaid.get("reviewer_reason"),
        "reviewer": overlaid.get("reviewer") or overlaid.get("human_reviewer", ""),
        "evidence_count": len(r.get("retrieved_evidence") or []),
        "claims_count": len(synth.get("claims") or r.get("claim_evidence_mappings") or []),
        "assessment_excerpt": str(assessment)[:180],
        "scenario": scenario_info,
    }


def _sanitize_for_excel(val: Any) -> Any:
    if val is None:
        return ""
    val_str = str(val)
    if not val_str:
        return ""
    # Neutralize CSV/Excel formula injection (DDE commands)
    if val_str[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
        return "'" + val_str
    return val_str


def build_audit_excel_workbook(enriched_records: List[Dict[str, Any]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "HackGrid Audit Trail"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "Audit ID",
        "Execution / Run ID",
        "Timestamp (UTC)",
        "Event Type",
        "Question / Scenario",
        "Execution Status",
        "Workflow Stages / Agents",
        "Final Answer / Result",
        "Governance Decision",
        "Risk Level",
        "Risk Score",
        "Evidence Status",
        "Source References",
        "Escalation / Human Review Status",
        "Human Reviewer",
        "Error Details",
        "Provenance",
    ]

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    data_font = Font(name="Segoe UI", size=10)
    data_align_left = Alignment(horizontal="left", vertical="top", wrap_text=True)
    data_align_center = Alignment(horizontal="center", vertical="top")

    if not enriched_records:
        empty_note = ["No audit events recorded yet. Run a question or scenario to create your first audit record."] + [""] * (len(headers) - 1)
        ws.append(empty_note)
        empty_cell = ws.cell(row=2, column=1)
        empty_cell.font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        ws.row_dimensions[2].height = 22
    else:
        for row_idx, r in enumerate(enriched_records, start=2):
            q_text = r.get("question") or (r.get("scenario") or {}).get("step_title") or "Not recorded"
            stages = ", ".join(r.get("workflow_stages") or []) if r.get("workflow_stages") else "Not recorded"
            ev_sources = []
            for ev in (r.get("retrieved_evidence") or []):
                doc = ev.get("document") or ev.get("source") or ev.get("evidence_id")
                if doc:
                    ev_sources.append(str(doc))
            ev_sources_str = "; ".join(ev_sources[:5]) if ev_sources else "Not available"

            row_data = [
                _sanitize_for_excel(r.get("audit_id") or "Not recorded"),
                _sanitize_for_excel(r.get("execution_id") or "Not recorded"),
                _sanitize_for_excel(r.get("timestamp") or "Not recorded"),
                _sanitize_for_excel(r.get("event_type") or "QUESTION_ANALYSIS"),
                _sanitize_for_excel(q_text),
                _sanitize_for_excel(r.get("execution_status") or "COMPLETED"),
                _sanitize_for_excel(stages),
                _sanitize_for_excel(r.get("assessment_excerpt") or r.get("final_decision") or "Not available"),
                _sanitize_for_excel(r.get("final_decision") or "Not available"),
                _sanitize_for_excel(r.get("risk_level") or "Not recorded"),
                _sanitize_for_excel(r.get("risk_score") if r.get("risk_score") is not None else "Not recorded"),
                _sanitize_for_excel(r.get("evidence_status") or "Not recorded"),
                _sanitize_for_excel(ev_sources_str),
                _sanitize_for_excel(r.get("human_review_status") or ("REQUIRED" if r.get("human_review_required") else "NONE")),
                _sanitize_for_excel(r.get("reviewer") or "Not assigned"),
                _sanitize_for_excel(r.get("error_details") or "None"),
                _sanitize_for_excel(r.get("provenance") or "RUNTIME_EXECUTION"),
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 24
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = data_align_center if col_idx in (1, 2, 3, 4, 6, 9, 10, 11, 12, 14, 15, 17) else data_align_left

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 65)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


@router.get("")
def get_all_audits(
    search: Optional[str] = Query(None, description="Search term across question, audit_id, domain, assessment, execution_id"),
    domain: Optional[str] = Query(None, description="Filter by domain category"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    evidence_status: Optional[str] = Query(None, description="Filter by evidence status"),
    human_review_required: Optional[bool] = Query(None, description="Filter by human review requirement"),
    human_review_status: Optional[str] = Query(None, description="Filter by human review status"),
    audit_type: Optional[str] = Query(None, description="Filter by audit/event type"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    execution_status: Optional[str] = Query(None, description="Filter by execution status (COMPLETED, FAILED, BLOCKED)"),
    provenance: Optional[str] = Query(None, description="Filter by provenance (RUNTIME_EXECUTION, LEGACY_UNVERIFIED)"),
    sort: Optional[str] = Query("newest", description="Sort order: newest, oldest, highest_risk, lowest_risk"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    raw_records = load_audit_records()
    scenario_map = _build_scenario_map()
    latest_reviews = get_all_latest_review_events()

    enriched = [
        enrich_audit_record(
            r,
            scenario_map,
            latest_reviews.get(r.get("audit_id")),
        )
        for r in raw_records
    ]

    total_audits = len(enriched)
    critical_cases = sum(1 for a in enriched if str(a["risk_level"]).upper() == "CRITICAL")
    human_review_count = sum(1 for a in enriched if a["human_review_required"])
    simulated_count = sum(1 for a in enriched if "SCENARIO" in str(a["audit_type"]).upper())
    insufficient_count = sum(1 for a in enriched if str(a["evidence_status"]).upper() in ["INSUFFICIENT", "MISSING"])
    failed_count = sum(1 for a in enriched if str(a.get("execution_status")).upper() == "FAILED")
    runtime_count = sum(1 for a in enriched if str(a.get("provenance")).upper() == "RUNTIME_EXECUTION")
    legacy_count = sum(1 for a in enriched if str(a.get("provenance")).upper() == "LEGACY_UNVERIFIED")

    domain_counts: Dict[str, int] = {}
    jur_counts: Dict[str, int] = {}
    for a in enriched:
        d = a["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        j = a["jurisdiction"]
        jur_counts[j] = jur_counts.get(j, 0) + 1

    filtered = enriched

    if search:
        s_term = search.strip().lower()
        filtered = [
            a for a in filtered
            if s_term in (a.get("audit_id") or "").lower()
            or s_term in (a.get("execution_id") or "").lower()
            or s_term in (a.get("question") or "").lower()
            or s_term in (a.get("domain") or "").lower()
            or s_term in (a.get("jurisdiction") or "").lower()
            or s_term in (a.get("assessment_excerpt") or "").lower()
            or s_term in (a.get("error_details") or "").lower()
            or (a.get("scenario") and s_term in (a["scenario"].get("scenario_title") or "").lower())
            or (a.get("scenario") and s_term in (a["scenario"].get("scenario_id") or "").lower())
        ]

    if domain and domain.lower() != "all":
        filtered = [a for a in filtered if a["domain"].lower() == domain.lower()]

    if jurisdiction and jurisdiction.lower() != "all":
        filtered = [a for a in filtered if a["jurisdiction"].lower() == jurisdiction.lower()]

    if risk_level and risk_level.lower() != "all":
        filtered = [a for a in filtered if str(a["risk_level"]).lower() == risk_level.lower()]

    if evidence_status and evidence_status.lower() != "all":
        filtered = [a for a in filtered if str(a["evidence_status"]).lower() == evidence_status.lower()]

    if human_review_required is not None:
        filtered = [a for a in filtered if a["human_review_required"] == human_review_required]

    if human_review_status and human_review_status.lower() != "all":
        filtered = [
            a for a in filtered
            if str(a.get("human_review_status", "")).lower() == human_review_status.lower()
        ]

    if audit_type and audit_type.lower() != "all":
        at_clean = audit_type.lower().replace(" ", "").replace("/", "").replace("_", "")
        filtered = [
            a for a in filtered
            if at_clean in str(a.get("audit_type", "")).lower().replace(" ", "").replace("/", "").replace("_", "")
        ]

    if execution_status and execution_status.lower() != "all":
        filtered = [
            a for a in filtered
            if str(a.get("execution_status", "")).lower() == execution_status.lower()
        ]

    if provenance and provenance.lower() != "all":
        filtered = [
            a for a in filtered
            if str(a.get("provenance", "")).lower() == provenance.lower()
        ]

    if scenario_id:
        filtered = [
            a for a in filtered
            if a["scenario"] and a["scenario"]["scenario_id"].lower() == scenario_id.lower()
        ]

    # Sort
    if sort == "oldest":
        filtered.sort(key=lambda x: x["timestamp"] or "")
    elif sort == "highest_risk":
        filtered.sort(key=lambda x: x["risk_score"], reverse=True)
    elif sort == "lowest_risk":
        filtered.sort(key=lambda x: x["risk_score"])
    else:  # newest default
        filtered.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    paginated = filtered[offset : offset + limit]

    return {
        "total": total_audits,
        "filtered_count": len(filtered),
        "offset": offset,
        "limit": limit,
        "metrics": {
            "total_audits": total_audits,
            "critical_cases": critical_cases,
            "human_review_required": human_review_count,
            "simulated_scenarios": simulated_count,
            "insufficient_evidence": insufficient_count,
            "failed_cases": failed_count,
            "runtime_executions": runtime_count,
            "legacy_records": legacy_count,
            "domains": domain_counts,
            "jurisdictions": jur_counts,
        },
        "audits": paginated,
    }


@router.get("/export/excel")
def export_audit_excel():
    raw_records = load_audit_records()
    scenario_map = _build_scenario_map()
    latest_reviews = get_all_latest_review_events()

    # Enriched newest first
    enriched = [
        enrich_audit_record(
            r,
            scenario_map,
            latest_reviews.get(r.get("audit_id")),
        )
        for r in raw_records
    ]
    enriched.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    # Attach raw retrieved evidence for source reference building
    for enr, raw in zip(enriched, raw_records):
        enr["retrieved_evidence"] = raw.get("retrieved_evidence") or []

    excel_bytes = build_audit_excel_workbook(enriched)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"HackGrid_Audit_Trail_{date_str}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get("/{audit_id}")
def get_audit_detail(audit_id: str):
    raw_records = load_audit_records()
    target_record = None
    for r in raw_records:
        if r.get("audit_id") == audit_id:
            target_record = r
            break

    if target_record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Audit record '{audit_id}' not found.",
        )

    latest_review = get_latest_review_event(audit_id)
    scenario_map = _build_scenario_map()
    enriched_summary = enrich_audit_record(target_record, scenario_map, latest_review)

    full_payload = dict(target_record)
    full_payload = apply_review_overlay(full_payload, latest_review)
    full_payload["scenario"] = enriched_summary.get("scenario")
    full_payload["domain"] = enriched_summary.get("domain")
    full_payload["jurisdiction"] = enriched_summary.get("jurisdiction")
    full_payload["audit_type"] = enriched_summary.get("audit_type")
    full_payload["execution_id"] = enriched_summary.get("execution_id")
    full_payload["execution_status"] = enriched_summary.get("execution_status")
    full_payload["error_details"] = enriched_summary.get("error_details")
    full_payload["workflow_stages"] = enriched_summary.get("workflow_stages")
    full_payload["provenance"] = enriched_summary.get("provenance")

    # Find related events sharing the same execution_id
    related_events = []
    target_exec_id = enriched_summary.get("execution_id")
    latest_reviews = get_all_latest_review_events()
    if target_exec_id and target_exec_id not in ("Not recorded", ""):
        for other_r in raw_records:
            if other_r.get("execution_id") == target_exec_id and other_r.get("audit_id") != audit_id:
                related_events.append(enrich_audit_record(
                    other_r,
                    scenario_map,
                    latest_reviews.get(other_r.get("audit_id")),
                ))
    full_payload["related_events"] = related_events

    return full_payload


@router.post("/{audit_id}/review")
def review_audit(
    audit_id: str,
    request: ReviewActionRequest,
):
    raw_records = load_audit_records()
    target_record = None
    for r in raw_records:
        if r.get("audit_id") == audit_id:
            target_record = r
            break

    if target_record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Audit record '{audit_id}' not found.",
        )

    action = (request.action or "").strip().upper()
    if action not in ("APPROVED", "MODIFIED", "REJECTED", "ESCALATED", "DEFERRED", "INVESTIGATE"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{request.action}'. Action must be one of: APPROVED, MODIFIED, REJECTED, ESCALATED, DEFERRED, INVESTIGATE.",
        )

    modification_text = None
    reason_text = None

    if action == "MODIFIED":
        if not request.modification or not request.modification.strip():
            raise HTTPException(
                status_code=422,
                detail="Action MODIFIED requires non-empty 'modification' text.",
            )
        modification_text = request.modification.strip()

    elif action in ("REJECTED", "ESCALATED", "DEFERRED", "INVESTIGATE"):
        if action == "REJECTED" and (not request.reason or not request.reason.strip()):
            raise HTTPException(
                status_code=422,
                detail="Action REJECTED requires non-empty 'reason' text.",
            )
        reason_text = request.reason.strip() if request.reason else None

    reviewer_label = (request.reviewer or "").strip() or "Human reviewer"
    timestamp = datetime.now(timezone.utc).isoformat()
    exec_id = target_record.get("execution_id")

    review_event = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "human_action": action,
        "final_decision": action,
        "execution_id": exec_id,
        "reviewer": reviewer_label,
        "reviewer_modifications": modification_text,
        "reviewer_reason": reason_text,
    }
    append_review_event(review_event)

    # Record persistent GOVERNANCE_DECISION event linked to the execution
    target_q = target_record.get("question") or "Analysis Item"
    gov_record = create_audit_record(
        question=f"Governance Decision: {action} on {audit_id} ({target_q[:80]})",
        execution_id=exec_id,
        event_type="GOVERNANCE_DECISION",
        execution_status="COMPLETED",
        human_review_required=False,
        human_reviewer=reviewer_label,
        human_action=action,
        final_decision=action,
        reviewer_modifications=modification_text or "",
        workflow_stages=["Human Review Console", "Audit Trail Ledger"],
        notes=[f"Action: {action}. Target Audit: {audit_id}. Reviewer: {reviewer_label}. Reason: {reason_text or modification_text or 'None'}"],
        provenance="RUNTIME_EXECUTION",
        domain=target_record.get("domain"),
        jurisdiction=target_record.get("jurisdiction"),
    )
    append_audit_record(gov_record)

    effective_state = apply_review_overlay(target_record, review_event)

    return {
        "audit_id": audit_id,
        "human_review_required": effective_state["human_review_required"],
        "human_review_status": effective_state["human_review_status"],
        "human_action": effective_state["human_action"],
        "final_decision": effective_state["final_decision"],
        "review_timestamp": effective_state["review_timestamp"],
        "reviewer_modifications": effective_state["reviewer_modifications"],
        "reviewer_reason": effective_state["reviewer_reason"],
        "governance_audit_id": gov_record.get("audit_id"),
    }
