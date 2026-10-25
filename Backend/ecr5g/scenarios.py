from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import (
    ConflictStatus,
    DecisionRequirement,
    ECR5GScenario,
    EvidenceObject,
    EvidenceRequirement,
    IntegrityStatus,
    NetworkChange,
    NetworkState,
    QoSClass,
    TrafficFlow,
    VerificationStatus,
)


SCENARIO_VERSION = "1.0.0"
_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
_SAFETY = [
    "SIMULATION_ONLY_NO_REAL_NETWORK_CONFIGURATION",
    "NO_REAL_WORLD_ACTION_AUTHORIZED",
    "PACKET_DELIVERY_DOES_NOT_PROVE_EVIDENCE_VALIDITY",
    "MANDATORY_EVIDENCE_REQUIREMENTS_ARE_HARD_CONSTRAINTS",
]


def _dt(milliseconds: int) -> datetime:
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _evidence(evidence_id: str, evidence_type: str, source: str, requirements: list[str], *,
              source_age_seconds: int = 20, conflict: ConflictStatus = ConflictStatus.CLEAR,
              verified: VerificationStatus = VerificationStatus.VERIFIED,
              integrity: IntegrityStatus = IntegrityStatus.VERIFIED,
              payload_bytes: int = 2048) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        incident_id="INC-001",
        evidence_type=evidence_type,
        source_identifier=source,
        source_timestamp_utc=_EPOCH - timedelta(seconds=source_age_seconds),
        ingestion_timestamp_utc=_EPOCH - timedelta(seconds=max(1, source_age_seconds - 5)),
        version_identifier="fixture-v1",
        integrity_status=integrity,
        integrity_metadata={"method": "SIMULATED_FIXTURE_VALIDATION", "real_document_digest": False},
        payload_size_bytes=payload_bytes,
        supports_requirements=requirements,
        verification_status=verified,
        conflict_status=conflict,
        origin="SIMULATED_SCENARIO_FIXTURE",
    )


def _base_requirements(*, route_conflict: bool = False, incident_deadline_ms: int = 1800,
                       route_deadline_ms: int = 2500) -> list[EvidenceRequirement]:
    return [
        EvidenceRequirement(
            requirement_id="REQ-INCIDENT",
            evidence_type="INCIDENT_REPORT",
            mandatory=True,
            freshness_limit_seconds=180,
            deadline_utc=_dt(incident_deadline_ms),
            permitted_source_identifiers=["agency:incident-command"],
            applicable_actions=["ACTION-RESTORE"],
        ),
        EvidenceRequirement(
            requirement_id="REQ-ROUTE",
            evidence_type="ROUTE_STATUS",
            mandatory=True,
            freshness_limit_seconds=90,
            deadline_utc=_dt(route_deadline_ms),
            permitted_source_identifiers=["agency:field-unit"],
            requires_conflict_resolution=route_conflict,
            applicable_actions=["ACTION-RESTORE"],
        ),
        EvidenceRequirement(
            requirement_id="REQ-NETWORK",
            evidence_type="NETWORK_HEALTH",
            mandatory=False,
            freshness_limit_seconds=60,
            deadline_utc=_dt(2800),
            permitted_source_identifiers=["operator:noc"],
            applicable_actions=["ACTION-RESTORE"],
        ),
    ]


def _flows(*, duration_ms: int = 3000, incident_rate: float = 0.08,
           route_rate: float = 0.05, background_rate: float = 0.25,
           payload_bytes: int = 2048, extra: bool = False) -> list[TrafficFlow]:
    flows = [
        TrafficFlow(
            flow_id="FLOW-INCIDENT", incident_id="INC-001",
            agency_application_identity="agency:incident-command/emergency-report",
            offered_load_mbps=incident_rate, payload_size_bytes=payload_bytes,
            deadline_utc=_dt(duration_ms), qos_class=QoSClass.CRITICAL,
            max_latency_ms=250, reliability_target=0.999,
            evidence_ids=["EVID-INCIDENT"],
        ),
        TrafficFlow(
            flow_id="FLOW-ROUTE", incident_id="INC-001",
            agency_application_identity="agency:field-unit/route-status",
            offered_load_mbps=route_rate, payload_size_bytes=payload_bytes,
            deadline_utc=_dt(duration_ms), qos_class=QoSClass.EMERGENCY,
            max_latency_ms=500, reliability_target=0.99,
            evidence_ids=["EVID-ROUTE"], arrival_offset_ms=100,
        ),
        TrafficFlow(
            flow_id="FLOW-BACKGROUND", incident_id="INC-001",
            agency_application_identity="operator:noc/telemetry",
            offered_load_mbps=background_rate, payload_size_bytes=1024,
            deadline_utc=_dt(duration_ms), qos_class=QoSClass.STANDARD,
            max_latency_ms=1500, reliability_target=0.95,
        ),
    ]
    if extra:
        flows.append(TrafficFlow(
            flow_id="FLOW-INTERAGENCY", incident_id="INC-001",
            agency_application_identity="agency:disaster-management/coordination",
            offered_load_mbps=background_rate * 0.8, payload_size_bytes=1400,
            deadline_utc=_dt(duration_ms), qos_class=QoSClass.BULK,
            max_latency_ms=1800, reliability_target=0.9,
        ))
    return flows


