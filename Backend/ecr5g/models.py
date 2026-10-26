from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ControllerStrategy(str, Enum):
    FIFO_BASELINE = "FIFO_BASELINE"
    STATIC_QOS_BASELINE = "STATIC_QOS_BASELINE"
    ECAC_CONTROLLER = "ECAC_CONTROLLER"


class QoSClass(str, Enum):
    EMERGENCY = "EMERGENCY"
    CRITICAL = "CRITICAL"
    STANDARD = "STANDARD"
    BULK = "BULK"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class ConflictStatus(str, Enum):
    CLEAR = "CLEAR"
    CONFLICTING = "CONFLICTING"
    SUPERSEDED = "SUPERSEDED"


class IntegrityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


def _require_id(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("identifier must be 1–120 ASCII letters, digits, '.', '_', ':', or '-' characters")
    return value


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


class EvidenceRequirement(StrictModel):
    requirement_id: str
    evidence_type: str = Field(min_length=1, max_length=80)
    mandatory: bool = True
    freshness_limit_seconds: int = Field(ge=0, le=31_536_000)
    deadline_utc: datetime
    permitted_source_identifiers: list[str] = Field(default_factory=list, max_length=50)
    require_verified_source: bool = True
    require_integrity_verified: bool = True
    requires_conflict_resolution: bool = False
    applicable_actions: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("requirement_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _require_id(value)

    @field_validator("deadline_utc")
    @classmethod
    def validate_deadline(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @field_validator("permitted_source_identifiers", "applicable_actions")
    @classmethod
    def validate_identifiers(cls, values: list[str]) -> list[str]:
        return [_require_id(value) for value in values]


class EvidenceObject(StrictModel):
    evidence_id: str
    incident_id: str
    evidence_type: str = Field(min_length=1, max_length=80)
    source_identifier: str
    source_timestamp_utc: datetime
    ingestion_timestamp_utc: datetime
    version_identifier: str = Field(min_length=1, max_length=120)
    integrity_status: IntegrityStatus
    integrity_metadata: dict[str, Any] = Field(default_factory=dict)
    payload_size_bytes: int = Field(ge=1, le=10_000_000)
    supports_requirements: list[str] = Field(default_factory=list, max_length=50)
    verification_status: VerificationStatus
    conflict_status: ConflictStatus = ConflictStatus.CLEAR
    conflict_resolution_reference: str | None = Field(default=None, max_length=160)
    supersedes_evidence_id: str | None = None
    origin: str = Field(default="SIMULATED_FIXTURE", min_length=1, max_length=80)

    @field_validator("evidence_id", "incident_id", "source_identifier", "supersedes_evidence_id")
    @classmethod
    def validate_ids(cls, value: str | None) -> str | None:
        return _require_id(value) if value is not None else value

    @field_validator("source_timestamp_utc", "ingestion_timestamp_utc")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "EvidenceObject":
        if self.ingestion_timestamp_utc < self.source_timestamp_utc:
            raise ValueError("evidence ingestion timestamp may not precede its source timestamp")
        return self

    @field_validator("supports_requirements")
    @classmethod
    def validate_requirement_ids(cls, values: list[str]) -> list[str]:
        return [_require_id(value) for value in values]


class TrafficFlow(StrictModel):
    flow_id: str
    incident_id: str
    agency_application_identity: str = Field(min_length=1, max_length=120)
    offered_load_mbps: float = Field(ge=0, le=100_000)
    payload_size_bytes: int = Field(ge=1, le=10_000_000)
    deadline_utc: datetime
    qos_class: QoSClass
    max_latency_ms: float = Field(gt=0, le=600_000)
    reliability_target: float = Field(gt=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    arrival_offset_ms: float = Field(default=0, ge=0, le=60_000)

    @field_validator("flow_id", "incident_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _require_id(value)

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: list[str]) -> list[str]:
        return [_require_id(value) for value in values]

    @field_validator("deadline_utc")
    @classmethod
    def validate_deadline(cls, value: datetime) -> datetime:
        return _require_utc(value)


class NetworkState(StrictModel):
    simulation_timestamp_utc: datetime
    bottleneck_capacity_mbps: float = Field(ge=0, le=1_000_000)
    latency_ms: float = Field(ge=0, le=600_000)
    packet_loss_probability: float = Field(ge=0, le=1)
    processing_delay_ms: float = Field(default=0, ge=0, le=600_000)
    congestion_state: str = Field(min_length=1, max_length=40)
    link_available: bool
    per_flow_measurements: dict[str, dict[str, float]] = Field(default_factory=dict)

    @field_validator("simulation_timestamp_utc")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _require_utc(value)


class NetworkChange(StrictModel):
    start_offset_ms: float = Field(ge=0, le=60_000)
    end_offset_ms: float = Field(gt=0, le=60_000)
    bottleneck_capacity_mbps: float | None = Field(default=None, ge=0, le=1_000_000)
    latency_ms: float | None = Field(default=None, ge=0, le=600_000)
    packet_loss_probability: float | None = Field(default=None, ge=0, le=1)
    processing_delay_ms: float | None = Field(default=None, ge=0, le=600_000)
    congestion_state: str | None = Field(default=None, min_length=1, max_length=40)
    link_available: bool | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "NetworkChange":
        if self.end_offset_ms <= self.start_offset_ms:
            raise ValueError("network change end must be after its start")
        if all(getattr(self, name) is None for name in (
            "bottleneck_capacity_mbps", "latency_ms", "packet_loss_probability",
            "processing_delay_ms", "congestion_state", "link_available",
        )):
            raise ValueError("network change must modify at least one network property")
        return self


class DecisionRequirement(StrictModel):
    action_id: str
    incident_id: str
    mandatory_evidence_requirements: list[str] = Field(default_factory=list, max_length=50)
    optional_evidence_requirements: list[str] = Field(default_factory=list, max_length=50)
    requires_conflict_resolution: bool = False
    human_approval_required: bool = True

    @field_validator("action_id", "incident_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _require_id(value)

    @field_validator("mandatory_evidence_requirements", "optional_evidence_requirements")
    @classmethod
    def validate_requirement_ids(cls, values: list[str]) -> list[str]:
        return [_require_id(value) for value in values]


class ECACPolicyLimits(StrictModel):
    mandatory_preempts_optional: bool = True
    max_consecutive_mandatory_messages: int = Field(default=32, ge=1, le=1000)
    max_priority_promotions: int = Field(default=10_000, ge=0, le=100_000)


class ECR5GScenario(StrictModel):
    scenario_id: str
    version: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=1000)
    simulation_epoch_utc: datetime
    simulation_duration_ms: int = Field(gt=0, le=60_000)
    seed: int = Field(ge=0, le=2**31 - 1)
    initial_network_state: NetworkState
    network_changes: list[NetworkChange] = Field(default_factory=list, max_length=50)
    traffic_flows: list[TrafficFlow] = Field(min_length=1, max_length=100)
    evidence_requirements: list[EvidenceRequirement] = Field(default_factory=list, max_length=100)
    evidence_objects: list[EvidenceObject] = Field(default_factory=list, max_length=200)
    decision_requirements: list[DecisionRequirement] = Field(default_factory=list, max_length=50)
    ecac_policy_limits: ECACPolicyLimits = Field(default_factory=ECACPolicyLimits)
    failure_conditions: list[str] = Field(default_factory=list, max_length=30)
    expected_safety_invariants: list[str] = Field(default_factory=list, max_length=30)
    evaluation_objectives: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str) -> str:
        return _require_id(value)

    @field_validator("simulation_epoch_utc")
    @classmethod
    def validate_epoch(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def validate_cross_references(self) -> "ECR5GScenario":
        if self.initial_network_state.simulation_timestamp_utc != self.simulation_epoch_utc:
            raise ValueError("initial network timestamp must equal the scenario UTC epoch")
        reqs = {r.requirement_id: r for r in self.evidence_requirements}
        if len(reqs) != len(self.evidence_requirements):
            raise ValueError("evidence requirement identifiers must be unique")
        evidence = {e.evidence_id: e for e in self.evidence_objects}
        if len(evidence) != len(self.evidence_objects):
            raise ValueError("evidence identifiers must be unique")
        flows = {flow.flow_id: flow for flow in self.traffic_flows}
        if len(flows) != len(self.traffic_flows):
            raise ValueError("traffic flow identifiers must be unique")
        actions = {action.action_id: action for action in self.decision_requirements}
        if len(actions) != len(self.decision_requirements):
            raise ValueError("decision action identifiers must be unique")
        for change in self.network_changes:
            if change.end_offset_ms > self.simulation_duration_ms:
                raise ValueError("network change may not extend beyond simulation duration")
        ordered_changes = sorted(self.network_changes, key=lambda item: item.start_offset_ms)
        for previous, current in zip(ordered_changes, ordered_changes[1:]):
            if current.start_offset_ms < previous.end_offset_ms:
                raise ValueError("network change intervals may not overlap")
        for requirement in self.evidence_requirements:
            if not (self.simulation_epoch_utc <= requirement.deadline_utc <= self.simulation_epoch_utc + timedelta(milliseconds=self.simulation_duration_ms)):
                raise ValueError("evidence deadline must fall inside the simulation window")
            for action_id in requirement.applicable_actions:
                if action_id not in actions:
                    raise ValueError(f"evidence requirement references unknown action: {action_id}")
        for item in self.evidence_objects:
            if item.ingestion_timestamp_utc > self.simulation_epoch_utc:
                raise ValueError(f"evidence was ingested after the simulation epoch: {item.evidence_id}")
            if item.incident_id not in {flow.incident_id for flow in self.traffic_flows}:
                raise ValueError(f"evidence object references unknown incident: {item.incident_id}")
            if any(req_id not in reqs for req_id in item.supports_requirements):
                raise ValueError(f"evidence object references unknown requirement: {item.evidence_id}")
            if item.supersedes_evidence_id and item.supersedes_evidence_id not in evidence:
                raise ValueError(f"evidence object supersedes unknown evidence: {item.supersedes_evidence_id}")
        for flow in self.traffic_flows:
            if not (self.simulation_epoch_utc <= flow.deadline_utc <= self.simulation_epoch_utc + timedelta(milliseconds=self.simulation_duration_ms)):
                raise ValueError(f"flow deadline must fall inside the simulation window: {flow.flow_id}")
            if flow.arrival_offset_ms >= self.simulation_duration_ms:
                raise ValueError(f"flow arrival must be inside the simulation window: {flow.flow_id}")
            if any(evidence_id not in evidence for evidence_id in flow.evidence_ids):
                raise ValueError(f"flow references unknown evidence: {flow.flow_id}")
            if any(evidence[evidence_id].incident_id != flow.incident_id for evidence_id in flow.evidence_ids):
                raise ValueError(f"flow and evidence incident identifiers do not match: {flow.flow_id}")
            if flow.evidence_ids and sum(evidence[eid].payload_size_bytes for eid in flow.evidence_ids) > flow.payload_size_bytes:
                raise ValueError(f"flow payload is too small for its evidence objects: {flow.flow_id}")
        for decision in self.decision_requirements:
            referenced = decision.mandatory_evidence_requirements + decision.optional_evidence_requirements
            if len(referenced) != len(set(referenced)):
                raise ValueError(f"decision requirements must not be duplicated across mandatory/optional lists: {decision.action_id}")
            if any(req_id not in reqs for req_id in referenced):
                raise ValueError(f"decision references unknown evidence requirement: {decision.action_id}")
            if any(reqs[req_id].applicable_actions and decision.action_id not in reqs[req_id].applicable_actions for req_id in referenced):
                raise ValueError(f"evidence requirement is not applicable to decision: {decision.action_id}")
        return self
