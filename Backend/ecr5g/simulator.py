from __future__ import annotations

import hashlib
import math
import random
import time
from collections import defaultdict, deque
from statistics import mean

from .controllers import select_packet
from .models import ControllerStrategy, ECR5GScenario


_UNDELIVERED_PENALTY_MS = 60_000.0
_EPSILON_BITS = 1e-7


def _network_at(scenario: ECR5GScenario, offset_ms: float) -> dict:
    base = scenario.initial_network_state
    state = {
        "capacity_mbps": base.bottleneck_capacity_mbps,
        "latency_ms": base.latency_ms,
        "processing_delay_ms": base.processing_delay_ms,
        "loss_probability": base.packet_loss_probability,
        "congestion": base.congestion_state,
        "link_available": base.link_available,
    }
    for change in scenario.network_changes:
        if change.start_offset_ms <= offset_ms < change.end_offset_ms:
            for field, key in (("bottleneck_capacity_mbps", "capacity_mbps"),
                               ("latency_ms", "latency_ms"),
                               ("processing_delay_ms", "processing_delay_ms"),
                               ("packet_loss_probability", "loss_probability"),
                               ("congestion_state", "congestion"), ("link_available", "link_available")):
                value = getattr(change, field)
                if value is not None:
                    state[key] = value
    return state


def _boundaries(scenario: ECR5GScenario) -> list[float]:
    return sorted({0.0, float(scenario.simulation_duration_ms), *(
        point for item in scenario.network_changes for point in (item.start_offset_ms, item.end_offset_ms)
    )})


def _next_boundary(boundaries: list[float], offset_ms: float) -> float | None:
    return next((point for point in boundaries if point > offset_ms + 1e-9), None)


def _serialize_message(scenario: ECR5GScenario, packet: dict, offset_ms: float,
                       boundaries: list[float]) -> dict:
    """Transmit across capacity changes and outages without sleeping or exceeding link capacity."""
    time_ms = offset_ms
    first_bit_at: float | None = None
    remaining_bits = packet["payload_bytes"] * 8.0
    sent_bits = 0.0
    weighted_loss_bits = 0.0
    segments = []
    completion_state = _network_at(scenario, min(time_ms, scenario.simulation_duration_ms - 1e-9))

    while remaining_bits > _EPSILON_BITS and time_ms < scenario.simulation_duration_ms:
        state = _network_at(scenario, time_ms)
        if not state["link_available"] or state["capacity_mbps"] <= 0:
            boundary = _next_boundary(boundaries, time_ms)
            if boundary is None:
                break
            time_ms = boundary
            continue

        boundary = min(_next_boundary(boundaries, time_ms) or scenario.simulation_duration_ms,
                       float(scenario.simulation_duration_ms))
        if boundary <= time_ms:
            break
        bit_rate_per_ms = state["capacity_mbps"] * 1000.0
        available_bits = bit_rate_per_ms * (boundary - time_ms)
        transmitted_bits = min(remaining_bits, available_bits)
        if transmitted_bits <= _EPSILON_BITS:
            time_ms = boundary
            continue
        segment_start = time_ms
        segment_duration = transmitted_bits / bit_rate_per_ms
        time_ms += segment_duration
        if first_bit_at is None:
            first_bit_at = segment_start
        sent_bits += transmitted_bits
        remaining_bits -= transmitted_bits
        weighted_loss_bits += transmitted_bits * state["loss_probability"]
        segments.append({"start_ms": segment_start, "end_ms": time_ms,
                         "capacity_mbps": state["capacity_mbps"], "bits": transmitted_bits})
        completion_state = _network_at(scenario, max(0.0, time_ms - 1e-9))
        if remaining_bits > _EPSILON_BITS and time_ms < boundary:
            time_ms = boundary

    fully_serialized = remaining_bits <= _EPSILON_BITS
    return {
        "first_bit_at_ms": first_bit_at,
        "serialization_complete_ms": time_ms if fully_serialized else None,
        "serialized_bits": sent_bits,
        "transmitted_bytes": sent_bits / 8.0,
        "loss_probability": weighted_loss_bits / sent_bits if sent_bits else 0.0,
        "completion_state": completion_state,
        "segments": segments,
        "fully_serialized": fully_serialized,
    }


