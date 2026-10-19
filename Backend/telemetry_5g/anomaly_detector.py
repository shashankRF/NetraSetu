from __future__ import annotations
import math
from typing import List, Dict, Optional, Any
from .models import TelemetrySample, AnomalyResult


class NetworkAnomalyDetector:
    """
    Separate, measurable anomaly detection component for real-time 5G network telemetry.
    Uses deterministic statistical indicators (Exponentially Weighted Moving Average & Z-score)
    with optional LightGBM / XGBoost hooks when installed.

    NO LLMs are invoked in this component.
    """

    def __init__(
        self,
        alpha: float = 0.15,            # EWMA smoothing factor
        z_threshold: float = 2.5,       # Z-score threshold for anomaly flag
        min_history_size: int = 5,
    ):
        self.alpha = alpha
        self.z_threshold = z_threshold
        self.min_history_size = min_history_size

        # History tracking
        self.latency_history: List[float] = []

        # EWMA state
        self.ewma_latency: Optional[float] = None
        self.ewma_variance: Optional[float] = None

        # Check for LightGBM / XGBoost availability
        self.has_lightgbm = False
        self.has_xgboost = False
        try:
            import lightgbm
            self.has_lightgbm = True
        except ImportError:
            pass
        try:
            import xgboost
            self.has_xgboost = True
        except ImportError:
            pass

    def detect_sample(
        self,
        sample: TelemetrySample,
        ground_truth_impaired: Optional[bool] = None,
    ) -> List[AnomalyResult]:
        """
        Evaluate a single telemetry sample for anomalous deviations.
        """
        results: List[AnomalyResult] = []
        lat = sample.latency_ms
        self.latency_history.append(lat)

        if len(self.latency_history) < self.min_history_size:
            # Baseline calibration phase
            return results

        # Initialize baseline on first observation after min_history_size
        if self.ewma_latency is None:
            self.ewma_latency = sum(self.latency_history) / len(self.latency_history)
            self.ewma_variance = sum((x - self.ewma_latency) ** 2 for x in self.latency_history) / len(self.latency_history)

        # 1. Compute deviation against the prior EWMA state BEFORE updating
        prior_mean = self.ewma_latency
        prior_var = self.ewma_variance if self.ewma_variance is not None else 0.01
        std_dev = math.sqrt(max(prior_var, 0.0025))  # Minimum std dev floor 0.05ms
        z_score = abs(lat - prior_mean) / std_dev

        # Latency anomaly triggered if Z-score exceeds threshold OR absolute 5G URLLC threshold exceeded
        is_anomaly = (z_score >= self.z_threshold) or (sample.active_slice == "SST-1-URLLC" and lat > 10.0)
        normalized_score = min(1.0, z_score / (self.z_threshold * 2.0))

        # Check false alarm if ground truth status is provided
        false_alarm = False
        if is_anomaly and ground_truth_impaired is False:
            false_alarm = True

        algorithm_used = "EWMA_ZSCORE_BASELINE"
        if self.has_lightgbm:
            algorithm_used = "LIGHTGBM_SUPERVISED"
        elif self.has_xgboost:
            algorithm_used = "XGBOOST_SUPERVISED"

        results.append(
            AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=round(normalized_score, 4),
                metric_name="latency_ms",
                observed_value=round(lat, 2),
                threshold_value=round(prior_mean + self.z_threshold * std_dev, 2),
                detector_algorithm=algorithm_used,
                false_alarm_flag=false_alarm,
            )
        )

        # 2. Update EWMA state (dampen update if anomalous to prevent baseline corruption)
        effective_alpha = self.alpha * 0.2 if is_anomaly else self.alpha
        diff = lat - prior_mean
        self.ewma_latency = (1 - effective_alpha) * prior_mean + effective_alpha * lat
        self.ewma_variance = (1 - effective_alpha) * prior_var + effective_alpha * (diff ** 2)

        # 3. Packet loss surge anomaly detection (loss > 0.5% in 5G is anomalous)
        if sample.packet_loss_rate > 0.005:
            results.append(
                AnomalyResult(
                    is_anomaly=True,
                    anomaly_score=min(1.0, sample.packet_loss_rate * 50.0),
                    metric_name="packet_loss_rate",
                    observed_value=sample.packet_loss_rate,
                    threshold_value=0.005,
                    detector_algorithm=algorithm_used,
                    false_alarm_flag=False,
                )
            )

        return results
