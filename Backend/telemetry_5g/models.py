from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class NetworkProfileType(str, Enum):
    URLLC = "URLLC"                     # Ultra-Reliable Low-Latency Communication
    EMBB = "eMBB"                       # Enhanced Mobile Broadband
    MMTC = "mMTC"                       # Massive Machine-Type Communication
    CRITICAL_INFRA = "CRITICAL_INFRA"   # Critical Telecommunication Infrastructure


class ImpairmentType(str, Enum):
    LATENCY_SPIKE = "LATENCY_SPIKE"
    PACKET_LOSS = "PACKET_LOSS"
    CONGESTION = "CONGESTION"
    HANDOVER_DISRUPTION = "HANDOVER_DISRUPTION"
    LINK_FAILURE = "LINK_FAILURE"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    VIOLATING = "VIOLATING"


@dataclass
class TelemetrySample:
    timestamp: float
    latency_ms: float
    jitter_ms: float
    packet_loss_rate: float            # 0.0 to 1.0
    throughput_mbps: float
    queue_depth_pkts: int
    rtt_ms: float
    gnb_id: str
    active_slice: str
    is_simulated: bool = True
    provenance: str = "SIMULATED_TESTBED_ENGINE"


@dataclass
class SLOTargets:
    profile: NetworkProfileType
    max_latency_ms: float
    max_jitter_ms: float
    max_packet_loss_rate: float
    min_throughput_mbps: float
    max_handover_interruption_ms: float
    max_recovery_time_ms: float


# Standard 3GPP Release 17/18 and DoT Critical Infrastructure SLO baselines
SLO_PROFILES: Dict[NetworkProfileType, SLOTargets] = {
    NetworkProfileType.URLLC: SLOTargets(
        profile=NetworkProfileType.URLLC,
        max_latency_ms=5.0,
        max_jitter_ms=1.0,
        max_packet_loss_rate=0.00001,  # 99.999% reliability
        min_throughput_mbps=10.0,
        max_handover_interruption_ms=10.0,
        max_recovery_time_ms=50.0,
    ),
    NetworkProfileType.EMBB: SLOTargets(
        profile=NetworkProfileType.EMBB,
        max_latency_ms=20.0,
        max_jitter_ms=5.0,
        max_packet_loss_rate=0.001,    # 99.9% reliability
        min_throughput_mbps=100.0,
        max_handover_interruption_ms=50.0,
        max_recovery_time_ms=200.0,
    ),
    NetworkProfileType.MMTC: SLOTargets(
        profile=NetworkProfileType.MMTC,
        max_latency_ms=100.0,
        max_jitter_ms=20.0,
        max_packet_loss_rate=0.01,     # 99% reliability
        min_throughput_mbps=1.0,
        max_handover_interruption_ms=200.0,
        max_recovery_time_ms=1000.0,
    ),
    NetworkProfileType.CRITICAL_INFRA: SLOTargets(
        profile=NetworkProfileType.CRITICAL_INFRA,
        max_latency_ms=2.0,
        max_jitter_ms=0.5,
        max_packet_loss_rate=0.000001, # 99.9999% reliability
        min_throughput_mbps=25.0,
        max_handover_interruption_ms=5.0,
        max_recovery_time_ms=25.0,
    ),
}


@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float               # 0.0 to 1.0 normalized
    metric_name: str
    observed_value: float
    threshold_value: float
    detector_algorithm: str            # e.g., 'EWMA_ZSCORE', 'LIGHTGBM', 'XGBOOST'
    false_alarm_flag: bool = False


@dataclass
class RecoveryAction:
    action_id: str
    action_type: str                   # e.g., 'DUAL_CONNECTIVITY_SPLIT', 'REROUTE_SECONDARY_PATH', 'QOS_REPRIORITIZATION'
    trigger_rule: str
    target_metric: str
    expected_recovery_ms: float
    execution_status: str              # 'DETERMINISTIC_TRIGGERED', 'EXECUTED', 'NO_ACTION_REQUIRED'


@dataclass
class SimulationResult:
    simulation_id: str
    profile: str
    impairments_applied: List[str]
    total_samples: int
    delivery_success_rate: float       # Percentage 0.0 - 100.0
    tail_latency_p95_ms: float
    tail_latency_p99_ms: float
    average_latency_ms: float
    max_latency_ms: float
    packet_loss_pct: float
    recovery_time_ms: float
    total_anomalies_detected: int
    false_alarms_count: int
    resource_overhead_pct: float
    slo_compliance_status: str         # 'COMPLIANT', 'DEGRADED', 'VIOLATED'
    violations: List[str]
    recommended_recovery: List[RecoveryAction]
    provenance: Dict[str, Any] = field(default_factory=lambda: {
        "source": "SIMULATION",
        "is_simulated": True,
        "real_testbed": False,
        "engine": "NetraSetu Deterministic 5G Telemetry & Simulation Engine v1.0",
        "llm_in_decision_loop": False,
    })
    latency_report: Dict[str, Any] = field(default_factory=dict)