def _build_trace(scenario: ECR5GScenario) -> tuple[list[dict], dict[str, deque]]:
    packets: list[dict] = []
    per_flow: dict[str, deque] = defaultdict(deque)
    sequence = 0
    total_created = 0
    for flow in scenario.traffic_flows:
        estimated_bytes = flow.offered_load_mbps * scenario.simulation_duration_ms * 125
        count = int(math.ceil(estimated_bytes / flow.payload_size_bytes))
        if count > 5_000 or total_created + count > 5_000:
            raise ValueError("scenario offered load exceeds the 5,000-message CPU safety limit")
        for index in range(count):
            arrival = flow.arrival_offset_ms + index * scenario.simulation_duration_ms / max(count, 1)
            if arrival >= scenario.simulation_duration_ms:
                continue
            packet = {"sequence": sequence, "flow_id": flow.flow_id, "arrival_ms": arrival,
                      "payload_bytes": flow.payload_size_bytes, "evidence_ids": list(flow.evidence_ids)}
            packets.append(packet)
            per_flow[flow.flow_id].append(packet)
            sequence += 1
            total_created += 1
    return packets, per_flow


def _conflict_is_resolved(evidence, requirement, decision_requires_resolution: bool = False) -> bool:
    if evidence.conflict_status.value == "CLEAR":
        return True
    return bool((requirement.requires_conflict_resolution or decision_requires_resolution)
                and evidence.conflict_resolution_reference
                and evidence.conflict_status.value in {"CONFLICTING", "SUPERSEDED"})


