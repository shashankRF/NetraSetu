import math

from Backend.telemetry_5g.models import NetworkProfileType
from Backend.telemetry_5g.simulator import NetworkSimulator5G, linear_percentile


def test_linear_percentiles_use_documented_interpolated_rank():
    assert linear_percentile([0, 10, 20, 30], 50) == 15
    assert linear_percentile([0, 10, 20, 30], 0) == 0
    assert linear_percentile([0, 10, 20, 30], 100) == 30
    assert linear_percentile([], 95) is None


def test_simulator_returns_sample_count_and_honest_metrics_for_small_run():
    result = NetworkSimulator5G(seed=31).run_simulation(
        NetworkProfileType.URLLC, num_samples=10,
    )
    report = result.latency_report

    assert report["provenance"] == "SIMULATED"
    assert report["sample_count"] == report["latency_ms"]["sample_count"] == 10
    assert report["sample_support"] == "PROVISIONAL"
    assert report["percentile_method"].startswith("Linear interpolation")
    assert report["latency_ms"]["p50"] is not None
    assert report["latency_ms"]["p99"] is not None
    assert math.isclose(report["measurement_interval_ms_mean"], 10.0, abs_tol=1e-4)
    assert "not established" in report["latency_semantics"]
    assert report["reliability"]["packet_counts"].startswith("UNAVAILABLE")
    assert report["reliability"]["timeout_rate"].startswith("UNAVAILABLE")
    assert result.tail_latency_p95_ms == round(report["latency_ms"]["p95"], 2)


def test_full_simulation_report_has_explicit_modelled_sample_support():
    result = NetworkSimulator5G(seed=7).run_simulation(
        NetworkProfileType.EMBB, num_samples=100,
    )
    assert result.latency_report["sample_count"] == 100
    assert result.latency_report["sample_support"] == "SIMULATION_SAMPLE_SET"
    assert "not field measurements" in result.latency_report["sample_support_note"]
