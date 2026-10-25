"""Small deterministic synthetic aftermath fixtures; no live incident claims."""
from __future__ import annotations

from copy import deepcopy

BASE_TIME = "2026-10-20T06:00:00Z"

_ASSETS = [
    {"asset_id": "TWR-UTT-01", "category": "TELECOM_SITE", "area": "Kumaon North (fictional assessment area)", "reported_impact": "Site unavailable after combined power and backhaul interruption", "severity": "CRITICAL", "service_status": "UNAVAILABLE", "availability_pct": 0, "latency_ms": None, "jitter_ms": None, "packet_loss_pct": 100, "power_status": "OUTAGE", "backhaul_status": "FAILED", "dependent_facility_ids": ["FAC-HOSP-01", "FAC-EOC-01"], "evidence_ids": ["OBS-TWR-01", "TEL-TWR-01"], "observed_at": BASE_TIME, "verification_status": "SIMULATED", "confidence": None, "follow_up": "Inspect power and backhaul independently; restore only after human verification", "assessment_status": "REPORTED_SIMULATED"},
    {"asset_id": "TWR-UTT-02", "category": "TELECOM_SITE", "area": "Kumaon North (fictional assessment area)", "reported_impact": "Reduced service under congestion", "severity": "HIGH", "service_status": "DEGRADED", "availability_pct": 62, "latency_ms": 184, "jitter_ms": 41, "packet_loss_pct": 8, "power_status": "AVAILABLE", "backhaul_status": "CONGESTED", "dependent_facility_ids": ["FAC-SHELTER-01", "FAC-WATER-01"], "evidence_ids": ["TEL-TWR-02"], "observed_at": BASE_TIME, "verification_status": "SIMULATED", "confidence": None, "follow_up": "Check backhaul capacity and neighboring site load", "assessment_status": "REPORTED_SIMULATED"},
    {"asset_id": "TWR-UTT-03", "category": "TELECOM_SITE", "area": "Garhwal Link (fictional assessment area)", "reported_impact": "Field report says restored; simulator telemetry conflicts", "severity": "HIGH", "service_status": "DEGRADED", "availability_pct": 38, "latency_ms": 312, "jitter_ms": 78, "packet_loss_pct": 16, "power_status": "AVAILABLE", "backhaul_status": "IMPAIRED", "dependent_facility_ids": ["FAC-EOC-01"], "evidence_ids": ["OBS-TWR-03", "TEL-TWR-03"], "observed_at": BASE_TIME, "verification_status": "CONFLICTING", "confidence": None, "follow_up": "Request fresh independent telemetry and field confirmation", "assessment_status": "CONFLICTING_REPORTS"},
    {"asset_id": "TWR-UTT-04", "category": "TELECOM_SITE", "area": "Garhwal Link (fictional assessment area)", "reported_impact": "Site operational with elevated latency", "severity": "MEDIUM", "service_status": "DEGRADED", "availability_pct": 81, "latency_ms": 92, "jitter_ms": 23, "packet_loss_pct": 3, "power_status": "AVAILABLE", "backhaul_status": "AVAILABLE", "dependent_facility_ids": ["FAC-HOSP-01"], "evidence_ids": ["TEL-TWR-04"], "observed_at": BASE_TIME, "verification_status": "SIMULATED", "confidence": None, "follow_up": "Continue monitoring; confirm route diversity", "assessment_status": "REPORTED_SIMULATED"},
    {"asset_id": "BH-UTT-01", "category": "BACKHAUL_LINK", "area": "Kumaon North (fictional assessment area)", "reported_impact": "Primary backhaul unavailable", "severity": "CRITICAL", "service_status": "UNAVAILABLE", "availability_pct": 0, "latency_ms": None, "jitter_ms": None, "packet_loss_pct": 100, "power_status": "AVAILABLE", "backhaul_status": "FAILED", "dependent_facility_ids": ["FAC-HOSP-01", "FAC-EOC-01"], "evidence_ids": ["OBS-BH-01"], "observed_at": BASE_TIME, "verification_status": "SIMULATED", "confidence": None, "follow_up": "Access inspection pending road clearance", "assessment_status": "REPORTED_SIMULATED"},
]