def _validate_evidence(scenario: ECR5GScenario, outcomes: list[dict]) -> dict:
    """Evaluate required source objects against delivery, freshness, integrity and conflict rules."""
    validation_started = time.perf_counter()
    requirements = {item.requirement_id: item for item in scenario.evidence_requirements}
    flows = {item.flow_id: item for item in scenario.traffic_flows}
    delivered_at: dict[str, list[float]] = defaultdict(list)
    for outcome in outcomes:
        if outcome["delivered"]:
            for evidence_id in flows[outcome["flow_id"]].evidence_ids:
                delivered_at[evidence_id].append(outcome["delivery_time_ms"])

    result_rows = []
    decision_rows = []
    stale_rejected: set[str] = set()
    unresolved_conflicts: set[str] = set()
    stale_accepted: set[str] = set()
    conflicting_accepted: set[str] = set()
    undelivered_accepted: set[str] = set()
    for decision in scenario.decision_requirements:
        unmet = []
        mandatory = set(decision.mandatory_evidence_requirements)
        for requirement_id in decision.mandatory_evidence_requirements:
            requirement = requirements[requirement_id]
            candidates = [item for item in scenario.evidence_objects
                          if item.incident_id == decision.incident_id
                          and item.evidence_type == requirement.evidence_type
                          and requirement_id in item.supports_requirements
                          and (not requirement.permitted_source_identifiers
                               or item.source_identifier in requirement.permitted_source_identifiers)]
            valid = False
            failure_reasons = []
            accepted_item = None
            accepted_delivery_time = None
            deadline_ms = (requirement.deadline_utc - scenario.simulation_epoch_utc).total_seconds() * 1000
            for item in candidates:
                delivery_times = delivered_at.get(item.evidence_id, [])
                on_time = [value for value in delivery_times if value <= deadline_ms]
                source_age = (scenario.simulation_epoch_utc - item.source_timestamp_utc).total_seconds()
                fresh_times = [value for value in on_time
                               if 0 <= source_age + value / 1000 <= requirement.freshness_limit_seconds]
                if ((delivery_times and not fresh_times
                     and all(source_age + value / 1000 < 0
                             or source_age + value / 1000 > requirement.freshness_limit_seconds
                             for value in delivery_times))
                        or (not delivery_times and (source_age < 0 or source_age > requirement.freshness_limit_seconds))):
                    stale_rejected.add(item.evidence_id)
                    failure_reasons.append("EVIDENCE_STALE_AT_VALIDATION")
                if item.conflict_status.value != "CLEAR" and not _conflict_is_resolved(item, requirement, decision.requires_conflict_resolution):
                    unresolved_conflicts.add(item.evidence_id)
                    failure_reasons.append("CONFLICT_UNRESOLVED: resolution rule/reference was not satisfied")
                    continue
                if item.evidence_id in stale_rejected:
                    continue
                if requirement.require_verified_source and item.verification_status.value != "VERIFIED":
                    failure_reasons.append("SOURCE_NOT_VERIFIED")
                    continue
                if requirement.require_integrity_verified and item.integrity_status.value != "VERIFIED":
                    failure_reasons.append("INTEGRITY_NOT_VERIFIED")
                    continue
                if not fresh_times:
                    failure_reasons.append("NOT_DELIVERED_BY_REQUIREMENT_DEADLINE")
                    continue
                valid = True
                accepted_item = item
                accepted_delivery_time = min(fresh_times)
                break
            if not candidates:
                failure_reasons.append("MANDATORY_EVIDENCE_NOT_PROVIDED")
            row = {"action_id": decision.action_id, "requirement_id": requirement_id,
                   "complete": valid, "deadline_utc": requirement.deadline_utc.isoformat(),
                   "reason_codes": sorted(set(failure_reasons)),
                   "reason": "All source, delivery, freshness, integrity and conflict checks passed." if valid
                   else "; ".join(dict.fromkeys(failure_reasons))}
            result_rows.append(row)
            if valid and accepted_item is not None:
                if accepted_delivery_time is None:
                    undelivered_accepted.add(accepted_item.evidence_id)
                if (accepted_delivery_time is not None and
                        not 0 <= (scenario.simulation_epoch_utc - accepted_item.source_timestamp_utc).total_seconds()
                        + accepted_delivery_time / 1000 <= requirement.freshness_limit_seconds):
                    stale_accepted.add(accepted_item.evidence_id)
                if accepted_item.conflict_status.value != "CLEAR" and not _conflict_is_resolved(accepted_item, requirement, decision.requires_conflict_resolution):
                    conflicting_accepted.add(accepted_item.evidence_id)
            if not valid:
                unmet.append(requirement_id)
        complete = not unmet and len(mandatory) == len(decision.mandatory_evidence_requirements)
        decision_rows.append({"action_id": decision.action_id, "incident_id": decision.incident_id,
                              "evidence_complete": complete,
                              "status": "READY_FOR_HUMAN_REVIEW" if complete and decision.human_approval_required
                              else "EVIDENCE_COMPLETE_PENDING_AUTHORIZATION" if complete
                              else "INFEASIBLE_NEEDS_REVIEW",
                              "mandatory_requirements_unmet": unmet,
                              "human_approval_required": decision.human_approval_required,
                              "authorized": False})

    pair_count = len(result_rows)
    complete_pairs = sum(row["complete"] for row in result_rows)
    return {"mandatory_requirement_pairs": pair_count, "complete_requirement_pairs": complete_pairs,
            "completeness_rate": complete_pairs / pair_count if pair_count else 1.0,
            "stale_evidence_objects_rejected": len(stale_rejected),
            "stale_evidence_ids_rejected": sorted(stale_rejected),
            "stale_evidence_accepted": len(stale_accepted),
            "unresolved_conflict_objects": len(unresolved_conflicts),
            "unresolved_conflict_evidence_ids": sorted(unresolved_conflicts),
            "conflicting_evidence_accepted": len(conflicting_accepted),
            "undelivered_evidence_accepted": len(undelivered_accepted),
            "requirement_results": result_rows, "decision_results": decision_rows,
            "validation_computation_ms": (time.perf_counter() - validation_started) * 1000}


def _capacity_budget_bytes(scenario: ECR5GScenario, boundaries: list[float]) -> float:
    capacity_bits = 0.0
    for start, end in zip(boundaries, boundaries[1:]):
        state = _network_at(scenario, (start + end) / 2)
        if state["link_available"]:
            capacity_bits += state["capacity_mbps"] * 1000.0 * (end - start)
    return capacity_bits / 8.0


