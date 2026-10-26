"""Source-backed incident analysis and synthetic aftermath workflows using NetraSetu engines."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from Backend.aftermath_fixtures import get_scenario, list_scenarios
from Backend.audit.recorder import append_audit_record, create_audit_record, generate_audit_id, load_audit_records
from Backend.risk_engine import (
    AIAnalysis, AuthorityRequirement, DecisionContext, DecisionImpact,
    EvidenceAssessment, EvidenceQuality, EvidenceStatus, RiskEngine,
)

router = APIRouter(prefix="/api/aftermath", tags=["post-disaster-aftermath-analysis"])

ACTION_TRANSITIONS = {
    "PROPOSED": {"UNDER_REVIEW", "REJECTED"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"COMPLETED", "BLOCKED"},
    "BLOCKED": {"IN_PROGRESS", "REJECTED"},
    "COMPLETED": set(), "REJECTED": set(),
}
REQUEST_TRANSITIONS = {
    "OPEN": {"RESOLVED"},
    "PENDING": {"ACKNOWLEDGED", "ESCALATED"},
    "ACKNOWLEDGED": {"ESCALATED", "RESOLVED"},
    "ESCALATED": {"ACKNOWLEDGED", "RESOLVED"},
    "RESOLVED": set(),
}


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: str = Field(min_length=3, max_length=24)
    reason: str = Field(default="", max_length=500)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=1, max_length=30)


class IncidentAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str = Field(default="Dharali, Bhatwari Tehsil, Uttarkashi, Uttarakhand", min_length=3, max_length=180)
    incident_start: date = date(2025, 8, 1)
    incident_end: date = date(2025, 8, 30)
    incident_details: str = Field(min_length=10, max_length=6000)
    analysis_focus: str = Field(default="Assess source-supported damage, remaining evidence gaps, and safe rehabilitation review steps.", min_length=10, max_length=2000)
    elevation_or_terrain_input: str = Field(default="Not supplied", max_length=1500)
    facility_or_asset_ids: list[str] = Field(default_factory=lambda: ["DHARALI-SETTLEMENT", "KHEER-GAD-RUNOUT", "BHAGIRATHI-CONFLUENCE", "DHARALI-MUKHBA-ACCESS"], max_length=30)


def _events(scenario_id: str) -> list[dict[str, Any]]:
    try:
        return [item for item in load_audit_records()
                if item.get("scenario_id") == scenario_id and str(item.get("event_type", "")).startswith("AFTERMATH_")]
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="The existing audit ledger could not be read; aftermath state is unavailable.")


def _active_events(scenario_id: str) -> list[dict[str, Any]]:
    events = _events(scenario_id)
    reset_positions = [i for i, event in enumerate(events) if event.get("event_type") == "AFTERMATH_SCENARIO_RESET"]
    return events[reset_positions[-1] + 1:] if reset_positions else events


def _actor(request: Request) -> str:
    from Backend.authentication import require_session
    return str(require_session(request).get("username", "reviewer"))


def _save_event(*, scenario_id: str, actor: str, event_type: str, summary: str,
                payload: dict[str, Any], provenance: str = "SIMULATED_SCENARIO_REVIEW",
                domain: str = "Post-disaster aftermath simulation", jurisdiction: str = "SIMULATION_ONLY") -> str:
    record = create_audit_record(
        question=summary, event_type=event_type, execution_status="RECORDED",
        scenario_id=scenario_id, scenario_title=scenario_id,
        human_reviewer=actor, human_action=event_type,
        human_review_required=True, provenance=provenance,
        domain=domain, jurisdiction=jurisdiction,
    )
    record.update(payload)
    record.pop("audit_id", None)
    record["audit_id"] = generate_audit_id(record)
    try:
        return append_audit_record(record)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="The action was not recorded because the audit ledger could not be written.") from exc


def _action_states(scenario_id: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for event in _active_events(scenario_id):
        if event.get("event_type") == "AFTERMATH_ACTION_TRANSITION":
            states[str(event.get("action_id"))] = str(event.get("new_status"))
    return states


def _request_states(scenario_id: str) -> dict[str, dict[str, str]]:
    states: dict[str, dict[str, str]] = defaultdict(dict)
    for event in _active_events(scenario_id):
        if event.get("event_type") == "AFTERMATH_REQUEST_TRANSITION":
            rid = str(event.get("request_id"))
            if event.get("field") == "acknowledgement_state":
                states[rid]["acknowledgement_state"] = str(event.get("new_status"))
            if event.get("field") == "resolution_state":
                states[rid]["resolution_state"] = str(event.get("new_status"))
            if event.get("field") == "escalation_status":
                states[rid]["escalation_status"] = str(event.get("new_status"))
    return states


def _facility_status(facility: dict[str, Any], asset_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    linked = [asset_by_id[item] for item in facility.get("primary_site_ids", []) if item in asset_by_id]
    if not linked:
        return {"facility_id": facility["facility_id"], "connectivity_status": "UNKNOWN", "availability_pct": None,
                "connected_site_ids": [], "missing_dependency": True}
    alive = [asset for asset in linked if (asset.get("availability_pct") or 0) > 0]
    status = "UNAVAILABLE" if not alive else "AVAILABLE" if len(alive) == len(linked) and all(a.get("service_status") == "AVAILABLE" for a in alive) else "DEGRADED"
    values = [float(asset["availability_pct"]) for asset in linked if asset.get("availability_pct") is not None]
    return {"facility_id": facility["facility_id"], "connectivity_status": status,
            "availability_pct": round(sum(values) / len(values), 2) if values else None,
            "connected_site_ids": [a["asset_id"] for a in alive], "missing_dependency": not bool(alive)}


def _risk_assessment(priority_score: int, has_conflict: bool) -> dict[str, Any]:
    evidence_status = EvidenceStatus.CONFLICTING if has_conflict else EvidenceStatus.INSUFFICIENT
    evidence = EvidenceAssessment(
        quality=EvidenceQuality.INSUFFICIENT, evidence_status=evidence_status,
        missing_evidence=["Independent source verification is not included in synthetic scenario fixtures."],
        contradicting_count=1 if has_conflict else 0,
    )
    context = DecisionContext(
        domain="Disaster response and critical communications",
        decision_impact=DecisionImpact.SAFETY, consequence_score=min(100, priority_score),
        authority_requirement=AuthorityRequirement.SENIOR_AUTHORITY,
        external_action=True, affects_public_safety=True, affects_critical_infrastructure=True,
    )
    result = RiskEngine().assess(context, evidence, AIAnalysis(confidence=0.0, hallucination_risk=1.0, novel_situation=True))
    return {"risk_level": result.risk_level.value, "risk_score": result.risk_score,
            "escalation_level": result.escalation_level.value,
            "human_review_required": result.human_review_required,
            "mandatory_review": result.mandatory_review,
            "blocking_conditions": list(result.blocking_conditions),
            "reasons": list(result.reasons), "source_engine": "Backend.risk_engine.RiskEngine",
            "decision_authorized": False}


def _priority(action: dict[str, Any], scenario: dict[str, Any], facility_statuses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    assets = {item["asset_id"]: item for item in scenario["assets"]}
    facilities = {item["facility_id"]: item for item in scenario["facilities"]}
    trigger_id = action["trigger_asset_id"]
    trigger = assets.get(trigger_id, facilities.get(trigger_id, {}))
    dependent = [facility for facility in scenario["facilities"]
                if trigger_id in facility.get("primary_site_ids", []) or trigger_id == facility["facility_id"]]
    affected_pop = max((int(item.get("estimated_population_served", 0)) for item in dependent), default=0)
    critical = any(item.get("criticality") == "CRITICAL" for item in dependent)
    severity = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}.get(trigger.get("severity"), 50)
    impact = max(0, 100 - int(trigger.get("availability_pct", 0) or 0))
    no_alternative = any(not item.get("alternative_connectivity") for item in dependent)
    access_blocked = any(road.get("status") == "CLOSED" and action["action_id"] in road.get("delays_action_ids", []) for road in scenario["roads"])
    factors = {
        "critical_service": {"weight": 0.30, "value": 100 if critical else 40, "reason": "At least one dependent facility is marked critical in the synthetic fixture." if critical else "No critical dependent facility is listed."},
        "population_served": {"weight": 0.20, "value": round(min(100, affected_pop / 5000 * 100), 2), "reason": f"Largest listed dependent facility population: {affected_pop}; synthetic estimate."},
        "service_impact": {"weight": 0.25, "value": severity, "reason": f"Trigger asset severity: {trigger.get('severity', 'not recorded')}."},
        "alternative_connectivity": {"weight": 0.15, "value": 100 if no_alternative else 35, "reason": "A dependent critical facility has no alternative path in the scenario." if no_alternative else "At least one alternative is listed; its real availability is not measured."},
        "access_constraint": {"weight": 0.10, "value": 100 if access_blocked else 0, "reason": "A closed road is recorded as an action dependency." if access_blocked else "No blocking road dependency is recorded for this action."},
    }
    score = round(sum(item["weight"] * item["value"] for item in factors.values()), 2)
    priority = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 40 else "LOW"
    governance = _risk_assessment(int(score), any(r.get("verification_status") == "CONFLICTING" and r.get("asset_id") == trigger_id for r in scenario["reports"]))
    return {"score": score, "priority": priority, "factors": factors, "dependent_facility_ids": [f["facility_id"] for f in dependent],
            "estimated_population_served": affected_pop, "evidence_uncertainty": "HIGH · fixture evidence is simulated; missing evidence never lowers priority",
            "governance": governance}


def _materialize(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    events = _active_events(scenario_id)
    action_states = _action_states_without_events(events)
    request_states = _request_states_without_events(events)
    asset_by_id = {item["asset_id"]: item for item in scenario["assets"]}
    facility_statuses = {item["facility_id"]: _facility_status(item, asset_by_id) for item in scenario["facilities"]}
    actions = []
    for action in scenario["actions"]:
        row = dict(action)
        row["status"] = action_states.get(row["action_id"], row["status"])
        row["priority_analysis"] = _priority(row, scenario, facility_statuses)
        row["audit_history"] = [e for e in events if e.get("action_id") == row["action_id"]]
        actions.append(row)
    requests = []
    for item in scenario["requests"]:
        row = dict(item)
        row.update(request_states.get(row["request_id"], {}))
        row["audit_history"] = [e for e in events if e.get("request_id") == row["request_id"]]
        requests.append(row)
    open_actions = [item for item in actions if item["status"] not in {"COMPLETED", "REJECTED"}]
    open_requests = [item for item in requests if item["resolution_state"] != "RESOLVED"]
    assets = scenario["assets"]
    status_counts = Counter(item["service_status"] for item in assets)
    conflicts = defaultdict(list)
    for report in scenario["reports"]:
        conflicts[report.get("asset_id")].append(report)
    competing = [{"asset_id": asset_id, "reports": rows, "status": "CONFLICTING", "action_required": "Independent verification; do not select a winner automatically."}
                 for asset_id, rows in conflicts.items() if len(rows) > 1 and any(row.get("verification_status") == "CONFLICTING" for row in rows)]
    overview = {
        "settlements_affected": len(scenario["settlements"]),
        "estimated_population": sum(item["population_estimate"] for item in scenario["settlements"]),
        "critical_facilities_affected": sum(1 for facility in scenario["facilities"] if facility_statuses[facility["facility_id"]]["connectivity_status"] != "AVAILABLE"),
        "road_closures": sum(1 for road in scenario["roads"] if road["status"] == "CLOSED"),
        "telecom_site_status": dict(status_counts),
        "unresolved_damage_reports": sum(1 for report in scenario["reports"] if report.get("verification_status") != "SOURCE_VERIFIED"),
        "pending_recovery_actions": len(open_actions),
        "outstanding_agency_requests": len(open_requests),
        "evidence_completeness": {"status": "SIMULATED_ONLY", "source_verified_count": 0, "record_count": len(scenario["evidence"]), "note": "These scenario records are not source-verified policy evidence."},
    }
    return {**scenario, "overview": overview, "facility_connectivity": list(facility_statuses.values()),
            "actions": actions, "requests": requests, "conflicting_reports": competing,
            "gap_analysis": [{"gap_id": "GAP-TELEMETRY-VERIFICATION", "status": "CONFLICTING" if competing else "POTENTIAL_GAP", "what_is_missing": "Independent source verification and current network telemetry", "evidence_examined": [r["record_id"] for r in scenario["reports"]], "finding": "Fixture claims and telemetry are simulated; no real event or policy requirement is established.", "recommended_action": "Request an independent site check and retain both claims until reconciled."}],
            "network_analysis": {"status": "READY_TO_RUN", "engine": "Backend.telemetry_5g.combination_engine.run_combination_search", "provenance": "SIMULATED_ONLY"},
            "reset_policy": "Reset restores fixture baseline by appending a reset event; prior audit records are retained and remain inspectable."}


def _action_states_without_events(events: list[dict[str, Any]]) -> dict[str, str]:
    return {str(e["action_id"]): str(e["new_status"]) for e in events if e.get("event_type") == "AFTERMATH_ACTION_TRANSITION"}


def _request_states_without_events(events: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for event in events:
        if event.get("event_type") == "AFTERMATH_REQUEST_TRANSITION":
            field = str(event.get("field"))
            if field in {"acknowledgement_state", "resolution_state", "escalation_status"}:
                result[str(event.get("request_id"))][field] = str(event.get("new_status"))
    return result


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "available", "fixture_scenarios": len(list_scenarios()), "simulated_only": True,
            "network_engine": "Backend.telemetry_5g.combination_engine", "risk_engine": "Backend.risk_engine.RiskEngine"}


@router.get("/incident-sources/dharali-2025")
def dharali_sources() -> dict[str, Any]:
    from Backend.dharali_evidence import TARGETS, source_catalog
    return {
        "incident_id": "DHARALI-FLASH-FLOOD-2025-08-05",
        "incident_name": "Kheer Gad flash flood and debris flow, Dharali",
        "location": "Dharali, Bhatwari Tehsil, Uttarkashi district, Uttarakhand, India",
        "incident_date": "2025-08-05",
        "analysis_window": {"start": "2025-08-01", "end": "2025-08-30"},
        "source_observation_dates": ["2025-08-06 NRSC post-event map", "2025-08-07 ISRO/NRSC post-event imagery referenced on official ISRO page", "2024-06-13 NRSC pre-event image"],
        "sources": source_catalog(),
        "assessment_targets": TARGETS,
        "elevation_status": "Absolute elevation raster/data not retrieved. GSI provides qualitative steep-gradient context and relative settlement position only.",
        "facility_status": "Four mapped incident assessment targets; named facility-by-facility operational condition not retrieved.",
    }


@router.post("/incident-analysis")
def analyze_incident(payload: IncidentAnalysisRequest, request: Request) -> dict[str, Any]:
    """Run a query-time BM25 evidence search and send every input into governance."""
    from Backend.dharali_evidence import SOURCES, TARGETS, search_incident_evidence

    coverage_start, coverage_end = date(2025, 8, 1), date(2025, 8, 30)
    if payload.incident_start < coverage_start or payload.incident_end > coverage_end or payload.incident_start > payload.incident_end:
        raise HTTPException(status_code=422, detail="The ingested source pack only covers the requested Dharali event window 2025-08-01 through 2025-08-30. No analysis was run outside that window.")
    if "dharali" not in payload.location.casefold() and "kheer gad" not in payload.location.casefold():
        raise HTTPException(status_code=422, detail="This ingested incident source pack covers Dharali / Kheer Gad only; no other location was analyzed.")

    query = " ".join([payload.location, payload.incident_details, payload.analysis_focus, payload.elevation_or_terrain_input, "Dharali Kheer Gad flash flood debris flow Bhagirathi river bridge road damage rehabilitation"])
    passages = search_incident_evidence(query, top_k=6)
    relevant = [row for row in passages if row["retrieval_score"] > 0]
    sources_used = sorted({row["source_id"] for row in relevant})
    targets = [item for item in TARGETS if item["target_id"] in payload.facility_or_asset_ids]
    missing_target_ids = sorted(set(payload.facility_or_asset_ids) - {item["target_id"] for item in targets})
    missing_evidence = [
        "Current field inspection and geolocated damage status for each selected target.",
        "Current road/bridge passability and engineering safety clearance.",
        "Current river obstruction, water-level and downstream-hazard measurements.",
        "Absolute elevation/DEM and current terrain survey; the sources provide only mapped/qualitative terrain context.",
        "Rehabilitation cost, household needs, services-restoration progress and authorized recovery plan.",
    ]
    evidence_status = EvidenceStatus.INSUFFICIENT
    evidence = EvidenceAssessment(
        quality=EvidenceQuality.MODERATE if relevant else EvidenceQuality.INSUFFICIENT,
        evidence_status=evidence_status,
        supporting_count=len(relevant),
        primary_source_count=len(sources_used),
        official_source_count=len(sources_used),
        source_diversity=len(sources_used),
        missing_evidence=missing_evidence,
    )
    parameters = {
        "incident_id": "DHARALI-FLASH-FLOOD-2025-08-05",
        "incident_name": "Kheer Gad flash flood and debris flow, Dharali",
        "location": payload.location,
        "requested_incident_window": {"start": payload.incident_start.isoformat(), "end": payload.incident_end.isoformat()},
        "source_coverage_window": {"start": coverage_start.isoformat(), "end": coverage_end.isoformat()},
        "incident_details_user_supplied": payload.incident_details,
        "analysis_focus_user_supplied": payload.analysis_focus,
        "elevation_or_terrain_input": payload.elevation_or_terrain_input,
        "source_observation_dates": ["2024-06-13 pre-event image", "2025-08-06 NRSC map observation", "2025-08-07 post-event imagery cited by ISRO"],
        "retrieval_engine": "BM25 over PyMuPDF-extracted official GSI and NRSC/NDEM PDF page text",
        "retrieved_passage_count": len(relevant),
        "source_ids": sources_used,
        "targets_in_scope": targets,
        "unknown_target_ids": missing_target_ids,
        "evidence_status": evidence_status.value,
        "known_data_limitations": missing_evidence,
        "absolute_elevation_m": None,
        "facility_level_operational_status": "NOT_RETRIEVED",
        "cause_of_event": "NOT_ESTABLISHED_BY_THIS_ANALYSIS",
        "human_review_required": True,
        "operational_action_authorized": False,
    }
    context = DecisionContext(
        domain="Dharali post-disaster recovery assessment",
        decision_impact=DecisionImpact.SAFETY,
        consequence_score=85,
        authority_requirement=AuthorityRequirement.SENIOR_AUTHORITY,
        external_action=False,
        affects_public_safety=True,
        affects_critical_infrastructure=True,
    )
    governance_result = RiskEngine().assess(context, evidence, AIAnalysis(confidence=0.0, hallucination_risk=0.0, novel_situation=True))
    governance = {
        "risk_level": governance_result.risk_level.value,
        "risk_score": governance_result.risk_score,
        "escalation_level": governance_result.escalation_level.value,
        "human_review_required": governance_result.human_review_required,
        "mandatory_review": governance_result.mandatory_review,
        "blocking_conditions": list(governance_result.blocking_conditions),
        "reasons": list(governance_result.reasons),
        "decision_authorized": False,
        "next_recommended_step": "Keep rehabilitation and reopening decisions pending. Obtain current field, bridge/road-engineering, and river-safety verification, then submit the evidence package to the officially designated incident authority; the specific accountable office is NOT RETRIEVED from these sources.",
        "authority_citation_status": "NOT_RETRIEVED: the two ingested assessment documents do not establish which authority approved a present rehabilitation decision.",
        "analysis_parameters": parameters,
    }
    citations = []
    for row in relevant:
        source = SOURCES[row["source_id"]]
        citations.append({
            "source_id": row["source_id"], "document_title": row["title"], "issuing_authority": row["authority"],
            "official_url": row["url"], "local_document_url": "/api/documents/raw/knowledge_base/Dharali%20Incident%202025/" + source["path"].name,
            "page": row["page"], "extracted_line_range": row["extracted_line_range"], "retrieval_score": row["retrieval_score"],
            "statement": row["excerpt"][:1600], "evidence_type": "OFFICIAL_DOCUMENT_PASSAGE",
        })
    if not citations:
        citations = [{"statement": "Evidence not retrieved — no matching passage was found in the ingested official sources.", "source_id": None, "page": None}]

    actions = [
        {"step": 1, "recommendation": "Request geolocated field verification of the four assessment targets and attach dated photographs/inspection records.", "gate": "Human review; no damage state presumed beyond cited source observations."},
        {"step": 2, "recommendation": "Obtain current road/bridge engineering clearance and river/channel assessment before restoring access or authorizing works.", "gate": "Officially designated decision authority: NOT RETRIEVED; confirm the responsible office before assignment."},
        {"step": 3, "recommendation": "Build a rehabilitation plan only after verified household, utility, access, and terrain survey data are added to this analysis.", "gate": "Needs assessment and accountable authority not present in retrieved sources."},
    ]
    result_id = "AFTER-DHARALI-2025"
    actor = _actor(request)
    audit_id = _save_event(
        scenario_id=result_id, actor=actor, event_type="AFTERMATH_INCIDENT_ANALYSIS",
        summary=f"Source-backed aftermath evidence search for Dharali, {payload.incident_start} through {payload.incident_end}.",
        provenance="OFFICIAL_GSI_NRSC_PDF_EVIDENCE_SEARCH",
        domain="Post-disaster aftermath evidence and governance review", jurisdiction="India / Uttarakhand",
        payload={"analysis_parameters": parameters, "governance": governance, "citations": citations,
                 "recommended_steps": actions, "source_ids": sources_used, "retrieval_engine": parameters["retrieval_engine"],
                 "operational_action_authorized": False},
    )
    return {"analysis_id": audit_id, "scenario_id": result_id, "incident_id": parameters["incident_id"],
            "status": "COMPLETED" if relevant else "EVIDENCE_NOT_RETRIEVED", "evidence_status": evidence_status.value,
            "summary": "Retrieved official source passages for the submitted Dharali incident details. Current facility condition, absolute elevation and rehabilitation progress remain unverified." if relevant else "Evidence not retrieved — no matching source passage was found.",
            "targets": targets, "citations": citations, "missing_evidence": missing_evidence,
            "recommended_steps": actions, "governance": governance, "analysis_parameters": parameters,
            "retrieval_engine": parameters["retrieval_engine"], "audit_id": audit_id,
            "live_telemetry_used": False, "operational_action_authorized": False}


@router.get("/scenarios")
def scenarios() -> dict[str, Any]:
    return {"scenarios": list_scenarios(), "count": len(list_scenarios()), "source_type": "SIMULATED"}


@router.get("/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str) -> dict[str, Any]:
    return _materialize(scenario_id)


@router.post("/scenarios/{scenario_id}/compare")
def compare_scenarios(scenario_id: str, comparison: str = "AFTER-UTT-002") -> dict[str, Any]:
    left = _materialize(scenario_id)
    right = _materialize(comparison)
    metric_keys = ["estimated_population", "critical_facilities_affected", "road_closures", "pending_recovery_actions", "outstanding_agency_requests"]
    deltas = {key: right["overview"][key] - left["overview"][key] for key in metric_keys}
    return {"left": {"scenario_id": left["scenario_id"], "title": left["title"], "overview": left["overview"]},
            "right": {"scenario_id": right["scenario_id"], "title": right["title"], "overview": right["overview"]},
            "right_minus_left": deltas, "provenance": "SYNTHETIC_FIXTURE_COMPARISON"}


@router.post("/scenarios/{scenario_id}/network-analysis")
def network_analysis(scenario_id: str, request: Request) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    from Backend.telemetry_5g.combination_engine import run_combination_search
    report = run_combination_search(profile="CRITICAL_INFRA", failure_types=scenario["network_failure_types"],
                                    combination_depth=min(2, len(scenario["network_failure_types"])),
                                    max_scenarios=10, samples=100, seed=scenario["seed"])
    actor = _actor(request)
    summary = [{"failure_types": row["configuration"]["failure_types"], "status": row["status"], "metrics": row.get("metrics", {}),
                "comparison_to_baseline": row.get("comparison_to_baseline"), "policy_evaluation": row.get("policy_evaluation")}
               for row in report["results"]]
    audit_id = _save_event(scenario_id=scenario_id, actor=actor, event_type="AFTERMATH_NETWORK_ANALYSIS",
                           summary=f"Ran existing deterministic 5G combination engine for {scenario_id}.",
                           payload={"run_id": report["run_id"], "analysis_status": report["status"], "seed": scenario["seed"], "failure_types": scenario["network_failure_types"], "result_count": len(summary), "simulated_only": True})
    return {"scenario_id": scenario_id, "audit_id": audit_id, "report": report,
            "records_are_simulated": True, "real_network_measurements": False}


@router.post("/actions/{action_id}/transition")
def transition_action(action_id: str, payload: TransitionRequest, request: Request, scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    action = next((item for item in scenario["actions"] if item["action_id"] == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Recovery action not found in this scenario.")
    current = _action_states(scenario_id).get(action_id, action["status"])
    allowed = ACTION_TRANSITIONS.get(current, set())
    if payload.new_status not in allowed:
        raise HTTPException(status_code=409, detail=f"Invalid recovery-action transition {current} → {payload.new_status}; allowed: {sorted(allowed)}.")
    if payload.new_status == "APPROVED" and current != "UNDER_REVIEW":
        raise HTTPException(status_code=409, detail="A recovery action must enter human review before approval.")
    if payload.new_status == "COMPLETED":
        states = _request_states(scenario_id)
        unresolved = [dep for dep in action.get("dependencies", []) if states.get(dep, {}).get("resolution_state", "OPEN") != "RESOLVED"]
        if unresolved:
            raise HTTPException(status_code=409, detail=f"Action is blocked by unresolved dependencies: {', '.join(unresolved)}.")
    actor = _actor(request)
    audit_id = _save_event(scenario_id=scenario_id, actor=actor, event_type="AFTERMATH_ACTION_TRANSITION",
                           summary=f"Recovery action {action_id} transitioned {current} to {payload.new_status}.",
                           payload={"action_id": action_id, "previous_status": current, "new_status": payload.new_status,
                                    "review_reason": payload.reason, "real_world_operation": False})
    return {"action_id": action_id, "previous_status": current, "status": payload.new_status, "audit_id": audit_id, "real_world_operation": False}


@router.post("/requests/{request_id}/transition")
def transition_request(request_id: str, payload: TransitionRequest, request: Request, scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    item = next((row for row in scenario["requests"] if row["request_id"] == request_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Coordination request not found in this scenario.")
    current_state = _request_states(scenario_id).get(request_id, {})
    if payload.new_status == "ACKNOWLEDGED":
        field, current = "acknowledgement_state", current_state.get("acknowledgement_state", item["acknowledgement_state"])
    elif payload.new_status == "RESOLVED":
        field, current = "resolution_state", current_state.get("resolution_state", item["resolution_state"])
    elif payload.new_status == "ESCALATED":
        field, current = "escalation_status", current_state.get("escalation_status", item["escalation_status"])
        current = "PENDING" if current == "NOT_ESCALATED" else current
    else:
        raise HTTPException(status_code=422, detail="Request status must be ACKNOWLEDGED, ESCALATED, or RESOLVED.")
    transitions = REQUEST_TRANSITIONS if field != "escalation_status" else {"PENDING": {"ESCALATED"}, "ESCALATED": set()}
    if payload.new_status not in transitions.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid request transition {current} → {payload.new_status}.")
    actor = _actor(request)
    audit_id = _save_event(scenario_id=scenario_id, actor=actor, event_type="AFTERMATH_REQUEST_TRANSITION",
                           summary=f"Coordination request {request_id} changed to {payload.new_status}.",
                           payload={"request_id": request_id, "field": field, "previous_status": current,
                                    "new_status": payload.new_status, "review_reason": payload.reason, "external_delivery": False})
    return {"request_id": request_id, "field": field, "status": payload.new_status, "audit_id": audit_id, "external_delivery": False}


@router.post("/scenarios/{scenario_id}/reset")
def reset_scenario(scenario_id: str, payload: ResetRequest, request: Request) -> dict[str, Any]:
    if payload.confirmation != "RESET":
        raise HTTPException(status_code=422, detail='Type "RESET" to restore fixture baseline.')
    if get_scenario(scenario_id) is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    audit_id = _save_event(scenario_id=scenario_id, actor=_actor(request), event_type="AFTERMATH_SCENARIO_RESET",
                           summary=f"Reset {scenario_id} to its deterministic fixture baseline; prior events retained.",
                           payload={"reset_policy": "APPEND_ONLY_AUDIT; dynamic projection reset to immutable fixture", "prior_events_retained": True})
    return {"scenario_id": scenario_id, "status": "RESET_TO_FIXTURE_BASELINE", "audit_id": audit_id,
            "prior_audit_events_retained": True}


@router.get("/scenarios/{scenario_id}/timeline")
def timeline(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Aftermath scenario not found.")
    rows = list(scenario["timeline"])
    for event in _events(scenario_id):
        rows.append({"event_id": event.get("audit_id", "AUDIT-UNAVAILABLE"), "timestamp": event.get("timestamp"),
                     "event_type": event.get("event_type"), "summary": event.get("question", "Recorded action"),
                     "provenance": event.get("provenance", "SIMULATED_SCENARIO_REVIEW"), "audit_id": event.get("audit_id")})
    return {"scenario_id": scenario_id, "events": sorted(rows, key=lambda row: row.get("timestamp") or ""),
            "fixture_events_are_simulated": True, "audit_events_are_append_only": True}
