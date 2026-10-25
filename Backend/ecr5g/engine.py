from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .models import ControllerStrategy, ECR5GScenario
from .simulator import run_simulation


def run_comparison(scenario: ECR5GScenario, strategies: list[ControllerStrategy], seed: int | None = None) -> dict:
    actual_seed = scenario.seed if seed is None else seed
    started_at = datetime.now(timezone.utc).isoformat()
    results = [run_simulation(scenario, strategy, seed=actual_seed) for strategy in strategies]
    return {
        "run_id": f"ECR5G-{uuid.uuid4().hex[:16]}",
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.version,
        "scenario_title": scenario.title,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": actual_seed,
        "configuration": scenario.model_dump(mode="json"),
        "simulation_assumptions": {
            "single_shared_bottleneck": True,
            "event_time_only_no_sleep": True,
            "capacity_change_applied_at_serialization_segments": True,
            "propagation_and_processing_delays_are_separate": True,
            "undelivered_latency_penalty_ms": 60_000,
            "message_safety_limit": 5_000,
        },
        "provenance": {"simulated": True, "real_5g": False, "llm_in_decision_loop": False,
                       "real_world_action_authorized": False,
                       "scenario_fixture_origin": "SYNTHETIC_DETERMINISTIC_TEST_FIXTURE"},
        "strategy_results": results,
        "comparison_method": "Same scenario, generated traffic trace, and seed across selected strategies.",
        "limitations": ["This emulator is not a 3GPP conformance test or production network controller.",
                        "No live network configuration, agency dispatch, or operational authorization occurs."],
    }
