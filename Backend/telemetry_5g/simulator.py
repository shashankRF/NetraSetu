from __future__ import annotations
import math
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from .models import (
    NetworkProfileType,
    ImpairmentType,
    TelemetrySample,
    SimulationResult,
    SLO_PROFILES,
    HealthStatus,
)
from .slo_evaluator import SLOEvaluator
from .anomaly_detector import NetworkAnomalyDetector


def linear_percentile(values: List[float], percentile: float) -> Optional[float]:
    """Return the linearly interpolated percentile (rank=(n-1)*p)."""
    if not values:
        return None
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")
    ordered = sorted(float(value) for value in values)
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


class NetworkSimulator5G:
    """
    Deterministic simulation engine for 5G communication reliability and impairment testing.
    Models latency, packet loss, congestion, handover disruption, and link failure.

    All outputs are explicitly labeled as SIMULATED to distinguish from real testbed measurements.
    NO LLMs are invoked in any prediction, detection, or recovery path.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.random = random.Random(seed)

    def generate_trace(
        self,
        profile: NetworkProfileType = NetworkProfileType.URLLC,
        impairments: Optional[List[ImpairmentType]] = None,
        num_samples: int = 100,
        sample_interval_ms: float = 10.0,
    ) -> List[TelemetrySample]:
        """
        Generate time-series telemetry samples under specified impairment conditions.
        """
        impairments = impairments or []
        samples: List[TelemetrySample] = []
        base_slo = SLO_PROFILES.get(profile, SLO_PROFILES[NetworkProfileType.URLLC])

        # Nominal baselines based on profile
        nominal_lat = base_slo.max_latency_ms * 0.4
        nominal_jitter = base_slo.max_jitter_ms * 0.3
        nominal_loss = 0.0
        nominal_throughput = base_slo.min_throughput_mbps * 1.5

        current_time = time.time()

        for i in range(num_samples):
            # Use a sample-local stream so paired baseline/failure runs with
            # the same seed share identical nominal noise. Adding an
            # impairment must not shift the random stream for later samples.
            sample_rng = random.Random(self.seed + i)
            latency_rng = random.Random(self.seed * 1000003 + i * 7 + 1)
            loss_rng = random.Random(self.seed * 1000003 + i * 7 + 2)
            congestion_rng = random.Random(self.seed * 1000003 + i * 7 + 3)
            t = current_time + (i * sample_interval_ms / 1000.0)

            # Baseline noise
            lat = nominal_lat + sample_rng.gauss(0, nominal_jitter * 0.2)
            jitter = nominal_jitter + sample_rng.uniform(-0.1, 0.1)
            loss = nominal_loss
            throughput = nominal_throughput + sample_rng.uniform(-1.0, 1.0)
            queue_depth = max(5, int(sample_rng.gauss(15, 3)))
            rtt = lat * 2.0

            # Apply impairments to middle section of trace (samples 30 to 65)
            is_impaired_window = 30 <= i <= 65

            if is_impaired_window:
                if ImpairmentType.LATENCY_SPIKE in impairments:
                    # Significant latency spike (e.g., bufferbloat or scheduling delay)
                    lat += latency_rng.uniform(15.0, 35.0)
                    jitter += latency_rng.uniform(3.0, 8.0)
                    rtt = lat * 2.1

                if ImpairmentType.PACKET_LOSS in impairments:
                    # Burst packet loss (e.g., deep fading or shadow obstacle)
                    loss = loss_rng.uniform(0.02, 0.08)

                if ImpairmentType.CONGESTION in impairments:
                    # Cell queue congestion
                    queue_depth += int(congestion_rng.uniform(180, 320))
                    lat += (queue_depth / 20.0)
                    throughput = max(1.0, throughput * 0.3)

                if ImpairmentType.HANDOVER_DISRUPTION in impairments:
                    # Handover interruption between gNB-101 and gNB-102
                    if 40 <= i <= 48:
                        lat += 45.0
                        loss = 0.15
                        jitter += 12.0

                if ImpairmentType.LINK_FAILURE in impairments:
                    # Temporary Radio Link Failure (RLF)
                    if 42 <= i <= 52:
                        lat = 250.0
                        loss = 1.0
                        throughput = 0.0

            # Guard positive values
            lat = max(0.5, lat)
            jitter = max(0.1, jitter)
            loss = min(1.0, max(0.0, loss))
            throughput = max(0.0, throughput)

            samples.append(
                TelemetrySample(
                    timestamp=t,
                    latency_ms=round(lat, 3),
                    jitter_ms=round(jitter, 3),
                    packet_loss_rate=round(loss, 5),
                    throughput_mbps=round(throughput, 2),
                    queue_depth_pkts=queue_depth,
                    rtt_ms=round(rtt, 3),
                    gnb_id="gNB-102" if i > 45 and ImpairmentType.HANDOVER_DISRUPTION in impairments else "gNB-101",
                    active_slice="SST-1-URLLC" if profile == NetworkProfileType.URLLC else "SST-2-eMBB",
                    is_simulated=True,
                    provenance="SIMULATED_TESTBED_ENGINE",
                )
            )

        return samples

    def run_simulation(
        self,
        profile: NetworkProfileType = NetworkProfileType.URLLC,
        impairments: Optional[List[ImpairmentType]] = None,
        num_samples: int = 100,
    ) -> SimulationResult:
        """
        Execute a complete simulated performance test run, measuring delivery success,
        tail latency (P95, P99), recovery time, false alarms, and SLO compliance.
        """
        impairments = impairments or []
        samples = self.generate_trace(profile, impairments, num_samples)

        evaluator = SLOEvaluator(profile)
        detector = NetworkAnomalyDetector()

        all_violations: List[str] = []
        latencies = [s.latency_ms for s in samples]
        losses = [s.packet_loss_rate for s in samples]

        # Keep legacy metric fields consistent with the documented report method.
        tail_p95 = linear_percentile(latencies, 95)
        tail_p99 = linear_percentile(latencies, 99)
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        sample_count = len(latencies)
        jitter_values = [float(sample.jitter_ms) for sample in samples]
        rtt_values = [float(sample.rtt_ms) for sample in samples]
        sample_times = [float(sample.timestamp) for sample in samples]
        intervals_ms = [max(0.0, (right - left) * 1000.0)
                        for left, right in zip(sample_times, sample_times[1:])]

        def describe_distribution(values: List[float]) -> Dict[str, Any]:
            mean = sum(values) / len(values) if values else None
            stddev = (math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
                      if values and mean is not None else None)
            return {
                "sample_count": len(values),
                "p50": linear_percentile(values, 50),
                "p90": linear_percentile(values, 90),
                "p95": linear_percentile(values, 95),
                "p99": linear_percentile(values, 99),
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
                "mean": mean,
                "population_standard_deviation": stddev,
            }

        delivered_ratio = 1.0 - (sum(losses) / len(losses))
        delivery_success_pct = round(max(0.0, delivered_ratio * 100.0), 3)
        overall_loss_pct = round((sum(losses) / len(losses)) * 100.0, 3)
        simulated_latency_report = {
            "provenance": "SIMULATED",
            "source": "SIMULATED_TESTBED_ENGINE",
            "sample_count": sample_count,
            "sample_support": "PROVISIONAL" if sample_count < 100 else "SIMULATION_SAMPLE_SET",
            "sample_support_note": (
                "Fewer than 100 generated samples; tail percentiles are provisional."
                if sample_count < 100 else
                "Percentiles describe this generated trace only; they are not field measurements."
            ),
            "measurement_window_start_utc": datetime.fromtimestamp(sample_times[0], timezone.utc).isoformat() if sample_times else None,
            "measurement_window_end_utc": datetime.fromtimestamp(sample_times[-1], timezone.utc).isoformat() if sample_times else None,
            "measurement_interval_ms_mean": sum(intervals_ms) / len(intervals_ms) if intervals_ms else None,
            "percentile_method": "Linear interpolation, rank=(n-1)*p, zero-based order statistic.",
            "latency_semantics": "Simulated latency_ms model output; directionality is not established as one-way field latency.",
            "latency_unit": "ms",
            "latency_ms": describe_distribution(latencies),
            "rtt_ms": describe_distribution(rtt_values),
            "rtt_semantics": "Separately generated model field; not an observed network round trip.",
            "jitter_ms": describe_distribution(jitter_values),
            "reliability": {
                "packet_loss_rate_percent": round(overall_loss_pct, 3),
                "samples_with_nonzero_loss": sum(1 for loss in losses if loss > 0),
                "samples_without_loss": sum(1 for loss in losses if loss == 0),
                "packet_counts": "UNAVAILABLE: simulator samples contain loss-rate values, not individual packet outcomes.",
                "timeout_rate": "UNAVAILABLE: timeouts are not modeled as distinct events.",
                "delivery_success_rate_percent": delivery_success_pct,
                "delivery_success_method": "100% minus mean generated sample packet_loss_rate; sample-derived, not packet-count based.",
            },
        }

        # Evaluate each sample and detect anomalies
        total_anomalies = 0
        false_alarms = 0
        impaired_start_idx: Optional[int] = None
        recovery_end_idx: Optional[int] = None

        for i, s in enumerate(samples):
            status, vios = evaluator.evaluate_sample(s)
            for v in vios:
                if v not in all_violations:
                    all_violations.append(v)

            is_ground_truth_impaired = (30 <= i <= 65) and len(impairments) > 0
            anom_results = detector.detect_sample(s, ground_truth_impaired=is_ground_truth_impaired)

            for ar in anom_results:
                if ar.is_anomaly:
                    total_anomalies += 1
                    if ar.false_alarm_flag:
                        false_alarms += 1

            if status != HealthStatus.HEALTHY and impaired_start_idx is None:
                impaired_start_idx = i
            if impaired_start_idx is not None and status == HealthStatus.HEALTHY and i > 65 and recovery_end_idx is None:
                recovery_end_idx = i

        # Calculate recovery time in milliseconds
        recovery_time_ms = 0.0
        if impaired_start_idx is not None:
            end_idx = recovery_end_idx if recovery_end_idx is not None else len(samples) - 1
            recovery_time_ms = round(max(0.0, (end_idx - 65) * 10.0), 2)

        # Determine compliance
        if not all_violations:
            compliance = "COMPLIANT"
        elif any("Latency violation" in v or "loss violation" in v for v in all_violations):
            compliance = "VIOLATED"
        else:
            compliance = "DEGRADED"

        # Deterministic recovery actions (No LLM)
        recovery_actions = evaluator.determine_deterministic_recovery(samples, all_violations)

        # Resource overhead calculation (deterministic compute overhead of monitoring & telemetry)
        resource_overhead_pct = round(0.42 + (0.05 * len(impairments)), 2)

        sim_id = f"SIM-5G-{int(time.time())}-{random.randint(100, 999)}"

        return SimulationResult(
            simulation_id=sim_id,
            profile=profile.value if isinstance(profile, NetworkProfileType) else str(profile),
            impairments_applied=[imp.value if isinstance(imp, ImpairmentType) else str(imp) for imp in impairments],
            total_samples=len(samples),
            delivery_success_rate=delivery_success_pct,
            tail_latency_p95_ms=round(tail_p95, 2),
            tail_latency_p99_ms=round(tail_p99, 2),
            average_latency_ms=round(avg_lat, 2),
            max_latency_ms=round(max_lat, 2),
            packet_loss_pct=overall_loss_pct,
            recovery_time_ms=recovery_time_ms,
            total_anomalies_detected=total_anomalies,
            false_alarms_count=false_alarms,
            resource_overhead_pct=resource_overhead_pct,
            slo_compliance_status=compliance,
            violations=all_violations,
            recommended_recovery=recovery_actions,
            latency_report=simulated_latency_report,
        )