_FACILITIES = [
    {"facility_id": "FAC-HOSP-01", "name": "North Valley Hospital (fictional)", "category": "HOSPITAL", "estimated_population_served": 4800, "criticality": "CRITICAL", "primary_site_ids": ["TWR-UTT-01", "TWR-UTT-04"], "alternative_connectivity": False, "connectivity_status": "UNAVAILABLE", "evidence_ids": ["OBS-FAC-01"], "verification_status": "SIMULATED"},
    {"facility_id": "FAC-EOC-01", "name": "District EOC (fictional)", "category": "EMERGENCY_OPERATIONS", "estimated_population_served": 12000, "criticality": "CRITICAL", "primary_site_ids": ["TWR-UTT-01", "TWR-UTT-03"], "alternative_connectivity": True, "connectivity_status": "DEGRADED", "evidence_ids": ["OBS-FAC-02"], "verification_status": "SIMULATED"},
    {"facility_id": "FAC-SHELTER-01", "name": "Riverside Relief Shelter (fictional)", "category": "SHELTER", "estimated_population_served": 950, "criticality": "HIGH", "primary_site_ids": ["TWR-UTT-02"], "alternative_connectivity": False, "connectivity_status": "DEGRADED", "evidence_ids": ["OBS-FAC-03"], "verification_status": "SIMULATED"},
    {"facility_id": "FAC-WATER-01", "name": "Hill Water Utility (fictional)", "category": "WATER_UTILITY", "estimated_population_served": 3100, "criticality": "HIGH", "primary_site_ids": ["TWR-UTT-02"], "alternative_connectivity": True, "connectivity_status": "DEGRADED", "evidence_ids": ["OBS-FAC-04"], "verification_status": "SIMULATED"},
]

_ASSET_REPORTS = [
    {"record_id": "OBS-TWR-01", "asset_id": "TWR-UTT-01", "report": "Power and backhaul interruption reported in the simulation", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME, "evidence_ids": ["EV-SIM-01"]},
    {"record_id": "TEL-TWR-01", "asset_id": "TWR-UTT-01", "report": "Simulator state: unavailable; synthetic loss 100%", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME, "evidence_ids": ["EV-SIM-02"]},
    {"record_id": "OBS-TWR-03", "asset_id": "TWR-UTT-03", "report": "Field-role report claims site restored", "source_type": "SIMULATED", "verification_status": "CONFLICTING", "observed_at": "2026-10-20T06:05:00Z", "evidence_ids": ["EV-SIM-03"]},
    {"record_id": "TEL-TWR-03", "asset_id": "TWR-UTT-03", "report": "Simulator state shows 16% packet loss and degraded availability", "source_type": "SIMULATED", "verification_status": "CONFLICTING", "observed_at": "2026-10-20T06:06:00Z", "evidence_ids": ["EV-SIM-04"]},
    {"record_id": "OBS-ROAD-01", "asset_id": "ROAD-UTT-01", "report": "Road access constraint delays repair-team dispatch", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME, "evidence_ids": ["EV-SIM-05"]},
]

_ACTIONS = [
    {"action_id": "ACT-TWR-01-POWER", "trigger_asset_id": "TWR-UTT-01", "title": "Inspect and restore site power", "reason": "Critical site is reported without power and supports a hospital and the EOC.", "evidence_ids": ["OBS-TWR-01", "TEL-TWR-01"], "recommended_agency": "Telecom operator and power utility (simulated responsibility mapping)", "dependencies": [], "expected_outcome": "Power condition assessed and connectivity reassessed", "status": "PROPOSED", "human_approval_required": True},
    {"action_id": "ACT-BH-01-ACCESS", "trigger_asset_id": "BH-UTT-01", "title": "Clear access constraint and inspect backhaul", "reason": "Primary backhaul is unavailable; the repair route is blocked in the scenario.", "evidence_ids": ["OBS-BH-01", "OBS-ROAD-01"], "recommended_agency": "Road maintenance team with telecom operator (simulated responsibility mapping)", "dependencies": ["REQ-ROAD-01"], "expected_outcome": "Access status confirmed before field work", "status": "PROPOSED", "human_approval_required": True},
    {"action_id": "ACT-TWR-03-VERIFY", "trigger_asset_id": "TWR-UTT-03", "title": "Verify conflicting restoration report", "reason": "A simulated field claim conflicts with simulated telemetry; neither is treated as confirmed.", "evidence_ids": ["OBS-TWR-03", "TEL-TWR-03"], "recommended_agency": "Telecom operator (simulated responsibility mapping)", "dependencies": [], "expected_outcome": "Independent telemetry and field report reconciled", "status": "PROPOSED", "human_approval_required": True},
    {"action_id": "ACT-FAC-HOSP-ALT", "trigger_asset_id": "FAC-HOSP-01", "title": "Assess temporary alternative hospital connectivity", "reason": "Hospital is a critical facility without a scenario-recorded alternative connection.", "evidence_ids": ["OBS-FAC-01", "TEL-TWR-01"], "recommended_agency": "District administration and telecom operator (simulated responsibility mapping)", "dependencies": [], "expected_outcome": "Alternative connection options assessed by a human reviewer", "status": "PROPOSED", "human_approval_required": True},
]