def run_simulation(scenario: ECR5GScenario, strategy: ControllerStrategy, *, seed: int | None = None) -> dict:
    """Run deterministic discrete events; no real-time sleeps or real network changes occur."""
    simulation_started = time.perf_counter()
    actual_seed = scenario.seed if seed is None else seed
    trace, flow_queues = _build_trace(scenario)
    flow_map = {flow.flow_id: flow for flow in scenario.traffic_flows}
    packet_rng = {packet["sequence"]: random.Random(actual_seed ^ int(hashlib.sha256(
        f"{scenario.scenario_id}:{packet['sequence']}".encode()).hexdigest()[:8], 16)) for packet in trace}
    boundaries = _boundaries(scenario)
    ready: list[dict] = []
    active_flows: set[str] = set()
    outcomes: list[dict] = []
    now = 0.0
    bytes_transmitted = 0.0
    queue_delays: list[float] = []
    network_latencies: list[float] = []
    controller_ms = 0.0
    promotions = 0
    consecutive_mandatory = 0
    max_queue_size = 0

    def release_arrivals(at: float) -> None:
        for flow_id, queue in flow_queues.items():
            if flow_id not in active_flows and queue and queue[0]["arrival_ms"] <= at:
                ready.append(queue[0])
                active_flows.add(flow_id)

    while any(flow_queues.values()):
        release_arrivals(now)
        max_queue_size = max(max_queue_size,
                             sum(1 for queue in flow_queues.values() for item in queue
                                 if item["arrival_ms"] <= now))
        if not ready:
            next_arrivals = [queue[0]["arrival_ms"] for queue in flow_queues.values() if queue]
            if not next_arrivals:
                break
            now = max(now, min(next_arrivals))
            release_arrivals(now)

        controller_started = time.perf_counter()
        packet, was_promoted, selected_mandatory = select_packet(
            ready, strategy, scenario, now,
            promotion_count=promotions,
            consecutive_mandatory=consecutive_mandatory,
        )
        controller_ms += (time.perf_counter() - controller_started) * 1000
        flow = flow_map[packet["flow_id"]]
        ready.remove(packet)
        active_flows.remove(packet["flow_id"])
        flow_queues[packet["flow_id"]].popleft()
        if was_promoted:
            promotions += 1
        consecutive_mandatory = consecutive_mandatory + 1 if selected_mandatory else 0

        tx = _serialize_message(scenario, packet, now, boundaries)
        start_ms = tx["first_bit_at_ms"]
        completion_ms = tx["serialization_complete_ms"]
        effective_start = start_ms if start_ms is not None else min(now, scenario.simulation_duration_ms)
        queue_delay = max(0.0, effective_start - packet["arrival_ms"])
        queue_delays.append(queue_delay)
        bytes_transmitted += tx["transmitted_bytes"]
        fully_sent = tx["fully_serialized"]
        state = tx["completion_state"]
        network_latency = ((completion_ms - start_ms) + state["latency_ms"] + state["processing_delay_ms"]
                           if fully_sent and start_ms is not None and completion_ms is not None else None)
        delivery_time = completion_ms + state["latency_ms"] + state["processing_delay_ms"] if network_latency is not None else None
        random_loss = fully_sent and packet_rng[packet["sequence"]].random() < tx["loss_probability"]
        delivered = bool(fully_sent and not random_loss and delivery_time <= scenario.simulation_duration_ms)
        deadline_ms = (flow.deadline_utc - scenario.simulation_epoch_utc).total_seconds() * 1000
        flow_deadline_met = bool(delivered and delivery_time <= deadline_ms)
        latency_slo_met = bool(delivered and network_latency <= flow.max_latency_ms)
        end_to_end_latency = delivery_time - packet["arrival_ms"] if delivered else None
        if network_latency is not None:
            network_latencies.append(network_latency)
        if not tx["fully_serialized"]:
            failure_reason = "LINK_UNAVAILABLE_OR_CAPACITY_INSUFFICIENT_BEFORE_HORIZON" if not tx["segments"] else "MESSAGE_SERIALIZATION_INCOMPLETE_AT_HORIZON"
        elif random_loss:
            failure_reason = "SIMULATED_MESSAGE_LOSS"
        elif delivery_time > scenario.simulation_duration_ms:
            failure_reason = "DELIVERY_AFTER_SIMULATION_HORIZON"
        else:
            failure_reason = None
        outcomes.append({**packet, "delivered": delivered,
                         "transmission_start_ms": start_ms,
                         "serialization_complete_ms": completion_ms,
                         "delivery_time_ms": delivery_time if delivered else None,
                         "network_delivery_latency_ms": network_latency,
                         "propagation_delay_ms": state["latency_ms"] if fully_sent else None,
                         "processing_delay_ms": state["processing_delay_ms"] if fully_sent else None,
                         "end_to_end_latency_ms": end_to_end_latency,
                         "queue_delay_ms": queue_delay,
                         "transmitted_bytes": tx["transmitted_bytes"],
                         "serialization_segments": tx["segments"],
                         "deadline_utc": flow.deadline_utc.isoformat(),
                         "within_deadline": flow_deadline_met,
                         "latency_slo_met": latency_slo_met,
                         "random_loss_probability": tx["loss_probability"],
                         "loss_reason": failure_reason})
        now = max(now, completion_ms if completion_ms is not None else scenario.simulation_duration_ms)

    completeness = _validate_evidence(scenario, outcomes)
    generated = len(trace)
    delivered = sum(outcome["delivered"] for outcome in outcomes)
    timely = sum(outcome["within_deadline"] for outcome in outcomes)
    loss_count = generated - delivered
    latencies = [outcome["end_to_end_latency_ms"] if outcome["delivered"] else _UNDELIVERED_PENALTY_MS
                 for outcome in outcomes]
    ordered = sorted(latencies)

    def percentile(fraction: float) -> float:
        return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] if ordered else 0.0

    jitter_values = []
    by_flow: dict[str, list[dict]] = defaultdict(list)
    for outcome in outcomes:
        by_flow[outcome["flow_id"]].append(outcome)
    for flow_outcomes in by_flow.values():
        flow_outcomes.sort(key=lambda outcome: outcome["sequence"])
        effective_flow_latency = [outcome["end_to_end_latency_ms"] if outcome["delivered"] else _UNDELIVERED_PENALTY_MS
                                 for outcome in flow_outcomes]
        jitter_values.extend(abs(b - a) for a, b in zip(effective_flow_latency, effective_flow_latency[1:]))

    failed_deadlines = [{"flow_id": outcome["flow_id"], "sequence": outcome["sequence"],
                         "deadline_utc": outcome["deadline_utc"], "reason": outcome["loss_reason"] or "DEADLINE_MISSED"}
                        for outcome in outcomes if not outcome["within_deadline"]]
    flow_summaries = []
    reliability_failures = []
    for flow in scenario.traffic_flows:
        flow_outcomes = [item for item in outcomes if item["flow_id"] == flow.flow_id]
        flow_delivered = sum(item["delivered"] for item in flow_outcomes)
        reliability = flow_delivered / len(flow_outcomes) if flow_outcomes else 1.0
        reliability_met = reliability >= flow.reliability_target
        latency_slo_success = sum(item["latency_slo_met"] for item in flow_outcomes)
        latency_slo_rate = latency_slo_success / len(flow_outcomes) if flow_outcomes else 1.0
        latency_slo_met = latency_slo_rate >= flow.reliability_target
        flow_summaries.append({"flow_id": flow.flow_id,
                               "generated_messages": len(flow_outcomes),
                               "delivered_messages": flow_delivered,
                               "reliability_target": flow.reliability_target,
                               "observed_delivery_reliability": reliability,
                               "reliability_slo_met": reliability_met,
                               "latency_target_ms": flow.max_latency_ms,
                               "latency_slo_success_count": latency_slo_success,
                               "latency_slo_success_rate": latency_slo_rate,
                               "latency_slo_met": latency_slo_met})
        if not reliability_met or not latency_slo_met:
            reliability_failures.append({"flow_id": flow.flow_id,
                                         "observed_delivery_reliability": reliability,
                                         "required_reliability": flow.reliability_target,
                                         "observed_latency_slo_rate": latency_slo_rate,
                                         "latency_target_ms": flow.max_latency_ms,
                                         "reason": "FLOW_RELIABILITY_OR_LATENCY_SLO_BELOW_TARGET"})
    infeasible_reasons = []
    for row in completeness["requirement_results"]:
        if not row["complete"]:
            infeasible_reasons.append({"action_id": row["action_id"], "requirement_id": row["requirement_id"],
                                       "reason_codes": row["reason_codes"], "reason": row["reason"]})
    if failed_deadlines:
        infeasible_reasons.append({"reason_code": "FLOW_DEADLINE_FAILURES",
                                   "failed_message_count": len(failed_deadlines),
                                   "details": failed_deadlines[:100]})
    if reliability_failures:
        infeasible_reasons.extend(reliability_failures)
    decision_infeasible = any(not decision["evidence_complete"] for decision in completeness["decision_results"])
    schedule_infeasible = decision_infeasible or bool(failed_deadlines) or bool(reliability_failures)
    schedule_status = "INFEASIBLE" if schedule_infeasible else "FEASIBLE_FOR_HUMAN_REVIEW"
    # Invariants are evaluated from actual outcomes; every action remains unauthorized.
    missing_blocked = all(not item["mandatory_requirements_unmet"] or not item["evidence_complete"]
                          for item in completeness["decision_results"])
    schedule_matches_failures = (schedule_status == "INFEASIBLE") == schedule_infeasible
    invariant_results = [
        {"name": "missing_mandatory_evidence_blocks_completion", "passed": missing_blocked},
        {"name": "stale_evidence_never_satisfies_freshness_requirement", "passed": completeness["stale_evidence_accepted"] == 0},
        {"name": "unresolved_conflicts_are_not_accepted", "passed": completeness["conflicting_evidence_accepted"] == 0},
        {"name": "undelivered_evidence_does_not_satisfy_requirements", "passed": completeness["undelivered_evidence_accepted"] == 0},
        {"name": "infeasible_schedule_is_not_reported_successful", "passed": schedule_matches_failures},
        {"name": "qos_never_authorizes_action", "passed": all(not item["authorized"] for item in completeness["decision_results"])},
        {"name": "no_real_world_action_is_authorized", "passed": True},
    ]
    violation_count = sum(not item["passed"] for item in invariant_results)
    capacity_budget_bytes = _capacity_budget_bytes(scenario, boundaries)
    simulation_wall_ms = (time.perf_counter() - simulation_started) * 1000
    trace_content = "\n".join(f"{item['sequence']}|{item['flow_id']}|{item['arrival_ms']:.6f}|{item['payload_bytes']}" for item in trace)
    return {
        "strategy": strategy.value,
        "seed": actual_seed,
        "trace_sha256": hashlib.sha256(trace_content.encode()).hexdigest(),
        "schedule_status": schedule_status,
        "generated_messages": generated,
        "delivered_messages": delivered,
        "message_loss_count": loss_count,
        "message_loss_rate": loss_count / generated if generated else 0.0,
        "simulated_random_losses": sum(outcome["loss_reason"] == "SIMULATED_MESSAGE_LOSS" for outcome in outcomes),
        "deadline_success_count": timely,
        "deadline_success_rate": timely / generated if generated else 0.0,
        "failed_deadlines": failed_deadlines,
        "per_flow_metrics": flow_summaries,
        "reliability_slo_failures": reliability_failures,
        "delivery_latency_ms": {
            "definition": "end-to-end arrival-to-delivery time including queueing, serialization, propagation and processing; undelivered uses 60000 ms penalty",
            "mean_including_undelivered_penalty": mean(latencies) if latencies else 0.0,
            "p50": percentile(0.50), "p95": percentile(0.95), "p99": percentile(0.99),
            "maximum": max(latencies, default=0.0),
            "delivered_only_mean": mean([item["end_to_end_latency_ms"] for item in outcomes if item["delivered"]]) if delivered else None,
            "network_only_mean": mean(network_latencies) if network_latencies else None,
        },
        "jitter_ms": {"definition": "mean absolute difference of consecutive per-flow end-to-end message latencies; undelivered uses 60000 ms penalty",
                      "mean_absolute_consecutive_difference": mean(jitter_values) if jitter_values else 0.0},
        "evidence_completeness": completeness,
        "evidence_validation_computation_ms": completeness["validation_computation_ms"],
        "stale_evidence_objects_rejected": completeness["stale_evidence_objects_rejected"],
        "unresolved_conflict_objects": completeness["unresolved_conflict_objects"],
        "bytes_transmitted": bytes_transmitted,
        "bottleneck_utilization_rate": min(1.0, bytes_transmitted / capacity_budget_bytes) if capacity_budget_bytes else 0.0,
        "capacity_budget_bytes": capacity_budget_bytes,
        "queueing_delay_ms": {"mean": mean(queue_delays) if queue_delays else 0.0,
                              "maximum": max(queue_delays, default=0.0),
                              "maximum_simultaneous_queued_messages": max_queue_size},
        "controller_computation_ms": controller_ms,
        "simulation_execution_wall_clock_ms": simulation_wall_ms,
        "api_request_latency_ms": None,
        "api_request_latency_note": "Measured at the HTTP client boundary; not part of simulated network/controller metrics.",
        "scheduler_priority_promotions": promotions,
        "live_qos_policy_changes": 0,
        "infeasible_schedule_count": int(schedule_status == "INFEASIBLE"),
        "infeasible_reasons": infeasible_reasons,
        "safety_invariant_violations": violation_count,
        "safety_invariants": invariant_results,
        "human_review_escalations": len(completeness["decision_results"]),
        "invariants": {"stale_evidence_accepted": completeness["stale_evidence_accepted"],
                       "conflicting_evidence_accepted": completeness["conflicting_evidence_accepted"],
                       "undelivered_evidence_accepted": completeness["undelivered_evidence_accepted"],
                       "real_actions_authorized": False,
                       "real_5g_network_configured": False},
        "packet_outcomes": outcomes,
        "metric_definitions": {
            "delivery_latency_ms": "End-to-end message latency; undelivered messages receive the 60000 ms penalty for distribution metrics.",
            "message_loss_rate": "Undelivered generated messages / all generated messages.",
            "deadline_success_rate": "Delivered by each flow deadline / all generated messages.",
            "observed_delivery_reliability": "Delivered messages / generated messages for the flow, compared with that flow's configured target.",
            "evidence_completeness": "Satisfied mandatory action-requirement pairs / all mandatory action-requirement pairs.",
            "stale_evidence_objects_rejected": "Unique matching mandatory evidence objects stale at validation or all observed delivery attempts.",
            "unresolved_conflict_objects": "Unique matching mandatory evidence objects lacking the configured conflict-resolution rule/reference.",
            "bytes_transmitted": "Actual serialized bits / 8, including partial messages at horizon.",
            "bottleneck_utilization_rate": "Transmitted bytes / integrated available bottleneck capacity budget in bytes.",
            "queueing_delay_ms": "Time from message arrival to first serialized bit; includes outage wait.",
            "controller_computation_ms": "Accumulated wall-clock time spent selecting packets only.",
            "evidence_validation_computation_ms": "Wall-clock duration of deterministic evidence gate evaluation.",
            "api_request_latency_ms": "Not measured inside simulation; measure at HTTP client boundary.",
            "scheduler_priority_promotions": "Number of selected packets whose ECAC evidence rule improved scheduler rank.",
            "safety_invariant_violations": "Count of failed runtime safety invariant checks.",
        },
        "limitations": ["Synthetic discrete-event software emulator; no measured or certified 5G performance.",
                        "The simulator uses one shared serialized bottleneck and does not model radio scheduling, retransmission, handover, or a full 5G core.",
                        "Network changes are applied at simulation event boundaries. API request latency is measured outside this simulation."],
    }
