from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    INTERNATIONAL_TECHNICAL_STANDARD = "INTERNATIONAL_TECHNICAL_STANDARD"
    INTERNATIONAL_RECOMMENDATION = "INTERNATIONAL_RECOMMENDATION"
    NATIONAL_REGULATION = "NATIONAL_REGULATION"
    NATIONAL_POLICY = "NATIONAL_POLICY"
    NATIONAL_TECHNICAL_STANDARD = "NATIONAL_TECHNICAL_STANDARD"
    INDUSTRY_STANDARD = "INDUSTRY_STANDARD"
    GUIDANCE = "GUIDANCE"
    SECURITY_REQUIREMENT = "SECURITY_REQUIREMENT"
    TECHNICAL_SPECIFICATION = "TECHNICAL_SPECIFICATION"
    LAW = "LAW"
    RULE = "RULE"
    LOCAL_OPERATOR_POLICY = "LOCAL_OPERATOR_POLICY"
    ORGANIZATIONAL_REQUIREMENT = "ORGANIZATIONAL_REQUIREMENT"
    OTHER = "OTHER"


class RequirementType(str, Enum):
    MANDATORY = "MANDATORY"
    ADVISORY = "ADVISORY"
    TECHNICAL = "TECHNICAL"
    UNKNOWN = "UNKNOWN"


class ApplicabilityStatus(str, Enum):
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class MappingRelationship(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    ADDITIONAL_NATIONAL_REQUIREMENT = "ADDITIONAL_NATIONAL_REQUIREMENT"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    CONFLICT = "CONFLICT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_ADDRESSED_IN_EXAMINED_SOURCES = "NOT_ADDRESSED_IN_EXAMINED_SOURCES"
    POTENTIAL_GAP_NOT_ESTABLISHED = "POTENTIAL_GAP_NOT_ESTABLISHED"
    UNCERTAIN_MAPPING = "UNCERTAIN_MAPPING"


class GapStatus(str, Enum):
    ESTABLISHED_GAP = "ESTABLISHED GAP"
    POTENTIAL_GAP_NOT_ESTABLISHED = "POTENTIAL GAP — NOT ESTABLISHED"
    NO_GAP_ESTABLISHED = "NO GAP ESTABLISHED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY EQUIVALENT"
    ADDITIONAL_NATIONAL_REQUIREMENT = "ADDITIONAL NATIONAL REQUIREMENT"
    NOT_ADDRESSED_IN_EXAMINED_SOURCES = "NOT ADDRESSED IN EXAMINED SOURCES"
    LOCAL_REQUIREMENT_NOT_NATIONAL_GAP = "LOCAL REQUIREMENT — NOT NATIONAL GAP"


class GapAction(str, Enum):
    FIX = "FIX"
    VERIFY = "VERIFY"
    INVESTIGATE = "INVESTIGATE"
    NO_ACTION = "NO ACTION"


class HypothesisStatus(str, Enum):
    ESTABLISHED = "ESTABLISHED"
    SUPPORTED = "SUPPORTED"
    POSSIBLE = "POSSIBLE"
    WEAKENED = "WEAKENED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceRole(str, Enum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    LIMITING = "LIMITING"
    CONTEXTUAL = "CONTEXTUAL"


@dataclass
class ExtractedRequirement:
    requirement_id: str
    source: str
    source_type: SourceType
    document: str
    requirement_text: str
    requirement_summary: str
    technology_domain: str
    jurisdiction: str
    status: RequirementType
    applicability: ApplicabilityStatus
    evidence_id: str
    clause: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "source": self.source,
            "source_type": self.source_type.value,
            "document": self.document,
            "clause": self.clause,
            "section": self.section,
            "page": self.page,
            "requirement_text": self.requirement_text,
            "requirement_summary": self.requirement_summary,
            "technology_domain": self.technology_domain,
            "jurisdiction": self.jurisdiction,
            "status": self.status.value,
            "applicability": self.applicability.value,
            "evidence_id": self.evidence_id,
        }


@dataclass
class CounterEvidenceItem:
    evidence_id: str
    role: EvidenceRole
    relationship: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "role": self.role.value,
            "relationship": self.relationship,
            "explanation": self.explanation,
        }


