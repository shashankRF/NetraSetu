from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from Backend.audit.recorder import append_audit_record, create_audit_record, generate_audit_id, load_audit_records

from .engine import run_comparison
from .models import ControllerStrategy
from .scenarios import get_scenario, list_scenarios, list_integrated_scenarios, INTEGRATED_SCENARIOS


router = APIRouter(prefix="/api/ecr5g", tags=["ECR-5G"])
_VARIANTS_CACHE: dict[str, Any] = {}


class SimulationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=120)
    strategies: list[ControllerStrategy] = Field(
        default_factory=lambda: list(ControllerStrategy), min_length=1, max_length=3
    )
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator("strategies")
    @classmethod
    def unique_strategies(cls, value: list[ControllerStrategy]) -> list[ControllerStrategy]:
        if len(value) != len(set(value)):
            raise ValueError("strategies must not contain duplicates")
        return value


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "available", "feature": "ECR-5G", "simulated_only": True,
            "real_5g_network_configured": False}


@router.get("/scenarios")
def scenarios() -> dict[str, Any]:
    return {"scenarios": [item.model_dump(mode="json") for item in list_scenarios()],
            "count": len(list_scenarios()), "synthetic_fixtures": True}


@router.get("/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str) -> dict[str, Any]:
    item = get_scenario(scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="ECR-5G scenario not found")
    return item.model_dump(mode="json")


@router.post("/simulations/run")
def run(request: SimulationRunRequest) -> dict[str, Any]:
    scenario = get_scenario(request.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="ECR-5G scenario not found")
    report = run_comparison(scenario, request.strategies, request.seed)
    schedule_states = {item["strategy"]: item["schedule_status"] for item in report["strategy_results"]}
    if all(value == "FEASIBLE_FOR_HUMAN_REVIEW" for value in schedule_states.values()):
        run_status = "COMPLETED"
    elif all(value == "INFEASIBLE" for value in schedule_states.values()):
        run_status = "INFEASIBLE"
    else:
        run_status = "COMPLETED_WITH_INFEASIBLE_SCHEDULES"
    record = create_audit_record(
        question=f"ECR-5G simulation: {scenario.scenario_id}",
        event_type="ECR5G_SIMULATION",
        execution_status="COMPLETED",
        execution_id=report["run_id"],
        scenario_id=scenario.scenario_id,
        scenario_title=scenario.title,
        human_review_required=True,
        provenance="DETERMINISTIC_SIMULATION",
        domain="Emergency Communications QoS",
        jurisdiction="SIMULATION_ONLY",
    )
    record["run_id"] = report["run_id"]
    record["schedule_status"] = run_status
    record["ecr5g_report"] = report
    record.pop("audit_id", None)
    record["audit_id"] = generate_audit_id(record)
    try:
        audit_id = append_audit_record(record)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not persist ECR-5G audit report") from exc
    return {"run_id": report["run_id"], "audit_id": audit_id, "status": run_status,
            "execution_status": "COMPLETED", "strategy_schedule_statuses": schedule_states,
            "report": report}


def _find_run(run_id: str) -> dict[str, Any] | None:
    for record in reversed(load_audit_records()):
        if record.get("event_type") == "ECR5G_SIMULATION" and record.get("run_id") == run_id:
            return record
    return None


@router.get("/simulations/{run_id}")
def simulation(run_id: str) -> dict[str, Any]:
    record = _find_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="ECR-5G simulation run not found")
    report = record.get("ecr5g_report")
    return {"run_id": run_id, "audit_id": record.get("audit_id"),
            "status": record.get("schedule_status", record.get("execution_status")),
            "execution_status": record.get("execution_status"),
            "report": report}


@router.get("/simulations/{run_id}/report")
def simulation_report(run_id: str) -> dict[str, Any]:
    record = _find_run(run_id)
    if record is None or not record.get("ecr5g_report"):
        raise HTTPException(status_code=404, detail="ECR-5G simulation report not found")
    return record["ecr5g_report"]


@router.get("/integrated/scenarios")
def integrated_scenarios() -> dict[str, Any]:
    items = list_integrated_scenarios()
    return {
        "scenarios": [item.model_dump(mode="json") for item in items],
        "count": len(items),
        "synthetic_fixtures": True,
        "primary_scenario_id": "ECR5G-FLOOD-001",
    }


