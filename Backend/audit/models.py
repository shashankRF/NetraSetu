from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditRecord:

    audit_id: str

    timestamp: str

    question: str

    pipeline_version: str

    model: str

    execution_id: str | None = None

    event_type: str = "QUESTION_ANALYSIS"

    execution_status: str = "COMPLETED"

    error_details: str | None = None

    scenario_id: str | None = None

    scenario_title: str | None = None

    step_id: str | None = None

    step_title: str | None = None

    workflow_stages: List[str] = field(
        default_factory=list
    )

    provenance: str = "RUNTIME_EXECUTION"

    domain: str | None = None

    jurisdiction: str | None = None

    retrieved_evidence: List[Dict[str, Any]] = field(
        default_factory=list
    )

    evidence_classification: Dict[str, Any] = field(
        default_factory=dict
    )

    evidence_assessment: Dict[str, Any] = field(
        default_factory=dict
    )

    absence_verification: List[Dict[str, Any]] = field(
        default_factory=list
    )

    gap_analysis: Dict[str, Any] = field(
        default_factory=dict
    )

    risk_assessment: Dict[str, Any] = field(
        default_factory=dict
    )

    final_synthesis: Dict[str, Any] = field(
        default_factory=dict
    )

    claim_evidence_mappings: List[Dict[str, Any]] = field(
        default_factory=list
    )

    human_review_required: bool = False

    human_reviewer: str = ""

    human_action: str = ""

    reviewer_modifications: str = ""

    final_decision: str = ""

    notes: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:

        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "question": self.question,
            "pipeline_version": self.pipeline_version,
            "model": self.model,
            "execution_id": self.execution_id,
            "event_type": self.event_type,
            "execution_status": self.execution_status,
            "error_details": self.error_details,
            "scenario_id": self.scenario_id,
            "scenario_title": self.scenario_title,
            "step_id": self.step_id,
            "step_title": self.step_title,
            "workflow_stages": self.workflow_stages,
            "provenance": self.provenance,
            "domain": self.domain,
            "jurisdiction": self.jurisdiction,
            "retrieved_evidence": self.retrieved_evidence,
            "evidence_classification": self.evidence_classification,
            "evidence_assessment": self.evidence_assessment,
            "absence_verification": self.absence_verification,
            "gap_analysis": self.gap_analysis,
            "risk_assessment": self.risk_assessment,
            "final_synthesis": self.final_synthesis,
            "claim_evidence_mappings": (
                self.claim_evidence_mappings
            ),
            "human_review_required": (
                self.human_review_required
            ),
            "human_reviewer": self.human_reviewer,
            "human_action": self.human_action,
            "reviewer_modifications": (
                self.reviewer_modifications
            ),
            "final_decision": self.final_decision,
            "notes": self.notes,
        }


@dataclass
class ReviewEvent:

    audit_id: str

    timestamp: str

    human_action: str

    final_decision: str

    execution_id: str | None = None

    reviewer: str = "Human reviewer"

    reviewer_modifications: str | None = None

    reviewer_reason: str | None = None

    def to_dict(self) -> Dict[str, Any]:

        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "human_action": self.human_action,
            "final_decision": self.final_decision,
            "execution_id": self.execution_id,
            "reviewer": self.reviewer,
            "reviewer_modifications": self.reviewer_modifications,
            "reviewer_reason": self.reviewer_reason,
        }