_REQUESTS = [
    {"request_id": "REQ-ROAD-01", "sender_role": "District Administration", "recipient_role": "Road maintenance team", "created_at": "2026-10-20T06:10:00Z", "details": "Confirm access status on the fictional repair route.", "related_asset_id": "ROAD-UTT-01", "priority": "HIGH", "acknowledgement_state": "PENDING", "resolution_state": "OPEN", "dependencies": [], "escalation_status": "NOT_ESCALATED"},
    {"request_id": "REQ-POWER-01", "sender_role": "Telecom operator", "recipient_role": "Power utility", "created_at": "2026-10-20T06:12:00Z", "details": "Provide simulated power-restoration estimate for site TWR-UTT-01.", "related_asset_id": "TWR-UTT-01", "priority": "CRITICAL", "acknowledgement_state": "PENDING", "resolution_state": "OPEN", "dependencies": ["REQ-ROAD-01"], "escalation_status": "NOT_ESCALATED"},
    {"request_id": "REQ-HOSP-01", "sender_role": "District EOC", "recipient_role": "Telecom operator", "created_at": "2026-10-20T06:15:00Z", "details": "Assess alternate connectivity for the fictional hospital.", "related_asset_id": "FAC-HOSP-01", "priority": "CRITICAL", "acknowledgement_state": "ACKNOWLEDGED", "resolution_state": "OPEN", "dependencies": [], "escalation_status": "NOT_ESCALATED"},
]

_BASE = {
    "scenario_id": "AFTER-UTT-001", "title": "Severe monsoon disruption · synthetic assessment", "variant": "SEVERE_DISRUPTION",
    "description": "Deterministic fictionalized Uttarakhand assessment area. All scenario incidents, locations, populations, assets, telemetry, and agency records are synthetic.",
    "severity": "SEVERE", "assessment_time": BASE_TIME, "source_type": "SIMULATED", "seed": 7319,
    "settlements": [{"settlement_id": "SET-01", "name": "North Valley Cluster (fictional)", "population_estimate": 3600, "verification_status": "SIMULATED"}, {"settlement_id": "SET-02", "name": "Riverbend Cluster (fictional)", "population_estimate": 2100, "verification_status": "SIMULATED"}, {"settlement_id": "SET-03", "name": "Upper Ridge Cluster (fictional)", "population_estimate": 900, "verification_status": "SIMULATED"}],
    "facilities": _FACILITIES, "assets": _ASSETS,
    "roads": [{"record_id": "ROAD-UTT-01", "name": "North access road (fictional)", "status": "CLOSED", "observed_at": BASE_TIME, "source_type": "SIMULATED", "verification_status": "SIMULATED", "delays_action_ids": ["ACT-BH-01-ACCESS"]}, {"record_id": "ROAD-UTT-02", "name": "River route (fictional)", "status": "RESTRICTED", "observed_at": BASE_TIME, "source_type": "SIMULATED", "verification_status": "SIMULATED", "delays_action_ids": []}],
    "reports": _ASSET_REPORTS, "actions": _ACTIONS, "requests": _REQUESTS,
    "evidence": [{"evidence_id": "EV-SIM-01", "statement": "Synthetic scenario reports a power interruption at TWR-UTT-01.", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME}, {"evidence_id": "EV-SIM-02", "statement": "Synthetic simulator state records TWR-UTT-01 unavailable.", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME}, {"evidence_id": "EV-SIM-03", "statement": "Simulated field-role report says TWR-UTT-03 restored.", "source_type": "SIMULATED", "verification_status": "CONFLICTING", "observed_at": "2026-10-20T06:05:00Z"}, {"evidence_id": "EV-SIM-04", "statement": "Simulated network telemetry shows TWR-UTT-03 degraded with 16% packet loss.", "source_type": "SIMULATED", "verification_status": "CONFLICTING", "observed_at": "2026-10-20T06:06:00Z"}, {"evidence_id": "EV-SIM-05", "statement": "Synthetic road record states repair access is blocked.", "source_type": "SIMULATED", "verification_status": "SIMULATED", "observed_at": BASE_TIME}],
    "timeline": [{"event_id": "EVT-001", "timestamp": "2026-10-20T06:00:00Z", "event_type": "ASSESSMENT_STARTED", "summary": "Synthetic severe-disruption scenario loaded.", "provenance": "SIMULATED_FIXTURE"}, {"event_id": "EVT-002", "timestamp": "2026-10-20T06:05:00Z", "event_type": "CONFLICT_RECORDED", "summary": "Simulated restoration claim conflicts with simulator telemetry for TWR-UTT-03.", "provenance": "SIMULATED_FIXTURE"}, {"event_id": "EVT-003", "timestamp": "2026-10-20T06:10:00Z", "event_type": "REQUEST_CREATED", "summary": "Simulated road-access request created.", "provenance": "SIMULATED_FIXTURE"}],
    "network_failure_types": ["LINK_FAILURE", "CONGESTION", "PACKET_LOSS"],
    "assumptions": ["Population values and all place/asset records are synthetic and are not observations of real Uttarakhand locations.", "Facility connectivity is derived from the listed site dependencies and current scenario status.", "The network engine produces deterministic software simulation metrics, not live 5G measurements.", "No real agency is contacted and no operational action is executed."],
}


