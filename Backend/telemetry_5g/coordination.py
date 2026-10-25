"""Deterministic local-only agency-message mapping and transport simulation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional


AGENCIES = (
    "District Administration",
    "State Government — SDRF Uttarakhand",
    "Central Government — NDRF",
    "Telecom Operator",
)
TRANSPORT_MODES = {
    "AVAILABLE",
    "DELAYED",
    "UNAVAILABLE",
    "UNAVAILABLE_THEN_RECONNECT",
}


def _delivery(mode: str, *, delay_ms: int, ttl_ms: int, retry_interval_ms: int,
              retry_limit: int, reconnect_after_ms: Optional[int]) -> Dict[str, Any]:
    transitions: List[Dict[str, Any]] = [{"state": "QUEUED_SIMULATED", "elapsed_ms": 0}]
    if mode == "AVAILABLE":
        transitions.extend([
            {"state": "DELIVERED_SIMULATED", "elapsed_ms": 0},
            {"state": "ACKNOWLEDGED_SIMULATED", "elapsed_ms": 0},
        ])
    elif mode == "DELAYED":
        transitions.append({"state": "DELAYED_SIMULATED", "elapsed_ms": 0})
        if delay_ms > ttl_ms:
            transitions.append({"state": "EXPIRED_SIMULATED", "elapsed_ms": ttl_ms})
        else:
            transitions.extend([
                {"state": "DELIVERED_SIMULATED", "elapsed_ms": delay_ms},
                {"state": "ACKNOWLEDGED_SIMULATED", "elapsed_ms": delay_ms},
            ])
    elif mode == "UNAVAILABLE_THEN_RECONNECT":
        transitions.append({"state": "UNAVAILABLE_SIMULATED", "elapsed_ms": 0})
        for attempt in range(1, retry_limit + 1):
            elapsed = attempt * retry_interval_ms
            if elapsed >= min(ttl_ms, reconnect_after_ms or 0):
                break
            transitions.append({"state": "RETRY_QUEUED_SIMULATED", "elapsed_ms": elapsed,
                                "attempt": attempt})
        reconnect_at = reconnect_after_ms if reconnect_after_ms is not None else ttl_ms + 1
        if reconnect_at > ttl_ms:
            transitions.append({"state": "EXPIRED_SIMULATED", "elapsed_ms": ttl_ms})
        else:
            transitions.extend([
                {"state": "DELIVERED_SIMULATED", "elapsed_ms": reconnect_at},
                {"state": "ACKNOWLEDGED_SIMULATED", "elapsed_ms": reconnect_at},
            ])
    else:  # UNAVAILABLE
        transitions.append({"state": "UNAVAILABLE_SIMULATED", "elapsed_ms": 0})
        for attempt in range(1, retry_limit + 1):
            elapsed = attempt * retry_interval_ms
            if elapsed >= ttl_ms:
                transitions.append({"state": "EXPIRED_SIMULATED", "elapsed_ms": ttl_ms})
                break
            transitions.append({"state": "RETRY_QUEUED_SIMULATED", "elapsed_ms": elapsed,
                                "attempt": attempt})
        else:
            final_elapsed = retry_limit * retry_interval_ms
            if final_elapsed >= ttl_ms:
                if transitions[-1]["state"] != "EXPIRED_SIMULATED":
                    transitions.append({"state": "EXPIRED_SIMULATED", "elapsed_ms": ttl_ms})
            else:
                transitions.append({"state": "FAILED_SIMULATED", "elapsed_ms": final_elapsed,
                                    "reason": "Retry limit reached while simulated link remained unavailable."})
    return {
        "mode": mode,
        "final_status": transitions[-1]["state"],
        "transitions": transitions,
        "retry_limit": retry_limit,
        "ttl_ms": ttl_ms,
        "retry_interval_ms": retry_interval_ms,
        "delay_ms": delay_ms,
        "reconnect_after_ms": reconnect_after_ms,
        "model": "deterministic_local_state_model_v1",
        "real_transport": False,
    }


def build_agency_messages(
    *,
    run_id: str,
    scenario_id: Optional[str],
    profile: str,
    failures: List[str],
    simulation_case_id: Optional[str] = None,
    metrics: Dict[str, Any],
    slo_status: str,
    recovery_recommendations: List[Dict[str, Any]],
    risk: Dict[str, Any],
    evidence: Dict[str, Any],
    communication_mode: str = "AVAILABLE",
    delay_ms: int = 250,
    ttl_ms: int = 1000,
    retry_interval_ms: int = 100,
    retry_limit: int = 2,
    reconnect_after_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Create recipient-specific information from one immutable run result."""
    if communication_mode not in TRANSPORT_MODES:
        raise ValueError(f"Unsupported simulated communication mode: {communication_mode}")
    created_at = datetime.now(timezone.utc).isoformat()
    citations = [
        {"evidence_id": item.get("evidence_id"),
         "source_title": item.get("source_title"),
         "document_identifier": item.get("document_identifier"),
         "clause": item.get("full_clause_hierarchy") or item.get("clause"),
         "page": item.get("page"),
         "verification_status": item.get("verification_status"),
         "applicability": item.get("applicability"),
         "local_viewer_url": item.get("local_viewer_url")}
        for item in evidence.get("sources", [])
    ]
    citation_refs = [item["evidence_id"] for item in citations
                     if item.get("evidence_id") and item.get("verification_status") in
                     {"EXACT_MATCH_VERIFIED", "MATCH_VERIFIED_WITH_OCR"}]
    metrics_text = (
        f"Profile {profile}; failures {', '.join(failures) or 'baseline'}; "
        f"simulated p95 {metrics.get('tail_latency_p95_ms')} ms, "
        f"packet loss {metrics.get('packet_loss_pct')}%, "
        f"delivery {metrics.get('delivery_success_rate')}%; SLO status {slo_status}."
    )
    bodies = {
        "District Administration": (
            f"{metrics_text} Geographic impact is not modeled. Review is {risk.get('review_status')}; "
            "verify affected-area conditions independently before operational use."
        ),
        "State Government — SDRF Uttarakhand": (
            f"{metrics_text} Road access and response dependencies are unavailable in this model. "
            "Field/access status requires separate verification."
        ),
        "Central Government — NDRF": (
            f"{metrics_text} Escalation recommendation: {risk.get('escalation_level')}; "
            f"evidence: {risk.get('evidence_status_detail')}; review gate: {risk.get('review_status')}. "
            "No resource request or authorization is created."
        ),
        "Telecom Operator": (
            f"{metrics_text} Modeled recovery recommendations: "
            f"{', '.join(item.get('action_type', '') for item in recovery_recommendations) or 'none'}. "
            "Recommendations were not executed; outputs are synthetic."
        ),
    }
    outputs = []
    for recipient in AGENCIES:
        delivery = _delivery(
            communication_mode, delay_ms=delay_ms, ttl_ms=ttl_ms,
            retry_interval_ms=retry_interval_ms, retry_limit=retry_limit,
            reconnect_after_ms=reconnect_after_ms,
        )
        msg_id = "MSG-" + sha256(f"{run_id}|{recipient}".encode()).hexdigest()[:16]
        outputs.append({
            "message_id": msg_id,
            "run_id": run_id,
            "scenario_id": scenario_id,
            "simulation_case_id": simulation_case_id,
            "intended_recipient": recipient,
            "body": bodies[recipient],
            "source": "NetraSetu simulated failure-combination run",
            "source_run_id": run_id,
            "source_metric_provenance": "SIMULATION",
            "created_at_utc": created_at,
            "timestamp_semantics": "server message-creation time; simulated elapsed time is in transport transitions",
            "evidence_references": citation_refs,
            "citation_details": citations,
            "risk_level": risk.get("risk_level"),
            "risk_score": risk.get("risk_score"),
            "escalation_level": risk.get("escalation_level"),
            "review_status": risk.get("review_status"),
            "provenance": "SIMULATED_DEMO",
            "delivery": delivery,
            "external_delivery": False,
        })
    return outputs