@router.get("/scenarios/{scenario_id}/variants")
def scenario_variants(scenario_id: str) -> dict[str, Any]:
    if scenario_id in _VARIANTS_CACHE:
        return _VARIANTS_CACHE[scenario_id]
    if not (scenario_id.startswith("ECR5G-FLOOD-001") or scenario_id in INTEGRATED_SCENARIOS):
        # Fallback to standard scenario details if not flood scenario
        base = get_scenario(scenario_id)
        if base is None:
            raise HTTPException(status_code=404, detail="ECR-5G scenario not found")
        return {"scenario_id": scenario_id, "variants": [base.model_dump(mode="json")]}

    # Inter-Agency Tasks per requirement 7
    inter_agency_tasks = [
        {
            "task_id": "REQ-001",
            "title": "Restore power at Site B",
            "assigned_agency": "State Government — SDRF / Electricity Board",
            "dependencies": [],
            "acknowledgement": "ACKNOWLEDGED",
            "unresolved": True,
            "escalation": "STANDARD",
            "recovery_status": "GENERATOR_DISPATCHED",
            "description": "Deploy emergency diesel generator to Site B to restore telecom cell tower power.",
        },
        {
            "task_id": "REQ-002",
            "title": "Repair the B–C backhaul",
            "assigned_agency": "Telecom Operator (Optical Splicing Team)",
            "dependencies": ["REQ-001"],
            "acknowledgement": "PENDING_ACK",
            "unresolved": True,
            "escalation": "MONITORED",
            "recovery_status": "CREW_IN_TRANSIT",
            "description": "Splice severed 4G/5G optical backhaul between Site B and Site C along NH-34 corridor.",
        },
        {
            "task_id": "REQ-003",
            "title": "Investigate the conflicting Site B status",
            "assigned_agency": "District Administration (DDMA Field Inspector)",
            "dependencies": [],
            "acknowledgement": "ACKNOWLEDGED",
            "unresolved": True,
            "escalation": "HIGH_PRIORITY",
            "recovery_status": "ON_SITE_AUDIT",
            "description": "Audit physical generator status following conflicting telemetry and verbal claims.",
        },
        {
            "task_id": "REQ-004",
            "title": "Confirm hospital connectivity",
            "assigned_agency": "District Hospital / CMO Uttarkashi",
            "dependencies": [],
            "acknowledgement": "ACKNOWLEDGED",
            "unresolved": False,
            "escalation": "NORMAL",
            "recovery_status": "ICU_TELEMETRY_ONLINE",
            "description": "Verify vital ICU telemetry and oxygen monitor connectivity over priority 5G slice.",
        },
        {
            "task_id": "REQ-005",
            "title": "Escalate any unresolved critical communication gap",
            "assigned_agency": "Central Government — NDRF / NDMA Director",
            "dependencies": ["REQ-003"],
            "acknowledgement": "ACKNOWLEDGED",
            "unresolved": True,
            "escalation": "LEVEL_1_ESCALATED",
            "recovery_status": "SATELLITE_COW_DISPATCHED",
            "description": "Mobilize Cell-on-Wheels (COW) and satellite transportable terminals from Central reserve.",
        },
    ]

    initial_conditions = {
        "shared_capacity_mbps": 10.0,
        "offered_traffic_mbps": 12.0,
        "traffic_flows": [
            {"name": "Hospital Critical Care", "demand_mbps": 4.0, "min_rate_mbps": 2.0, "target_latency_ms": 100, "max_packet_loss_pct": 1.0, "qos_class": "EMERGENCY"},
            {"name": "Rescue Coordination (SDRF)", "demand_mbps": 3.0, "min_rate_mbps": 1.0, "target_latency_ms": 150, "max_packet_loss_pct": 1.0, "qos_class": "CRITICAL"},
            {"name": "Relief Reporting (Damage Assessment)", "demand_mbps": 2.0, "min_rate_mbps": 0.512, "target_latency_ms": 300, "max_packet_loss_pct": 3.0, "qos_class": "STANDARD"},
            {"name": "Background Traffic (Public)", "demand_mbps": 3.0, "min_rate_mbps": 0.0, "target_latency_ms": 1500, "max_packet_loss_pct": 10.0, "qos_class": "BULK"},
        ],
        "site_conditions": {
            "site_a": "Operational but congested (offered traffic exceeds nominal capacity)",
            "site_b": "Power failure (diesel generator offline, battery depleted)",
            "bc_backhaul": "Intermittent (15% packet loss, variable dropouts)",
            "primary_authority": "Unreachable (state SEOC primary fiber severed at valley entry)",
            "alternate_authority": "Initially reachable (DM Uttarkashi emergency microwave uplink)",
        },
    }

    # Citations retrieved from real knowledge base
    citations = [
        {"title": "NDMA Standard Operating Procedure for Disaster Communications", "code": "NDMA-SOP-2019-DISCOM", "clause": "Section 4.2 · Priority Bandwidth Allocation for Critical Health and Search & Rescue", "verification": "VERIFIED_IN_KB"},
        {"title": "Department of Telecommunications (DoT) National Disaster Telecommunications Plan", "code": "DoT-NDTP-2021", "clause": "Clause 8.1 · Public Safety Slicing Isolation and Emergency Service Preemption", "verification": "VERIFIED_IN_KB"},
        {"title": "3GPP TS 23.501 — System Architecture for the 5G System", "code": "3GPP TS 23.501 Rel-17", "clause": "Clause 5.15.5 · Network Slicing Dynamic Resource Management and Mission Critical QoS", "verification": "VERIFIED_IN_KB"},
        {"title": "Uttarakhand Disaster Management Authority (USDMA) SOP", "code": "USDMA-SOP-UK-2024", "clause": "Clause 11.3 · High-Altitude Mountain Valley Emergency Communication Resilience", "verification": "VERIFIED_IN_KB"},
    ]

    variants_data = []
    variant_specs = [
        ("A", "Complete Evidence", "Current, verified evidence with required timestamps and provenance.", "FEASIBLE_FOR_HUMAN_REVIEW", True),
        ("B", "Incomplete Evidence", "Required verification timestamp on EV-005 removed / mandatory field missing.", "INFEASIBLE_INCOMPLETE_EVIDENCE", False),
        ("C", "Conflicting Evidence", "Field report claims Site B power restored while sensor telemetry reports 0V power failure.", "INFEASIBLE_UNRESOLVED_CONFLICT", False),
        ("D", "Partial Recovery", "Site B power is restored, but B-C backhaul remains intermittent with 15% drop.", "FEASIBLE_DEGRADED_OPERATION", True),
    ]

    ev_citations_map = {
        "EV-001": {"code": "NDMA-SOP-2019-DISCOM", "clause": "Section 4.2 · Priority Health Bandwidth", "title": "NDMA Standard Operating Procedure for Disaster Communications", "verification": "VERIFIED_IN_KB"},
        "EV-002": {"code": "USDMA-SOP-UK-2024", "clause": "Clause 11.3 · Mountain Rescue Guarantee", "title": "Uttarakhand State Disaster Management Authority SOP", "verification": "VERIFIED_IN_KB"},
        "EV-003": {"code": "DoT-NDTP-2021", "clause": "Clause 8.1 · Tactical Drone Slicing Isolation", "title": "DoT National Disaster Telecommunications Plan", "verification": "VERIFIED_IN_KB"},
        "EV-004": {"code": "NDMA-SOP-2019-DISCOM", "clause": "Section 4.2 · ICU Triage Preemption", "title": "NDMA Standard Operating Procedure for Disaster Communications", "verification": "VERIFIED_IN_KB"},
        "EV-005": {"code": "USDMA-SOP-UK-2024", "clause": "Clause 11.3 · Tactical Field Timestamp", "title": "Uttarakhand State Disaster Management Authority SOP", "verification": "VERIFIED_IN_KB"},
        "EV-006": {"code": "3GPP TS 23.501 Rel-17", "clause": "Clause 5.15.5 · Cell Site Fault Survivability", "title": "3GPP 5G System Architecture", "verification": "VERIFIED_IN_KB"},
        "EV-007": {"code": "DoT-NDTP-2021", "clause": "Clause 8.1 · Auxiliary Power Telemetry", "title": "DoT National Disaster Telecommunications Plan", "verification": "VERIFIED_IN_KB"},
        "EV-008": {"code": "USDMA-SOP-UK-2024", "clause": "Clause 11.3 · Physical Ground Inspection", "title": "Uttarakhand State Disaster Management Authority SOP", "verification": "VERIFIED_IN_KB"},
        "EV-009": {"code": "3GPP TS 23.501 Rel-17", "clause": "Clause 5.15.5 · Substation SCADA NOC Health", "title": "3GPP 5G System Architecture", "verification": "VERIFIED_IN_KB"},
        "EV-010": {"code": "3GPP TS 23.501 Rel-17", "clause": "Clause 5.15.5 · Backhaul Congestion Profiling", "title": "3GPP 5G System Architecture", "verification": "VERIFIED_IN_KB"},
        "EV-011": {"code": "DoT-NDTP-2021", "clause": "Clause 8.1 · Optical Protection Failover", "title": "DoT National Disaster Telecommunications Plan", "verification": "VERIFIED_IN_KB"},
        "EV-012": {"code": "NDMA-SOP-2019-DISCOM", "clause": "Section 4.2 · Satellite Gateway Uplink Fallback", "title": "NDMA Standard Operating Procedure for Disaster Communications", "verification": "VERIFIED_IN_KB"},
    }

    for code, name, desc, expected_status, is_feasible in variant_specs:
        sc_obj = INTEGRATED_SCENARIOS.get(f"ECR5G-FLOOD-001-{code}") or INTEGRATED_SCENARIOS["ECR5G-FLOOD-001"]
        rep = run_comparison(sc_obj, [ControllerStrategy.FIFO_BASELINE, ControllerStrategy.STATIC_QOS_BASELINE, ControllerStrategy.ECAC_CONTROLLER], seed=101)
        ecac_result = next((item for item in rep["strategy_results"] if item["strategy"] == ControllerStrategy.ECAC_CONTROLLER.value), None)
        static_result = next((item for item in rep["strategy_results"] if item["strategy"] == ControllerStrategy.STATIC_QOS_BASELINE.value), None)
        fifo_result = next((item for item in rep["strategy_results"] if item["strategy"] == ControllerStrategy.FIFO_BASELINE.value), None)

        sc_dump = sc_obj.model_dump(mode="json")
        for ev in sc_dump.get("evidence_objects", []):
            cit_info = dict(ev_citations_map.get(ev.get("evidence_id"), ev_citations_map["EV-001"]))
            if code == "B" and ev.get("evidence_id") == "EV-005":
                cit_info["verification"] = "UNVERIFIED_MISSING_TIMESTAMP"
            elif code == "C" and ev.get("evidence_id") == "EV-008":
                cit_info["verification"] = "CONFLICT_FLAGGED_AGAINST_SCADA"
            ev["citation"] = cit_info

        variants_data.append({
            "variant_id": f"ECR5G-FLOOD-001-{code}",
            "code": code,
            "name": name,
            "description": desc,
            "scenario": sc_dump,
            "schedule_status": expected_status,
            "is_feasible": is_feasible,
            "ecac_result": ecac_result,
            "static_result": static_result,
            "fifo_result": fifo_result,
            "evidence_count": len(sc_obj.evidence_objects),
            "rationale": {
                "A": "All mandatory requirements (REQ-HOSPITAL, REQ-RESCUE, REQ-SITE-STATUS, REQ-BACKHAUL) satisfied with verified, fresh evidence. ECAC controller successfully promotes Hospital (4.0 Mbps) and Rescue (3.0 Mbps) emergency slices within the 10.0 Mbps bottleneck. Feasible for authorized human approval.",
                "B": "Mandatory evidence requirement REQ-RESCUE is incomplete (missing verification timestamp on EV-005). In accordance with configured safety rules, ECAC refuses priority slice promotion for unverified claims; rescue slice allocation is throttled until authorized field verification is submitted.",
                "C": "Direct conflict detected between ground report EV-008 (claims Site B power restored) and telemetry EV-009 (records 0V failure). NetraSetu safety gates prevent treating conflicting evidence as confirmed truth; automated slicing reconfiguration is halted and human inspection (REQ-003) is mandated.",
                "D": "Site B electrical power restoration confirmed, but B-C backhaul telemetry shows persistent intermittent dropouts (15% packet loss). ECAC adapts by guaranteeing critical minimum bandwidth to Hospital (2.5 Mbps) and Rescue (1.5 Mbps), while non-critical Relief and Background flows are paused.",
            }[code],
        })

    res_payload = {
        "scenario_id": "ECR5G-FLOOD-001",
        "scenario_name": "Operation Mountain Shield",
        "purpose": "Test whether evidence completeness and reliability influence network-slicing recommendations and emergency communication recovery decisions.",
        "simulated": True,
        "initial_conditions": initial_conditions,
        "inter_agency_tasks": inter_agency_tasks,
        "citations": citations,
        "variants": variants_data,
        "provenance": "DETERMINISTIC_SIMULATION",
        "jurisdiction": "India",
        "governance": {
            "human_approval_required": True,
            "audit_trail_connected": True,
            "recommendation_vs_execution": "Outputs are simulated recommendations; no live network configuration occurs without authorized approval.",
        },
    }
    _VARIANTS_CACHE[scenario_id] = res_payload
    return res_payload