def _variant(scenario_id: str, title: str, variant: str, *, recovered: bool, conflict_only: bool = False) -> dict:
    item = deepcopy(_BASE)
    item.update(scenario_id=scenario_id, title=title, variant=variant)
    if recovered:
        for asset in item["assets"]:
            if asset["asset_id"] in {"TWR-UTT-01", "BH-UTT-01"}:
                asset.update(service_status="DEGRADED", availability_pct=48, latency_ms=211, jitter_ms=49, packet_loss_pct=11, power_status="AVAILABLE", backhaul_status="IMPAIRED")
                asset["follow_up"] = "Monitor residual service impairment and verify independently"
        for facility in item["facilities"]:
            if facility["facility_id"] in {"FAC-HOSP-01", "FAC-EOC-01"}:
                facility["connectivity_status"] = "DEGRADED"
            if facility["facility_id"] == "FAC-HOSP-01":
                facility["alternative_connectivity"] = True
        item["roads"][0]["status"] = "RESTRICTED"
        item["timeline"].append({"event_id": "EVT-004", "timestamp": "2026-10-20T08:30:00Z", "event_type": "PARTIAL_RECOVERY", "summary": "Synthetic scenario state records partial power and connectivity recovery; residual gaps remain.", "provenance": "SIMULATED_FIXTURE"})
    if conflict_only:
        item["title"] = title
        item["severity"] = "HIGH"
        item["network_failure_types"] = ["PACKET_LOSS", "LINK_FAILURE"]
        item["timeline"] = [e for e in item["timeline"] if e["event_type"] == "CONFLICT_RECORDED"]
    return item


SCENARIOS = {
    "AFTER-UTT-001": deepcopy(_BASE),
    "AFTER-UTT-002": _variant("AFTER-UTT-002", "Partial recovery · residual gaps · synthetic", "PARTIAL_RECOVERY", recovered=True),
    "AFTER-UTT-003": _variant("AFTER-UTT-003", "Conflicting restoration reports · synthetic", "CONFLICTING_REPORTS", recovered=False, conflict_only=True),
}


def get_scenario(scenario_id: str) -> dict | None:
    scenario = SCENARIOS.get(scenario_id)
    return deepcopy(scenario) if scenario else None


def list_scenarios() -> list[dict]:
    return [{key: item[key] for key in ("scenario_id", "title", "variant", "severity", "assessment_time", "source_type", "description")} for item in SCENARIOS.values()]
