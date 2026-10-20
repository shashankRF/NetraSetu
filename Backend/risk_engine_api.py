from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .risk_engine import (
    RiskEngine,
    AIAnalysis,
    DecisionContext,
    EvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus,
    DecisionImpact,
    AuthorityRequirement,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/risk",
    tags=["Risk Engine"],
)


# ============================================================
# EVIDENCE REQUEST
# ============================================================

class EvidenceRequest(BaseModel):

    quality: EvidenceQuality = (
        EvidenceQuality.MODERATE
    )

    supporting_count: int = Field(
        default=0,
        ge=0,
    )

    contradicting_count: int = Field(
        default=0,
        ge=0,
    )

    primary_source_count: int = Field(
        default=0,
        ge=0,
    )

    official_source_count: int = Field(
        default=0,
        ge=0,
    )

    source_diversity: int = Field(
        default=0,
        ge=0,
    )

    evidence_status: EvidenceStatus = (
        EvidenceStatus.SUFFICIENT
    )

    missing_evidence: List[str] = Field(
        default_factory=list
    )


# ============================================================
# AI REQUEST
# ============================================================

class AIRequest(BaseModel):

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    factual_claims: int = Field(
        default=0,
        ge=0,
    )

    supported_claims: int = Field(
        default=0,
        ge=0,
    )

    unsupported_claims: int = Field(
        default=0,
        ge=0,
    )

    hallucination_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    novel_situation: bool = False


# ============================================================
# DECISION REQUEST
# ============================================================

class DecisionRequest(BaseModel):

    domain: str

    decision_impact: DecisionImpact

    consequence_score: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    authority_requirement: AuthorityRequirement = (
        AuthorityRequirement.NONE
    )

    sensitive_information: bool = False

    external_action: bool = False

    production_change: bool = False

    legal_or_regulatory_interpretation: bool = False

    affects_public_safety: bool = False

    affects_critical_infrastructure: bool = False


# ============================================================
# COMPLETE REQUEST
# ============================================================

class RiskRequest(BaseModel):

    decision: DecisionRequest

    evidence: EvidenceRequest

    ai: AIRequest


# ============================================================
# ENGINE INSTANCE
# ============================================================

engine = RiskEngine()


# ============================================================
# ASSESS ENDPOINT
# ============================================================

@router.post("/assess")
def assess_risk(
    request: RiskRequest,
):

    # --------------------------------------------------------
    # Convert API request → internal DecisionContext
    # --------------------------------------------------------

    context = DecisionContext(

        domain=request.decision.domain,

        decision_impact=(
            request.decision.decision_impact
        ),

        consequence_score=(
            request.decision.consequence_score
        ),

        authority_requirement=(
            request.decision.authority_requirement
        ),

        sensitive_information=(
            request.decision.sensitive_information
        ),

        external_action=(
            request.decision.external_action
        ),

        production_change=(
            request.decision.production_change
        ),

        legal_or_regulatory_interpretation=(
            request.decision
            .legal_or_regulatory_interpretation
        ),

        affects_public_safety=(
            request.decision
            .affects_public_safety
        ),

        affects_critical_infrastructure=(
            request.decision
            .affects_critical_infrastructure
        ),
    )

    # --------------------------------------------------------
    # Convert API request → EvidenceAssessment
    # --------------------------------------------------------

    evidence = EvidenceAssessment(

        quality=request.evidence.quality,

        supporting_count=(
            request.evidence.supporting_count
        ),

        contradicting_count=(
            request.evidence.contradicting_count
        ),

        primary_source_count=(
            request.evidence.primary_source_count
        ),

        official_source_count=(
            request.evidence.official_source_count
        ),

        source_diversity=(
            request.evidence.source_diversity
        ),

        evidence_status=(
            request.evidence.evidence_status
        ),

        missing_evidence=(
            request.evidence.missing_evidence
        ),
    )

    # --------------------------------------------------------
    # Convert API request → AIAnalysis
    # --------------------------------------------------------

    ai = AIAnalysis(

        confidence=request.ai.confidence,

        factual_claims=request.ai.factual_claims,

        supported_claims=request.ai.supported_claims,

        unsupported_claims=(
            request.ai.unsupported_claims
        ),

        hallucination_risk=(
            request.ai.hallucination_risk
        ),

        novel_situation=(
            request.ai.novel_situation
        ),
    )

    # --------------------------------------------------------
    # Run deterministic governance engine
    # --------------------------------------------------------

    result = engine.assess(

        context=context,

        evidence=evidence,

        ai=ai,
    )

    # --------------------------------------------------------
    # Return structured API response
    # --------------------------------------------------------

    return {

        "risk": {

            "level": (
                result.risk_level.value
            ),

            "score": (
                result.risk_score
            ),
        },

        "governance": {

            "escalation_level": (
                result
                .escalation_level
                .value
            ),

            "human_review_required": (
                result
                .human_review_required
            ),

            "mandatory_review": (
                result
                .mandatory_review
            ),

            "decision": (
                result
                .governance_decision
            ),
        },

        "evidence": {

            "quality": (
                result
                .evidence_quality
                .value
            ),

            "status": (
                result
                .evidence_status
                .value
            ),
        },

        "ai": {

            "confidence": (
                result
                .ai_confidence
            ),
        },

        "reasons": (
            result.reasons
        ),

        "blocking_conditions": (
            result
            .blocking_conditions
        ),

        "recommended_action": (
            result
            .recommended_action
        ),
    }