def _scenario(scenario_id: str, title: str, description: str, *,
              capacity: float = 5.0, latency: float = 25.0, processing_delay_ms: float = 5.0,
              loss: float = 0.001,
              congestion: str = "NORMAL", link: bool = True,
              duration_ms: int = 3000, changes: list[NetworkChange] | None = None,
              requirements: list[EvidenceRequirement] | None = None,
              evidence: list[EvidenceObject] | None = None,
              flows: list[TrafficFlow] | None = None, seed: int = 17,
              failures: list[str] | None = None, objectives: list[str] | None = None) -> ECR5GScenario:
    return ECR5GScenario(
        scenario_id=scenario_id,
        version=SCENARIO_VERSION,
        title=title,
        description=description,
        simulation_epoch_utc=_EPOCH,
        simulation_duration_ms=duration_ms,
        seed=seed,
        initial_network_state=NetworkState(
            simulation_timestamp_utc=_EPOCH,
            bottleneck_capacity_mbps=capacity,
            latency_ms=latency,
            processing_delay_ms=processing_delay_ms,
            packet_loss_probability=loss,
            congestion_state=congestion,
            link_available=link,
        ),
        network_changes=changes or [],
        traffic_flows=flows or _flows(duration_ms=duration_ms),
        evidence_requirements=requirements or _base_requirements(),
        evidence_objects=evidence or [
            _evidence("EVID-INCIDENT", "INCIDENT_REPORT", "agency:incident-command", ["REQ-INCIDENT"]),
            _evidence("EVID-ROUTE", "ROUTE_STATUS", "agency:field-unit", ["REQ-ROUTE"]),
        ],
        decision_requirements=[DecisionRequirement(
            action_id="ACTION-RESTORE",
            incident_id="INC-001",
            mandatory_evidence_requirements=["REQ-INCIDENT", "REQ-ROUTE"],
            optional_evidence_requirements=["REQ-NETWORK"],
            requires_conflict_resolution=any(r.requires_conflict_resolution for r in (requirements or _base_requirements())),
            human_approval_required=True,
        )],
        failure_conditions=failures or [],
        expected_safety_invariants=list(_SAFETY),
        evaluation_objectives=objectives or [
            "Compare all selected strategies on the same generated traffic trace.",
            "Measure deadline delivery and evidence completeness separately.",
        ],
    )