@dataclass
class PolicyStandardMappingRecord:
    mapping_id: str
    international_requirement: Dict[str, Any]
    national_provision: Dict[str, Any]
    applicability: str
    relationship: MappingRelationship
    reason: str
    missing_element: Optional[str] = None
    counter_evidence: List[Dict[str, Any]] = field(default_factory=list)
    evidence_confidence: float = 0.0
    mapping_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "international_requirement": self.international_requirement,
            "national_provision": self.national_provision,
            "applicability": self.applicability,
            "relationship": self.relationship.value,
            "reason": self.reason,
            "missing_element": self.missing_element,
            "counter_evidence": self.counter_evidence,
            "evidence_confidence": round(self.evidence_confidence, 4),
            "mapping_confidence": round(self.mapping_confidence, 4),
        }


@dataclass
class GenuineGapRecord:
    gap_id: str
    international_requirement: str
    source: str
    international_evidence_ids: List[str]
    national_provision: str
    national_evidence_ids: List[str]
    applicability: str = "DIRECT"
    coverage: str = "Not Covered"
    counter_evidence: str = "No meaningful counter-evidence was identified in the supplied Knowledge Base evidence set."
    why: str = ""
    missing_element: Optional[str] = None
    status: GapStatus = GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED
    impact: str = ""
    action: GapAction = GapAction.VERIFY
    required_action_detail: str = ""
    gates_passed: List[str] = field(default_factory=list)
    gates_unresolved: List[str] = field(default_factory=list)
    authority_status: str = "UNKNOWN"
    scope_limitations: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "international_requirement": self.international_requirement,
            "source": self.source,
            "international_evidence_ids": self.international_evidence_ids,
            "national_provision": self.national_provision,
            "national_evidence_ids": self.national_evidence_ids,
            "applicability": self.applicability,
            "coverage": self.coverage,
            "counter_evidence": self.counter_evidence,
            "why": self.why,
            "missing_element": self.missing_element,
            "status": self.status.value,
            "impact": self.impact,
            "action": self.action.value,
            "required_action_detail": self.required_action_detail,
            "gates_passed": self.gates_passed,
            "gates_unresolved": self.gates_unresolved,
            "authority_status": self.authority_status,
            "scope_limitations": self.scope_limitations,
        }


@dataclass
class TechnicalImplication:
    implication_id: str
    implication: str
    evidence_ids: List[str]
    basis: str
    status: str  # ESTABLISHED, SUPPORTED, POSSIBLE, NOT_ESTABLISHED
    limitation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "implication_id": self.implication_id,
            "implication": self.implication,
            "evidence_ids": self.evidence_ids,
            "basis": self.basis,
            "status": self.status,
            "limitation": self.limitation,
        }


@dataclass
class RegulatoryImplication:
    implication_id: str
    implication: str
    evidence_ids: List[str]
    source_type: str
    jurisdiction: str
    applicability: str
    status: str  # ESTABLISHED, PARTIALLY_ESTABLISHED, NOT_ESTABLISHED, UNCERTAIN
    basis: str
    limitation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "implication_id": self.implication_id,
            "implication": self.implication,
            "evidence_ids": self.evidence_ids,
            "source_type": self.source_type,
            "jurisdiction": self.jurisdiction,
            "applicability": self.applicability,
            "status": self.status,
            "basis": self.basis,
            "limitation": self.limitation,
        }


@dataclass
class HypothesisEvaluation:
    hypothesis: str
    status: HypothesisStatus
    evidence_ids: List[str]
    supporting_evidence: List[str]
    limiting_counter_evidence: List[str]
    confidence: float
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis": self.hypothesis,
            "status": self.status.value,
            "evidence_ids": self.evidence_ids,
            "supporting_evidence": self.supporting_evidence,
            "limiting_counter_evidence": self.limiting_counter_evidence,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
        }


@dataclass
class DecisionSpecificSufficiency:
    overall_evidence: str
    requirement_mapping: str
    risk_assessment: str
    regulatory_conclusion: str
    root_cause: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_evidence": self.overall_evidence,
            "requirement_mapping": self.requirement_mapping,
            "risk_assessment": self.risk_assessment,
            "regulatory_conclusion": self.regulatory_conclusion,
            "root_cause": self.root_cause,
        }
