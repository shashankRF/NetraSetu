"""Bounded, reproducible multi-impairment experiments using NetraSetu's simulator.

This is a controlled software simulation. Its impairment windows and ranges are
defined by ``NetworkSimulator5G``; they are not field measurements or claims
about a deployed 5G network.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
import uuid
import statistics
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .models import ImpairmentType, NetworkProfileType
from .simulator import NetworkSimulator5G

ENGINE_VERSION = "combination-discovery-v1"
MAX_SCENARIOS = 64
MAX_TRIALS = 5
MAX_SAMPLES = 500
MIN_SAMPLES = 66

FAILURE_CATALOG: Dict[str, Dict[str, Any]] = {
    ImpairmentType.LATENCY_SPIKE.value: {
        "label": "Latency spike", "metric": "latency_ms", "unit": "ms",
        "modeled_range": "+15 to +35 ms during simulator samples 30–65; additional jitter +3 to +8 ms",
    },
    ImpairmentType.PACKET_LOSS.value: {
        "label": "Packet loss", "metric": "packet_loss_rate", "unit": "ratio",
        "modeled_range": "0.02 to 0.08 during simulator samples 30–65",
    },
    ImpairmentType.CONGESTION.value: {
        "label": "Congestion", "metric": "queue_depth_pkts", "unit": "packets",
        "modeled_range": "+180 to +320 packets during simulator samples 30–65",
    },
    ImpairmentType.HANDOVER_DISRUPTION.value: {
        "label": "Handover disruption", "metric": "latency_ms", "unit": "ms",
        "modeled_range": "+45 ms and 0.15 loss during samples 40–48",
    },
    ImpairmentType.LINK_FAILURE.value: {
        "label": "Link failure", "metric": "throughput_mbps", "unit": "Mbps",
        "modeled_range": "zero throughput and full loss during samples 42–52",
    },
}

METRICS = (
    "tail_latency_p95_ms", "tail_latency_p99_ms", "average_latency_ms",
    "max_latency_ms", "packet_loss_pct", "delivery_success_rate",
    "recovery_time_ms", "resource_overhead_pct",
)
METRIC_UNITS = {
    "tail_latency_p95_ms": "ms", "tail_latency_p99_ms": "ms",
    "average_latency_ms": "ms", "max_latency_ms": "ms",
    "packet_loss_pct": "%", "delivery_success_rate": "%",
    "recovery_time_ms": "ms", "resource_overhead_pct": "%",
}


class CombinationValidationError(ValueError):
    pass


def scenario_count(failure_types: Sequence[str], max_depth: int, trials: int = 1) -> int:
    """Return baseline + all non-empty subsets up to ``max_depth``, per trial."""
    _validate_failures(failure_types)
    if not 1 <= max_depth <= max(1, len(failure_types)):
        raise CombinationValidationError("combination_depth must be between 1 and the selected failure count")
    if not 1 <= trials <= MAX_TRIALS:
        raise CombinationValidationError(f"trials must be between 1 and {MAX_TRIALS}")
    return (1 + sum(len(list(combinations(failure_types, depth)))
                    for depth in range(1, min(max_depth, len(failure_types)) + 1))) * trials


def _validate_failures(failure_types: Sequence[str]) -> None:
    if len(set(failure_types)) != len(failure_types):
        raise CombinationValidationError("failure_types must not contain duplicates")
    unknown = sorted(set(failure_types) - set(FAILURE_CATALOG))
    if unknown:
        raise CombinationValidationError(f"Unsupported failure types: {', '.join(unknown)}")


def _validate_thresholds(thresholds: Optional[Mapping[str, float]]) -> Dict[str, float]:
    thresholds = dict(thresholds or {})
    bounds = {
        "max_tail_latency_p95_ms": (0.0, 60000.0),
        "max_packet_loss_pct": (0.0, 100.0),
        "min_delivery_success_rate": (0.0, 100.0),
    }
    extra = sorted(set(thresholds) - set(bounds))
    if extra:
        raise CombinationValidationError(f"Unsupported policy thresholds: {', '.join(extra)}")
    for key, value in thresholds.items():
        low, high = bounds[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise CombinationValidationError(f"{key} must be a number in [{low}, {high}]")
    return {k: float(v) for k, v in thresholds.items()}


def evaluate_policy(metrics: Mapping[str, Any], thresholds: Optional[Mapping[str, float]]) -> Dict[str, Any]:
    """Evaluate only explicitly supplied, user-defined thresholds."""
    configured = _validate_thresholds(thresholds)
    if not configured:
        return {"policy_id": "USER-DEFINED-THRESHOLDS", "status": "NOT_EVALUATED",
                "threshold_origin": "No threshold supplied", "rules": [],
                "action": "Review the simulated metrics; no threshold decision was requested."}
    checks = {
        "max_tail_latency_p95_ms": ("tail_latency_p95_ms", "<="),
        "max_packet_loss_pct": ("packet_loss_pct", "<="),
        "min_delivery_success_rate": ("delivery_success_rate", ">="),
    }
    rules = []
    for key, threshold in configured.items():
        metric, op = checks[key]
        observed = metrics.get(metric)
        if observed is None:
            rules.append({"threshold": key, "metric": metric, "limit": threshold,
                          "observed": None, "status": "NOT_EVALUATED", "origin": "USER_DEFINED"})
            continue
        passed = observed <= threshold if op == "<=" else observed >= threshold
        rules.append({"threshold": key, "metric": metric, "limit": threshold,
                      "observed": observed, "unit": "ms" if metric.endswith("_ms") else "%",
                      "status": "SATISFIED" if passed else "THRESHOLD_EXCEEDED",
                      "origin": "USER_DEFINED"})
    statuses = {r["status"] for r in rules}
    status = "THRESHOLD_EXCEEDED" if "THRESHOLD_EXCEEDED" in statuses else (
        "NOT_EVALUATED" if "NOT_EVALUATED" in statuses else "SATISFIED")
    return {"policy_id": "USER-DEFINED-THRESHOLDS", "version": "1",
            "status": status, "threshold_origin": "USER_DEFINED",
            "rules": rules,
            "action": "Flag for human review; no network change was performed."
            if status == "THRESHOLD_EXCEEDED" else "No enforcement action was performed."}


def run_combination_search(
    *, profile: str = "URLLC", failure_types: Sequence[str], combination_depth: int = 2,
    max_scenarios: int = MAX_SCENARIOS, samples: int = 100, seed: int = 42,
    trials: int = 1, thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Run a bounded baseline + failure-subset experiment, with additive contrasts."""
    _validate_failures(failure_types)
    if not failure_types:
        raise CombinationValidationError("Select at least one failure type")
    if not 1 <= combination_depth <= len(failure_types):
        raise CombinationValidationError("combination_depth must be between 1 and selected failure count")
    if not 1 <= max_scenarios <= MAX_SCENARIOS:
        raise CombinationValidationError(f"max_scenarios must be between 1 and {MAX_SCENARIOS}")
    if not MIN_SAMPLES <= samples <= MAX_SAMPLES:
        raise CombinationValidationError(f"samples must be between {MIN_SAMPLES} and {MAX_SAMPLES} to include the modeled impairment window")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**31 - 1:
        raise CombinationValidationError("seed must be an integer between 0 and 2147483647")
    thresholds = _validate_thresholds(thresholds)
    try:
        profile_enum = NetworkProfileType(profile)
    except ValueError as exc:
        raise CombinationValidationError(f"Unsupported profile: {profile}") from exc

    requested = scenario_count(failure_types, combination_depth, trials)
    subsets: List[Tuple[str, ...]] = [()]
    for depth in range(1, combination_depth + 1):
        subsets.extend(combinations(failure_types, depth))
    selected = subsets[:max_scenarios]
    run_fingerprint = sha256(repr((profile, tuple(failure_types), combination_depth,
                                   max_scenarios, samples, seed, trials,
                                   tuple(sorted(thresholds.items())))).encode()).hexdigest()[:12]
    run_id = f"FCR-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []
    metric_by_trial: Dict[int, Dict[Tuple[str, ...], Dict[str, Any]]] = {}

    for trial in range(trials):
        per_trial: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        trial_seed = seed + trial * 100003
        for index, subset in enumerate(selected):
            # Paired conditions use the same seed within a trial so their
            # difference is not confounded by unrelated nominal-noise draws.
            scenario_seed = trial_seed
            scenario_id = f"{run_id}-T{trial + 1:02d}-S{index + 1:03d}"
            scenario_started = datetime.now(timezone.utc).isoformat()
            config = {"profile": profile_enum.value,
                      "failure_types": list(subset), "samples": samples,
                      "seed": scenario_seed}
            try:
                result = NetworkSimulator5G(seed=scenario_seed).run_simulation(
                    profile=profile_enum,
                    impairments=[ImpairmentType(name) for name in subset],
                    num_samples=samples,
                )
            except Exception as exc:
                results.append({"scenario_id": scenario_id, "started_at": scenario_started,
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                                "trial": trial + 1, "status": "FAILED",
                                "errors": [f"{type(exc).__name__}: {exc}"],
                                "configuration": config, "simulator_version": ENGINE_VERSION,
                                "metrics": {}, "policy_evaluation": {"status": "NOT_EVALUATED"},
                                "human_review_status": "NOT_EVALUATED",
                                "provenance": {"source": "SIMULATION", "real_testbed": False,
                                               "engine_version": ENGINE_VERSION}})
                continue
            metrics = {name: getattr(result, name) for name in METRICS}
            metrics["simulated_post_impairment_interval_ms"] = metrics.get("recovery_time_ms")
            policy = evaluate_policy(metrics, thresholds)
            baseline_metrics = per_trial.get(())
            if not subset:
                comparison = {"status": "BASELINE", "metrics_compared": []}
            elif baseline_metrics is None:
                comparison = {"status": "INCONCLUSIVE", "metrics_compared": []}
            else:
                adverse = {
                    "tail_latency_p95_ms": metrics["tail_latency_p95_ms"] > baseline_metrics["tail_latency_p95_ms"],
                    "packet_loss_pct": metrics["packet_loss_pct"] > baseline_metrics["packet_loss_pct"],
                    "delivery_success_rate": metrics["delivery_success_rate"] < baseline_metrics["delivery_success_rate"],
                }
                comparison = {"status": "OBSERVED DEGRADATION" if any(adverse.values()) else "NO OBSERVED DEGRADATION",
                              "metrics_compared": adverse}
            row = {
                "scenario_id": scenario_id,
                "started_at": scenario_started,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "trial": trial + 1,
                "status": "COMPLETED",
                "errors": [],
                "configuration": config,
                "simulator_version": result.provenance.get("engine"),
                "metrics": metrics,
                "latency_report": result.latency_report,
                "comparison_to_baseline": comparison,
                "profile_evaluation": {
                    "status": result.slo_compliance_status,
                    "violations": result.violations,
                    "origin": "configured simulator profile; not independently source-verified here",
                },
                "policy_evaluation": policy,
                "recovery_recommendations": [
                    {"action_type": a.action_type,
                     "target_metric": a.target_metric,
                     "rule_source_status": "EVIDENCE NOT RETRIEVED",
                     "status": "RECOMMENDATION_ONLY"}
                    for a in result.recommended_recovery
                ],
                "human_review_status": ("RECOMMENDED" if policy["status"] == "THRESHOLD_EXCEEDED"
                                         else "NOT_EVALUATED" if policy["status"] == "NOT_EVALUATED"
                                         else "NOT_TRIGGERED"),
                "provenance": {"source": "SIMULATION", "real_testbed": False,
                               "llm_in_decision_loop": False, "engine_version": ENGINE_VERSION},
            }
            per_trial[subset] = {**metrics, "scenario_id": scenario_id}
            results.append(row)
        metric_by_trial[trial] = per_trial

    # Quantify interaction relative to an explicitly declared additive model.
    interactions = []
    for trial_idx, per_trial in metric_by_trial.items():
        baseline = per_trial.get(())
        if baseline is None:
            continue
        for subset, combined in per_trial.items():
            if len(subset) < 2:
                continue
            singles = [per_trial.get((failure,)) for failure in subset]
            if any(item is None for item in singles):
                continue
            for metric in METRICS:
                additive_expected = baseline[metric] + sum(item[metric] - baseline[metric] for item in singles)
                delta = combined[metric] - additive_expected
                interactions.append({"trial": trial_idx + 1, "scenario_id": combined["scenario_id"],
                                     "failure_types": list(subset), "metric": metric,
                                     "unit": METRIC_UNITS[metric],
                                     "observed_combined": combined[metric],
                                     "additive_expected": round(additive_expected, 6),
                                     "interaction_delta": round(delta, 6),
                                     "assessment": "INTERACTION EFFECT" if abs(delta) > 1e-6 else "INCONCLUSIVE",
                                     "comparison_model": "ADDITIVE: baseline + sum(individual effects)"})
    finished = datetime.now(timezone.utc).isoformat()
    completed_expected = len(selected) * trials
    completed_count = sum(row["status"] == "COMPLETED" for row in results)
    failed_count = len(results) - completed_count
    run_status = ("FAILED" if completed_count == 0 else
                  "PARTIAL_FAILED" if failed_count else
                  "COMPLETED" if completed_expected == requested else "INCOMPLETE")
    trial_summaries = []
    selected_keys = list(dict.fromkeys(tuple(r["configuration"]["failure_types"]) for r in results))
    for subset in selected_keys:
        for metric in METRICS:
            observed = [per_trial[subset][metric] for per_trial in metric_by_trial.values()
                        if subset in per_trial]
            if not observed:
                continue
            trial_summaries.append({"failure_types": list(subset) or ["BASELINE"],
                                    "metric": metric, "trials": len(observed),
                                    "mean": round(statistics.mean(observed), 6),
                                    "standard_deviation": round(statistics.stdev(observed), 6) if len(observed) > 1 else None,
                                    "variability_note": "Sample standard deviation across repeated simulator trials; omitted for a single trial."})
    audit_record = {"event_id": run_id, "event_type": "FAILURE_COMBINATION_SIMULATION",
                    "timestamp": finished, "engine_version": ENGINE_VERSION,
                    "input_fingerprint": run_fingerprint, "execution_status": run_status,
                    "scenario_count": len(results), "failed_scenarios": failed_count, "user_thresholds": thresholds,
                    "threshold_origin": "USER_DEFINED" if thresholds else "NONE",
                    "provenance": "SIMULATION; not a live network action"}
    return {
        "run_id": run_id, "status": run_status,
        "started_at": started_at, "completed_at": finished,
        "engine_version": ENGINE_VERSION,
        "input_fingerprint": run_fingerprint,
        "search": {"requested_scenarios": requested, "executed_scenarios": len(results),
                   "max_scenarios": max_scenarios, "complete": completed_expected == requested and failed_count == 0,
                   "failed_scenarios": failed_count,
                   "trials": trials, "combination_depth": combination_depth,
                   "search_strategy": "bounded exhaustive subsets in stable order",
                   "omitted_scenarios": max(0, requested - completed_expected)},
        "assumptions": ["Simulator-defined impairment windows and generated ranges are controlled inputs, not field estimates.",
                        "The interaction comparison uses an additive model and is descriptive; it does not establish causation."],
        "results": results, "interaction_analysis": interactions,
        "trial_summary": trial_summaries, "audit_record": audit_record,
        "evidence_assessment": {"status": "EVIDENCE NOT RETRIEVED",
                                 "scope": "No regulatory or standards documents were queried by this simulator.",
                                 "note": "Thresholds are user-defined; simulator profile checks are code-configured and not independently source-verified here."},
        "provenance": {"source": "SIMULATION", "real_testbed": False,
                       "llm_in_decision_loop": False},
    }