def build_scenarios() -> dict[str, ECR5GScenario]:
    normal_evidence = [
        _evidence("EVID-INCIDENT", "INCIDENT_REPORT", "agency:incident-command", ["REQ-INCIDENT"]),
        _evidence("EVID-ROUTE", "ROUTE_STATUS", "agency:field-unit", ["REQ-ROUTE"]),
        _evidence("EVID-NETWORK", "NETWORK_HEALTH", "operator:noc", ["REQ-NETWORK"]),
    ]
    normal_flows = _flows()
    scenarios = [
        _scenario("HG-ECAC-001", "Normal connectivity", "Verified simulated incident and route records traverse an uncongested link.",
                  capacity=8.0, latency=18, loss=0.0001, evidence=normal_evidence, flows=normal_flows, seed=101),
        _scenario("HG-ECAC-002", "Emergency traffic congestion", "Competing emergency and background traffic contends for a constrained bottleneck.",
                  capacity=0.35, latency=45, loss=0.01, congestion="CONGESTED",
                  flows=_flows(incident_rate=0.45, route_rate=0.35, background_rate=0.8, extra=True),
                  seed=202, failures=["COMPETING_TRAFFIC_CONGESTION"]),
        _scenario("HG-ECAC-003", "High latency and packet loss", "A degraded link adds propagation delay and deterministic packet-loss draws.",
                  capacity=2.0, latency=420, processing_delay_ms=20, loss=0.18, congestion="DEGRADED",
                  flows=_flows(incident_rate=0.12, route_rate=0.1), seed=303,
                  failures=["HIGH_LATENCY", "PACKET_LOSS"]),
        _scenario("HG-ECAC-004", "Stale and conflicting route reports", "Route reports are stale or marked conflicting; neither transmission nor receipt resolves the conflict.",
                  capacity=5.0, latency=30, loss=0.001,
                  requirements=_base_requirements(route_conflict=True),
                  evidence=[
                      _evidence("EVID-INCIDENT", "INCIDENT_REPORT", "agency:incident-command", ["REQ-INCIDENT"]),
                      _evidence("EVID-ROUTE-OLD", "ROUTE_STATUS", "agency:field-unit", ["REQ-ROUTE"], source_age_seconds=900, conflict=ConflictStatus.CONFLICTING),
                      _evidence("EVID-ROUTE-NEW", "ROUTE_STATUS", "agency:field-unit", ["REQ-ROUTE"], conflict=ConflictStatus.CONFLICTING, payload_bytes=1024),
                  ],
                  flows=[TrafficFlow(**{**item.model_dump(), "evidence_ids": (["EVID-INCIDENT"] if item.flow_id == "FLOW-INCIDENT" else ["EVID-ROUTE-NEW"] if item.flow_id == "FLOW-ROUTE" else [])}) for item in _flows()],
                  seed=404, failures=["STALE_ROUTE_REPORT", "UNRESOLVED_EVIDENCE_CONFLICT"]),
        _scenario("HG-ECAC-005", "Missing mandatory route evidence", "The mandatory route-status object is absent; no controller may infer that requirement is satisfied.",
                  capacity=6.0, latency=24, loss=0.001,
                  evidence=[_evidence("EVID-INCIDENT", "INCIDENT_REPORT", "agency:incident-command", ["REQ-INCIDENT"])],
                  flows=[flow for flow in _flows() if flow.flow_id != "FLOW-ROUTE"], seed=505,
                  failures=["MISSING_MANDATORY_ROUTE_EVIDENCE"]),
        _scenario("HG-ECAC-006", "Temporary disconnection and recovery", "The link is unavailable until the configured recovery offset; queued messages compete after recovery.",
                  capacity=2.0, latency=35, loss=0.002, link=False, duration_ms=4000,
                  changes=[NetworkChange(start_offset_ms=0, end_offset_ms=1000, link_available=False, bottleneck_capacity_mbps=0),
                           NetworkChange(start_offset_ms=1000, end_offset_ms=4000, link_available=True, bottleneck_capacity_mbps=2.0)],
                  flows=_flows(duration_ms=4000),
                  requirements=_base_requirements(incident_deadline_ms=3500, route_deadline_ms=3800), seed=606,
                  failures=["TEMPORARY_LINK_DISCONNECTION", "LINK_RECOVERY_AT_1000_MS"]),
        _scenario("HG-ECAC-007", "Competing agencies and deadlines", "Several agency/application flows share one link while incident and route evidence have different deadlines.",
                  capacity=0.8, latency=80, loss=0.01, congestion="BUSY",
                  flows=_flows(incident_rate=0.3, route_rate=0.18, background_rate=0.4, extra=True),
                  requirements=_base_requirements(incident_deadline_ms=900, route_deadline_ms=2600),
                  seed=707, failures=["COMPETING_AGENCY_DEADLINES"]),
        _scenario("HG-ECAC-008", "Rapidly fluctuating network conditions", "Capacity, latency, loss, congestion and availability change across deterministic time windows.",
                  capacity=3.0, latency=30, loss=0.002, duration_ms=4000,
                  changes=[NetworkChange(start_offset_ms=0, end_offset_ms=500, bottleneck_capacity_mbps=5, latency_ms=25, packet_loss_probability=0.001, congestion_state="NORMAL"),
                           NetworkChange(start_offset_ms=500, end_offset_ms=1000, bottleneck_capacity_mbps=0.5, latency_ms=180, packet_loss_probability=0.08, congestion_state="CONGESTED"),
                           NetworkChange(start_offset_ms=1000, end_offset_ms=1400, link_available=False, bottleneck_capacity_mbps=0, latency_ms=300, packet_loss_probability=0.2, congestion_state="DISCONNECTED"),
                           NetworkChange(start_offset_ms=1400, end_offset_ms=4000, bottleneck_capacity_mbps=2.5, latency_ms=60, packet_loss_probability=0.02, congestion_state="RECOVERING", link_available=True)],
                  flows=_flows(duration_ms=4000, incident_rate=0.15, route_rate=0.1, background_rate=0.3, extra=True),
                  requirements=_base_requirements(incident_deadline_ms=3000, route_deadline_ms=3800),
                  seed=808, failures=["RAPID_CAPACITY_FLUCTUATION", "TRANSIENT_DISCONNECTION"]),
    ]
    return {scenario.scenario_id: scenario for scenario in scenarios}


SCENARIOS = build_scenarios()


def list_scenarios() -> list[ECR5GScenario]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> ECR5GScenario | None:
    return SCENARIOS.get(scenario_id)
