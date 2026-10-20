from __future__ import annotations

from typing import Optional

from Backend.evidence_engine.models import (
    EvidenceAssessment as EngineEvidenceAssessment,
    EvidenceStatus as EngineEvidenceStatus,
    EvidenceStrength,
)

from Backend.risk_engine.models import (
    AIAnalysis,
    DecisionContext,
    EvidenceAssessment as RiskEvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus as RiskEvidenceStatus,
    RiskAssessment,
)

from Backend.risk_engine.engine import RiskEngine


# ============================================================
# EVIDENCE STRENGTH → RISK EVIDENCE QUALITY
# ============================================================

def map_evidence_quality(
    strength: EvidenceStrength,
) -> EvidenceQuality:

    mapping = {
        EvidenceStrength.STRONG: EvidenceQuality.STRONG,
        EvidenceStrength.MODERATE: EvidenceQuality.MODERATE,
        EvidenceStrength.WEAK: EvidenceQuality.WEAK,
        EvidenceStrength.INSUFFICIENT: EvidenceQuality.INSUFFICIENT,
    }

    return mapping.get(
        strength,
        EvidenceQuality.INSUFFICIENT,
    )


# ============================================================
# EVIDENCE STATUS → RISK STATUS
# ============================================================

def map_evidence_status(
    status: EngineEvidenceStatus,
) -> RiskEvidenceStatus:

    mapping = {
        EngineEvidenceStatus.SUFFICIENT:
            RiskEvidenceStatus.SUFFICIENT,

        EngineEvidenceStatus.CONFLICTING:
            RiskEvidenceStatus.CONFLICTING,

        EngineEvidenceStatus.INSUFFICIENT:
            RiskEvidenceStatus.INSUFFICIENT,

        EngineEvidenceStatus.AMBIGUOUS:
            RiskEvidenceStatus.AMBIGUOUS,

        EngineEvidenceStatus.PARTIALLY_ESTABLISHED:
            RiskEvidenceStatus.SUFFICIENT,

        EngineEvidenceStatus.ABSENCE_NOT_ESTABLISHED:
            RiskEvidenceStatus.INSUFFICIENT,

        EngineEvidenceStatus.NOT_APPLICABLE:
            RiskEvidenceStatus.SUFFICIENT,
    }

    return mapping.get(
        status,
        RiskEvidenceStatus.INSUFFICIENT,
    )


# ============================================================
# BUILD RISK ENGINE EVIDENCE ASSESSMENT
# ============================================================

def build_risk_evidence_assessment(
    evidence: EngineEvidenceAssessment,
) -> RiskEvidenceAssessment:

    return RiskEvidenceAssessment(
        quality=map_evidence_quality(
            evidence.overall_strength
        ),

        supporting_count=evidence.supporting_count,

        contradicting_count=evidence.contradicting_count,

        primary_source_count=evidence.primary_source_count,

        official_source_count=evidence.official_source_count,

        source_diversity=evidence.source_diversity,

        evidence_status=map_evidence_status(
            evidence.overall_status
        ),

        missing_evidence=list(
            evidence.missing_evidence
        ),
    )


# ============================================================
# MAIN INTEGRATION
# ============================================================

def assess_with_evidence_engine(
    *,
    decision_context: DecisionContext,
    evidence_assessment: EngineEvidenceAssessment,
    ai_analysis: AIAnalysis,
) -> RiskAssessment:

    risk_evidence = build_risk_evidence_assessment(
        evidence_assessment
    )

    engine = RiskEngine()

    assessment = engine.assess(
        context=decision_context,
        evidence=risk_evidence,
        ai=ai_analysis,
    )

    return assessment


# ============================================================
# SERIALIZATION
# ============================================================

def risk_assessment_to_dict(
    assessment: RiskAssessment,
) -> dict:

    return {
        "risk_level": assessment.risk_level.value,
        "risk_score": assessment.risk_score,
        "escalation_level": assessment.escalation_level.value,
        "human_review_required": assessment.human_review_required,
        "mandatory_review": assessment.mandatory_review,
        "reasons": list(assessment.reasons),
        "blocking_conditions": list(
            assessment.blocking_conditions
        ),
        "recommended_action": assessment.recommended_action,
        "evidence_quality": assessment.evidence_quality.value,
        "evidence_status": assessment.evidence_status.value,
        "ai_confidence": assessment.ai_confidence,
        "governance_decision": assessment.governance_decision,
    }