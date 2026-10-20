from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class JurisdictionRole(str, Enum):
    HOST = "HOST"
    INTERNATIONAL = "INTERNATIONAL"
    REGIONAL_COMPARATIVE = "REGIONAL_COMPARATIVE"
    UNKNOWN = "UNKNOWN"


class RegionalRelationshipType(str, Enum):
    HOST_APPLICABLE = "HOST APPLICABLE"
    INTERNATIONAL_TECHNICAL_REQUIREMENT = "INTERNATIONAL TECHNICAL REQUIREMENT"
    REGIONAL_COMPARATIVE_REQUIREMENT = "REGIONAL COMPARATIVE REQUIREMENT"
    ADDITIONAL_REGIONAL_CONTROL = "ADDITIONAL REGIONAL CONTROL"
    POTENTIAL_POLICY_GAP = "POTENTIAL POLICY GAP"
    POTENTIAL_BEST_PRACTICE_DIFFERENCE = "POTENTIAL BEST-PRACTICE DIFFERENCE"
    DIFFERENT_TERMINOLOGY = "DIFFERENT TERMINOLOGY"
    DIFFERENT_IMPLEMENTATION_APPROACH = "DIFFERENT IMPLEMENTATION APPROACH"
    NOT_COMPARABLE = "NOT COMPARABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"
    ABSENCE_NOT_ESTABLISHED = "ABSENCE NOT ESTABLISHED"


class RegionalGapStatus(str, Enum):
    ESTABLISHED_GAP = "ESTABLISHED GAP"
    PARTIALLY_COVERED = "PARTIALLY COVERED"
    POTENTIAL_GAP_NOT_ESTABLISHED = "POTENTIAL GAP - NOT ESTABLISHED"
    NO_ESTABLISHED_GAP = "NO ESTABLISHED GAP"
    NOT_A_GAP = "NOT A GAP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"
    NOT_APPLICABLE = "NOT APPLICABLE"
    ABSENCE_NOT_ESTABLISHED = "ABSENCE NOT ESTABLISHED"


class RegionalActionType(str, Enum):
    FIX = "FIX"
    VERIFY = "VERIFY"
    INVESTIGATE = "INVESTIGATE"
    NO_ACTION = "NO ACTION"


class RegionalCoverageStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    NOT_ESTABLISHED = "NOT ESTABLISHED"


@dataclass
class RegionalEvidenceItem:
    evidence_id: str
    source: str
    source_type: str
    country: str
    document: str
    requirement_text: str
    requirement_type: str = "MANDATORY"
    applicability: str = "DIRECT"
    evidence_role: str = "SUPPORTING"
    evidence_status: str = "ACTIVE"
    confidence: float = 0.85
    retrieval_provenance: str = "RAG_RETRIEVAL"
    clause: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    jurisdiction_role: JurisdictionRole = JurisdictionRole.UNKNOWN
    comparative_relevance: str = "DIRECT"
    applicability_reason: str = ""
    regional_relationship: RegionalRelationshipType = RegionalRelationshipType.HOST_APPLICABLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "source_type": self.source_type,
            "country": self.country,
            "document": self.document,
            "clause": self.clause,
            "section": self.section,
            "page": self.page,
            "requirement_text": self.requirement_text,
            "requirement_type": self.requirement_type,
            "applicability": self.applicability,
            "evidence_role": self.evidence_role,
            "evidence_status": self.evidence_status,
            "confidence": self.confidence,
            "retrieval_provenance": self.retrieval_provenance,
            "jurisdiction_role": self.jurisdiction_role.value,
            "comparative_relevance": self.comparative_relevance,
            "applicability_reason": self.applicability_reason,
            "regional_relationship": self.regional_relationship.value,
        }


@dataclass
class RegionalComparisonMapping:
    mapping_id: str
    international_requirement: Dict[str, Any]
    host_provision: Optional[Dict[str, Any]]
    regional_provision: Optional[Dict[str, Any]]
    coverage: str
    missing_element: Optional[str]
    gap_status: RegionalGapStatus
    action: RegionalActionType
    reason: str
    impact: str
    remediation: str
    counter_evidence: List[Dict[str, Any]] = field(default_factory=list)
    limitations: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "international_requirement": self.international_requirement,
            "host_provision": self.host_provision,
            "regional_provision": self.regional_provision,
            "coverage": self.coverage,
            "missing_element": self.missing_element,
            "gap_status": self.gap_status.value,
            "action": self.action.value,
            "reason": self.reason,
            "impact": self.impact,
            "remediation": self.remediation,
            "counter_evidence": self.counter_evidence,
            "limitations": self.limitations,
        }


@dataclass
class RegionalComparativeAnalysisResult:
    comparison_id: str
    host_jurisdiction: str
    regional_jurisdictions: List[str]
    regional_mode: str
    international_requirements: List[Dict[str, Any]]
    host_requirements: List[Dict[str, Any]]
    regional_requirements: List[Dict[str, Any]]
    mappings: List[Dict[str, Any]]
    coverage_status: str
    gap_status: RegionalGapStatus
    action: RegionalActionType
    evidence_ids: List[str]
    counter_evidence_ids: List[str]
    applicability: Dict[str, Any]
    comparative_relevance: str
    reasoning: str
    impact: str
    remediation: str
    counter_evidence_summary: str
    limitations: str
    human_review_required: bool
    regional_coverage: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "host_jurisdiction": self.host_jurisdiction,
            "regional_jurisdictions": self.regional_jurisdictions,
            "regional_mode": self.regional_mode,
            "international_requirements": self.international_requirements,
            "host_requirements": self.host_requirements,
            "regional_requirements": self.regional_requirements,
            "mappings": self.mappings,
            "coverage_status": self.coverage_status,
            "gap_status": self.gap_status.value,
            "action": self.action.value,
            "evidence_ids": self.evidence_ids,
            "counter_evidence_ids": self.counter_evidence_ids,
            "applicability": self.applicability,
            "comparative_relevance": self.comparative_relevance,
            "reasoning": self.reasoning,
            "impact": self.impact,
            "remediation": self.remediation,
            "counter_evidence_summary": self.counter_evidence_summary,
            "limitations": self.limitations,
            "human_review_required": self.human_review_required,
            "regional_coverage": self.regional_coverage,
        }
