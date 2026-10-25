from __future__ import annotations
from typing import List, Dict, Optional, Any
from .models import (
    NetworkProfileType,
    ImpairmentType,
    SimulationResult,
    TelemetrySample,
    SLO_PROFILES,
    HealthStatus,
)
from .slo_evaluator import SLOEvaluator
from .anomaly_detector import NetworkAnomalyDetector
from .simulator import NetworkSimulator5G


class TelemetryEngine5G:
    """
    Central 5G Communication Reliability & Performance Testing Engine for NetraSetu.
    Provides deterministic metric evaluation, simulated impairment stress testing,
    and rule-based SLO verification.

    NO LLMs are used in any live monitoring, prediction, failure-detection,
    or recovery-decision path.
    """

    def __init__(self):
        self.simulator = NetworkSimulator5G()
        self.evaluators: Dict[NetworkProfileType, SLOEvaluator] = {
            p: SLOEvaluator(p) for p in NetworkProfileType
        }
        self.anomaly_detector = NetworkAnomalyDetector()

    def run_impairment_test(
        self,
        profile_name: str = "URLLC",
        impairments: Optional[List[str]] = None,
        num_samples: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute simulated impairment test and return full benchmark payload.
        """
        # Map string profile to enum
        try:
            profile = NetworkProfileType(profile_name)
        except ValueError:
            profile = NetworkProfileType.URLLC

        # Map string impairments to enums
        mapped_impairments: List[ImpairmentType] = []
        if impairments:
            for imp in impairments:
                try:
                    mapped_impairments.append(ImpairmentType(imp.upper()))
                except ValueError:
                    continue

        sim_result = self.simulator.run_simulation(
            profile=profile,
            impairments=mapped_impairments,
            num_samples=num_samples,
        )

        return {
            "simulation_id": sim_result.simulation_id,
            "profile": sim_result.profile,
            "impairments_applied": sim_result.impairments_applied,
            "total_samples": sim_result.total_samples,
            "latency_report": sim_result.latency_report,
            "delivery_success_rate": sim_result.delivery_success_rate,
            "tail_latency_p95_ms": sim_result.tail_latency_p95_ms,
            "tail_latency_p99_ms": sim_result.tail_latency_p99_ms,
            "average_latency_ms": sim_result.average_latency_ms,
            "max_latency_ms": sim_result.max_latency_ms,
            "packet_loss_pct": sim_result.packet_loss_pct,
            "recovery_time_ms": sim_result.recovery_time_ms,
            "simulated_post_impairment_interval_ms": sim_result.recovery_time_ms,
            "recovery_time_semantics": {
                "name": "simulated_post_impairment_interval_ms",
                "method": "Synthetic elapsed interval from modeled impairment window to first healthy generated sample.",
                "actual_restoration": False,
            },
            "total_anomalies_detected": sim_result.total_anomalies_detected,
            "false_alarms_count": sim_result.false_alarms_count,
            "resource_overhead_pct": sim_result.resource_overhead_pct,
            "slo_compliance_status": sim_result.slo_compliance_status,
            "violations": sim_result.violations,
            "recommended_recovery": [
                {
                    "action_id": r.action_id,
                    "action_type": r.action_type,
                    "trigger_rule": r.trigger_rule,
                    "target_metric": r.target_metric,
                    "expected_recovery_ms": r.expected_recovery_ms,
                    "execution_status": r.execution_status,
                }
                for r in sim_result.recommended_recovery
            ],
            "provenance": sim_result.provenance,
        }

    def analyze_scenario_telemetry(self, scenario_text: str) -> Dict[str, Any]:
        """
        Deterministic, rule-based network and SLO analysis of a given scenario query.
        Replaces legacy LLM-based network agents with deterministic network telemetry logic.
        """
        text_lower = scenario_text.lower()

        # Deterministic profile classification
        if any(k in text_lower for k in ["critical", "power grid", "telecom infrastructure", "substation"]):
            profile = NetworkProfileType.CRITICAL_INFRA
        elif any(k in text_lower for k in ["urllc", "low latency", "telemetry", "drone", "remote surgery", "autonomous"]):
            profile = NetworkProfileType.URLLC
        elif any(k in text_lower for k in ["sensor", "meter", "iot", "massive", "mmtc"]):
            profile = NetworkProfileType.MMTC
        else:
            profile = NetworkProfileType.EMBB

        # Detect simulated impairment triggers from query keywords
        detected_impairments: List[ImpairmentType] = []
        if any(k in text_lower for k in ["latency", "delay", "lag", "rtt"]):
            detected_impairments.append(ImpairmentType.LATENCY_SPIKE)
        if any(k in text_lower for k in ["loss", "drop", "fading", "packet"]):
            detected_impairments.append(ImpairmentType.PACKET_LOSS)
        if any(k in text_lower for k in ["congestion", "buffer", "overload", "queue"]):
            detected_impairments.append(ImpairmentType.CONGESTION)
        if any(k in text_lower for k in ["handover", "mobility", "roaming", "cell switch"]):
            detected_impairments.append(ImpairmentType.HANDOVER_DISRUPTION)
        if any(k in text_lower for k in ["failure", "outage", "link drop", "disconnect"]):
            detected_impairments.append(ImpairmentType.LINK_FAILURE)

        # Run deterministic simulation test
        sim_data = self.run_impairment_test(
            profile_name=profile.value,
            impairments=[imp.value for imp in detected_impairments],
            num_samples=100,
        )

        return {
            "status": "success",
            "analysis_type": "DETERMINISTIC_5G_NETWORK_TELEMETRY",
            "llm_used": False,
            "target_profile": profile.value,
            "detected_impairments": [imp.value for imp in detected_impairments],
            "telemetry_metrics": {
                "delivery_success_rate": sim_data["delivery_success_rate"],
                "tail_latency_p95_ms": sim_data["tail_latency_p95_ms"],
                "tail_latency_p99_ms": sim_data["tail_latency_p99_ms"],
                "average_latency_ms": sim_data["average_latency_ms"],
                "recovery_time_ms": sim_data["recovery_time_ms"],
                "simulated_post_impairment_interval_ms": sim_data["simulated_post_impairment_interval_ms"],
                "resource_overhead_pct": sim_data["resource_overhead_pct"],
            },
            "slo_compliance_status": sim_data["slo_compliance_status"],
            "violations": sim_data["violations"],
            "recovery_actions": sim_data["recommended_recovery"],
            "provenance": sim_data["provenance"],
        }


# Global singleton instance
_engine_instance: Optional[TelemetryEngine5G] = None

def get_5g_telemetry_engine() -> TelemetryEngine5G:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TelemetryEngine5G()
    return _engine_instance
