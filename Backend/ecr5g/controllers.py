from __future__ import annotations

from .models import ControllerStrategy, ECR5GScenario, QoSClass


# Static policy is fixed and never consults evidence state.
STATIC_QOS_RANK = {QoSClass.EMERGENCY: 0, QoSClass.CRITICAL: 1, QoSClass.STANDARD: 2, QoSClass.BULK: 3}


def _eligible_dependencies(packet: dict, scenario: ECR5GScenario, now_ms: float) -> list[tuple]:
    flow = next(flow for flow in scenario.traffic_flows if flow.flow_id == packet["flow_id"])
    decision = next((item for item in scenario.decision_requirements if item.incident_id == flow.incident_id), None)
    if not decision:
        return []
    requirements = {item.requirement_id: item for item in scenario.evidence_requirements}
    evidence_objects = {item.evidence_id: item for item in scenario.evidence_objects}
    eligible = []
    for evidence_id in flow.evidence_ids:
        evidence = evidence_objects.get(evidence_id)
        if evidence is None:
            continue
        for requirement_id in set(decision.mandatory_evidence_requirements).intersection(evidence.supports_requirements):
            requirement = requirements[requirement_id]
            evidence_age = ((scenario.simulation_epoch_utc - evidence.source_timestamp_utc).total_seconds()
                            + now_ms / 1000)
            deadline_ms = (requirement.deadline_utc - scenario.simulation_epoch_utc).total_seconds() * 1000
            requires_resolution = requirement.requires_conflict_resolution or decision.requires_conflict_resolution
            conflict_resolved = (
                evidence.conflict_status.value == "CLEAR"
                or (evidence.conflict_status.value in {"CONFLICTING", "SUPERSEDED"}
                    and requires_resolution
                    and bool(evidence.conflict_resolution_reference))
            )
            if (evidence.incident_id != flow.incident_id
                    or evidence.evidence_type != requirement.evidence_type
                    or (requirement.permitted_source_identifiers
                        and evidence.source_identifier not in requirement.permitted_source_identifiers)
                    or not 0 <= evidence_age <= requirement.freshness_limit_seconds
                    or (requirement.require_verified_source and evidence.verification_status.value != "VERIFIED")
                    or (requirement.require_integrity_verified and evidence.integrity_status.value != "VERIFIED")
                    or evidence.integrity_status.value == "FAILED"
                    or evidence.verification_status.value == "REJECTED"
                    or not conflict_resolved
                    or (requires_resolution and evidence.conflict_status.value != "CLEAR"
                        and not evidence.conflict_resolution_reference)
                    or now_ms > deadline_ms):
                continue
            freshness_slack = requirement.freshness_limit_seconds - evidence_age
            dependency_count = len(set(evidence.supports_requirements).intersection(decision.mandatory_evidence_requirements))
            eligible.append((deadline_ms, freshness_slack, -dependency_count,
                             evidence.payload_size_bytes, evidence.evidence_id))
    return eligible


def select_packet(ready: list[dict], strategy: ControllerStrategy, scenario: ECR5GScenario,
                  now_ms: float, *, promotion_count: int = 0,
                  consecutive_mandatory: int = 0) -> tuple[dict, bool, bool]:
    """Return next packet and whether ECAC used an evidence priority promotion."""
    if strategy == ControllerStrategy.FIFO_BASELINE:
        return min(ready, key=lambda item: (item["arrival_ms"], item["sequence"], item["flow_id"])), False, False
    flows = {flow.flow_id: flow for flow in scenario.traffic_flows}
    if strategy == ControllerStrategy.STATIC_QOS_BASELINE:
        packet = min(ready, key=lambda item: (STATIC_QOS_RANK[flows[item["flow_id"]].qos_class],
                                              item["arrival_ms"], item["sequence"], item["flow_id"]))
        return packet, False, False

    limits = scenario.ecac_policy_limits
    eligible_by_sequence = {packet["sequence"]: _eligible_dependencies(packet, scenario, now_ms) for packet in ready}
    can_promote = promotion_count < limits.max_priority_promotions
    mandatory_packets = [packet for packet in ready if eligible_by_sequence[packet["sequence"]]]
    non_mandatory_packets = [packet for packet in ready if not eligible_by_sequence[packet["sequence"]]]
    if (limits.mandatory_preempts_optional and mandatory_packets
            and consecutive_mandatory >= limits.max_consecutive_mandatory_messages
            and non_mandatory_packets):
        packet = min(non_mandatory_packets, key=lambda item: (item["arrival_ms"], item["sequence"], item["flow_id"]))
        return packet, False, bool(eligible_by_sequence[packet["sequence"]])

    def ecac_key(packet: dict) -> tuple:
        flow = flows[packet["flow_id"]]
        dependencies = eligible_by_sequence[packet["sequence"]]
        if dependencies and limits.mandatory_preempts_optional:
            deadline, freshness, dependency_count, payload_size, _ = min(dependencies)
            tier = 0
        else:
            deadline, freshness, dependency_count, payload_size = item_deadline(flow, scenario), float("inf"), 0, packet["payload_bytes"]
            tier = STATIC_QOS_RANK[flow.qos_class] - (1 if dependencies and can_promote else 0)
        return (tier, deadline, freshness, dependency_count, payload_size,
                item_deadline(flow, scenario), packet["arrival_ms"], packet["sequence"], packet["flow_id"])

    selected = min(ready, key=ecac_key)
    promoted = bool(eligible_by_sequence[selected["sequence"]] and can_promote
                    and STATIC_QOS_RANK[flows[selected["flow_id"]].qos_class] > 0)
    return selected, promoted, bool(eligible_by_sequence[selected["sequence"]])


def item_deadline(flow, scenario: ECR5GScenario) -> float:
    return (flow.deadline_utc - scenario.simulation_epoch_utc).total_seconds() * 1000
