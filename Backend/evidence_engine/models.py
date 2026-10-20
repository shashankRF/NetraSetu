from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EvidenceRole(str, Enum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    LIMITING = "LIMITING"
    CONTEXTUAL = "CONTEXTUAL"


class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    CONFLICTING = "CONFLICTING"
    PARTIALLY_ESTABLISHED = "PARTIALLY_ESTABLISHED"
    INSUFFICIENT = "INSUFFICIENT"
    AMBIGUOUS = "AMBIGUOUS"
    ABSENCE_NOT_ESTABLISHED = "ABSENCE_NOT_ESTABLISHED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"


class Applicability(str, Enum):
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class RequirementType(str, Enum):
    MANDATORY = "MANDATORY"
    ADVISORY = "ADVISORY"
    TECHNICAL = "TECHNICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class EvidenceMetadata:
    document: str = ""
    publisher: str = ""
    source_type: str = ""
    jurisdiction: str = ""

    page: Optional[int] = None
    section: str = ""
    clause: str = ""

    chunk_id: Optional[int] = None
    retrieval_rank: Optional[int] = None

    version: str = ""
    publication_date: str = ""
    effective_date: str = ""
    expiry_date: str = ""


@dataclass
class EvidenceItem:
    evidence_id: str
    claim_id: str

    claim_text: str
    evidence_text: str

    role: EvidenceRole
    strength: EvidenceStrength

    applicability: Applicability
    requirement_type: RequirementType

    metadata: EvidenceMetadata

    confidence: float = 0.0
    limitations: List[str] = field(default_factory=list)


@dataclass
class ClaimAssessment:
    claim_id: str
    claim_text: str

    supporting: List[EvidenceItem] = field(default_factory=list)
    contradicting: List[EvidenceItem] = field(default_factory=list)
    limiting: List[EvidenceItem] = field(default_factory=list)
    contextual: List[EvidenceItem] = field(default_factory=list)

    status: EvidenceStatus = EvidenceStatus.INSUFFICIENT

    applicability: Applicability = Applicability.NOT_ESTABLISHED

    confidence: float = 0.0

    limitations: List[str] = field(default_factory=list)


@dataclass
class AbsenceVerification:
    claim: str

    verification_status: EvidenceStatus

    sources_examined: int = 0
    authoritative_sources_examined: int = 0

    positive_evidence: int = 0
    negative_evidence: int = 0

    search_scope: List[str] = field(default_factory=list)

    limitations: List[str] = field(default_factory=list)


@dataclass
class EvidenceAssessment:
    claims: List[ClaimAssessment] = field(default_factory=list)

    absence_verifications: List[AbsenceVerification] = field(
        default_factory=list
    )

    overall_status: EvidenceStatus = EvidenceStatus.INSUFFICIENT
    overall_strength: EvidenceStrength = EvidenceStrength.INSUFFICIENT

    supporting_count: int = 0
    contradicting_count: int = 0

    primary_source_count: int = 0
    official_source_count: int = 0

    source_diversity: int = 0

    missing_evidence: List[str] = field(default_factory=list)

    overall_confidence: float = 0.0