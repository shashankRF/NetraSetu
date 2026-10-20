from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


# ============================================================
# RISK LEVEL
# ============================================================

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================
# ESCALATION LEVEL
# ============================================================

class EscalationLevel(str, Enum):
    AUTO_RESPONSE = "AUTO_RESPONSE"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    DOMAIN_EXPERT = "DOMAIN_EXPERT"
    SENIOR_AUTHORITY = "SENIOR_AUTHORITY"


# ============================================================
# DECISION IMPACT
# ============================================================

class DecisionImpact(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    OPERATIONAL = "OPERATIONAL"
    REGULATORY = "REGULATORY"
    SECURITY = "SECURITY"
    SAFETY = "SAFETY"
    STRATEGIC = "STRATEGIC"


# ============================================================
# EVIDENCE QUALITY
# ============================================================

class EvidenceQuality(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"


# ============================================================
# EVIDENCE STATUS
# ============================================================

class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"
    AMBIGUOUS = "AMBIGUOUS"


# ============================================================
# AUTHORITY REQUIREMENT
# ============================================================

class AuthorityRequirement(str, Enum):
    NONE = "NONE"
    ANALYST = "ANALYST"
    DOMAIN_EXPERT = "DOMAIN_EXPERT"
    SENIOR_AUTHORITY = "SENIOR_AUTHORITY"


# ============================================================
# EVIDENCE ASSESSMENT
# ============================================================

@dataclass
class EvidenceAssessment:

    quality: EvidenceQuality = EvidenceQuality.MODERATE

    # Evidence balance
    supporting_count: int = 0
    contradicting_count: int = 0

    # Source authority
    primary_source_count: int = 0
    official_source_count: int = 0

    # Diversity of independent sources
    source_diversity: int = 0

    # Overall evidence state
    evidence_status: EvidenceStatus = (
        EvidenceStatus.SUFFICIENT
    )

    # Evidence that the system knows it still needs
    missing_evidence: List[str] = field(
        default_factory=list
    )


# ============================================================
# AI ANALYSIS
# ============================================================

@dataclass
class AIAnalysis:

    # Model confidence in its interpretation
    confidence: float = 0.0

    # Claim-level statistics
    factual_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0

    # Estimated hallucination / unsupported generation risk
    hallucination_risk: float = 0.0

    # Whether this situation is outside established patterns
    novel_situation: bool = False


# ============================================================
# DECISION CONTEXT
# ============================================================

@dataclass
class DecisionContext:

    # HackGrid domain
    domain: str

    # Consequence category
    decision_impact: DecisionImpact

    # Additional consequence score: 0–100
    consequence_score: int = 0

    # Required human authority
    authority_requirement: AuthorityRequirement = (
        AuthorityRequirement.NONE
    )

    # Governance / operational properties
    sensitive_information: bool = False
    external_action: bool = False
    production_change: bool = False

    # Regulatory / legal interpretation
    legal_or_regulatory_interpretation: bool = False

    # High-consequence environments
    affects_public_safety: bool = False
    affects_critical_infrastructure: bool = False


# ============================================================
# FINAL RISK ASSESSMENT
# ============================================================

@dataclass
class RiskAssessment:

    risk_level: RiskLevel
    risk_score: int

    escalation_level: EscalationLevel

    human_review_required: bool
    mandatory_review: bool

    reasons: List[str] = field(
        default_factory=list
    )

    blocking_conditions: List[str] = field(
        default_factory=list
    )

    recommended_action: str = ""

    evidence_quality: EvidenceQuality = (
        EvidenceQuality.MODERATE
    )

    evidence_status: EvidenceStatus = (
        EvidenceStatus.SUFFICIENT
    )

    ai_confidence: float = 0.0

    governance_decision: str = ""