from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from Backend.audit.recorder import append_audit_record, create_audit_record, generate_audit_id, load_audit_records

from .engine import run_comparison
from .models import ControllerStrategy
from .scenarios import get_scenario, list_scenarios


router = APIRouter(prefix="/api/ecr5g", tags=["ECR-5G"])


class SimulationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=120)
    strategies: list[ControllerStrategy] = Field(
        default_factory=lambda: list(ControllerStrategy), min_length=1, max_length=3
    )
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator("strategies")
    @classmethod
    def unique_strategies(cls, value: list[ControllerStrategy]) -> list[ControllerStrategy]:
        if len(value) != len(set(value)):
            raise ValueError("strategies must not contain duplicates")
        return value


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "available", "feature": "ECR-5G", "simulated_only": True,
            "real_5g_network_configured": False}


@router.get("/scenarios")
def scenarios() -> dict[str, Any]:
    return {"scenarios": [item.model_dump(mode="json") for item in list_scenarios()],
            "count": len(list_scenarios()), "synthetic_fixtures": True}


@router.get("/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str) -> dict[str, Any]:
    item = get_scenario(scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="ECR-5G scenario not found")
    return item.model_dump(mode="json")


@router.post("/simulations/run")
def run(request: SimulationRunRequest) -> dict[str, Any]:
    scenario = get_scenario(request.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="ECR-5G scenario not found")
    report = run_comparison(scenario, request.strategies, request.seed)
    schedule_states = {item["strategy"]: item["schedule_status"] for item in report["strategy_results"]}
    if all(value == "FEASIBLE_FOR_HUMAN_REVIEW" for value in schedule_states.values()):
        run_status = "COMPLETED"
    elif all(value == "INFEASIBLE" for value in schedule_states.values()):
        run_status = "INFEASIBLE"
    else:
        run_status = "COMPLETED_WITH_INFEASIBLE_SCHEDULES"
    record = create_audit_record(
        question=f"ECR-5G simulation: {scenario.scenario_id}",
        event_type="ECR5G_SIMULATION",
        execution_status="COMPLETED",
        execution_id=report["run_id"],
        scenario_id=scenario.scenario_id,
        scenario_title=scenario.title,
        human_review_required=True,
        provenance="DETERMINISTIC_SIMULATION",
        domain="Emergency Communications QoS",
        jurisdiction="SIMULATION_ONLY",
    )
    record["run_id"] = report["run_id"]
    record["schedule_status"] = run_status
    record["ecr5g_report"] = report
    record.pop("audit_id", None)
    record["audit_id"] = generate_audit_id(record)
    try:
        audit_id = append_audit_record(record)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not persist ECR-5G audit report") from exc
    return {"run_id": report["run_id"], "audit_id": audit_id, "status": run_status,
            "execution_status": "COMPLETED", "strategy_schedule_statuses": schedule_states,
            "report": report}


def _find_run(run_id: str) -> dict[str, Any] | None:
    for record in reversed(load_audit_records()):
        if record.get("event_type") == "ECR5G_SIMULATION" and record.get("run_id") == run_id:
            return record
    return None


@router.get("/simulations/{run_id}")
def simulation(run_id: str) -> dict[str, Any]:
    record = _find_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="ECR-5G simulation run not found")
    report = record.get("ecr5g_report")
    return {"run_id": run_id, "audit_id": record.get("audit_id"),
            "status": record.get("schedule_status", record.get("execution_status")),
            "execution_status": record.get("execution_status"),
            "report": report}


@router.get("/simulations/{run_id}/report")
def simulation_report(run_id: str) -> dict[str, Any]:
    record = _find_run(run_id)
    if record is None or not record.get("ecr5g_report"):
        raise HTTPException(status_code=404, detail="ECR-5G simulation report not found")
    return record["ecr5g_report"]
