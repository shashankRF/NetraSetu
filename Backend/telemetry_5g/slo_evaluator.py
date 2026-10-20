from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from .models import (
    NetworkProfileType,
    SLOTargets,
    SLO_PROFILES,
    TelemetrySample,
    HealthStatus,
    RecoveryAction,
)


class SLOEvaluator:
    """
    Deterministic rule-based evaluator for 5G network telemetry against
    service-level objectives (SLOs) defined in 3GPP and DoT Critical Infrastructure norms.

    NO LLMs are used in this path. All decisions are deterministic, auditable, and repeatable.
    """

    def __init__(self, profile: NetworkProfileType = NetworkProfileType.URLLC):
        self.profile = profile
        self.targets = SLO_PROFILES.get(profile, SLO_PROFILES[NetworkProfileType.URLLC])

    def evaluate_sample(self, sample: TelemetrySample) -> Tuple[HealthStatus, List[str]]:
        """
        Evaluate a single telemetry sample against the configured SLO targets.
        """
        violations: List[str] = []

        if sample.latency_ms > self.targets.max_latency_ms:
            violations.append(
                f"Latency violation: {sample.latency_ms:.2f}ms exceeds target {self.targets.max_latency_ms:.2f}ms"
            )

        if sample.jitter_ms > self.targets.max_jitter_ms:
            violations.append(
                f"Jitter violation: {sample.jitter_ms:.2f}ms exceeds target {self.targets.max_jitter_ms:.2f}ms"
            )

        if sample.packet_loss_rate > self.targets.max_packet_loss_rate:
            violations.append(
                f"Packet loss violation: {sample.packet_loss_rate:.5f} exceeds target {self.targets.max_packet_loss_rate:.5f}"
            )

        if sample.throughput_mbps < self.targets.min_throughput_mbps:
            violations.append(
                f"Throughput shortfall: {sample.throughput_mbps:.1f}Mbps below target {self.targets.min_throughput_mbps:.1f}Mbps"
            )

        if not violations:
            return HealthStatus.HEALTHY, []
        elif len(violations) == 1 and sample.latency_ms <= self.targets.max_latency_ms * 1.2:
            return HealthStatus.DEGRADED, violations
        else:
            return HealthStatus.VIOLATING, violations

    def determine_deterministic_recovery(
        self,
        samples: List[TelemetrySample],
        violations: List[str],
    ) -> List[RecoveryAction]:
        """
        Determine deterministic, rule-based recovery actions without any LLM in the loop.
        Actions map directly to 3GPP Rel-16/17 and TEC standard mechanisms.
        """
        if not samples or not violations:
            return []

        recent = samples[-1]
        actions: List[RecoveryAction] = []

        # Rule 1: High Latency or Jitter in URLLC -> Trigger Dual Connectivity (DC) Packet Duplication
        if any("Latency" in v or "Jitter" in v for v in violations):
            actions.append(
                RecoveryAction(
                    action_id="REC-DC-DUP-01",
                    action_type="DUAL_CONNECTIVITY_PACKET_DUPLICATION",
                    trigger_rule="IF latency > target OR jitter > target THEN activate PDCP duplication over secondary cell group (3GPP TS 37.340)",
                    target_metric="latency_ms",
                    expected_recovery_ms=12.5,
                    execution_status="DETERMINISTIC_TRIGGERED",
                )
            )

        # Rule 2: Packet Loss Surge -> Activate Grant-Free Autonomous Transmission with RLC AM
        if any("Packet loss" in v for v in violations):
            actions.append(
                RecoveryAction(
                    action_id="REC-RLC-AM-02",
                    action_type="RLC_AM_RETRANSMISSION_BOOST",
                    trigger_rule="IF packet_loss_rate > target THEN shift slice to RLC Acknowledged Mode with Grant-Free Uplink repetition (3GPP TS 38.322)",
                    target_metric="packet_loss_rate",
                    expected_recovery_ms=18.0,
                    execution_status="DETERMINISTIC_TRIGGERED",
                )
            )

        # Rule 3: Buffer / Queue Congestion -> Active Queue Management (CoDel / ECN)
        if recent.queue_depth_pkts > 150:
            actions.append(
                RecoveryAction(
                    action_id="REC-AQM-ECN-03",
                    action_type="AQM_CODEL_CONGESTION_BACKOFF",
                    trigger_rule="IF queue_depth > 150 pkts THEN trigger CoDel packet drop on low-priority slices and signal ECN to gNB scheduler",
                    target_metric="queue_depth_pkts",
                    expected_recovery_ms=8.0,
                    execution_status="DETERMINISTIC_TRIGGERED",
                )
            )

        # Rule 4: Throughput Shortfall -> Dynamic PRB Slice Expansion
        if any("Throughput shortfall" in v for v in violations):
            actions.append(
                RecoveryAction(
                    action_id="REC-PRB-ALLOC-04",
                    action_type="DYNAMIC_PRB_QUOTA_EXPANSION",
                    trigger_rule="IF throughput < target THEN reallocate unused PRBs from best-effort eMBB slice to critical telemetry slice (3GPP TS 28.530)",
                    target_metric="throughput_mbps",
                    expected_recovery_ms=22.0,
                    execution_status="DETERMINISTIC_TRIGGERED",
                )
            )

        return actions
