from .models import (
    AIAnalysis,
    DecisionContext,
    EvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus,
    EscalationLevel,
)

from .policy import (
    IMPACT_SCORES,
    AUTHORITY_LEVEL,
    ESCALATION_RANK,
)


# ============================================================
# DECISION IMPACT
# ============================================================

def calculate_base_score(
    context: DecisionContext,
) -> int:

    score = IMPACT_SCORES.get(
        context.decision_impact,
        0,
    )

    # User-defined consequence adjustment
    score += context.consequence_score

    # Sensitive information
    if context.sensitive_information:
        score += 15

    # External action
    if context.external_action:
        score += 15

    # Production system modification
    if context.production_change:
        score += 20

    # Legal/regulatory interpretation
    if context.legal_or_regulatory_interpretation:
        score += 15

    # Public safety
    if context.affects_public_safety:
        score += 25

    # Critical infrastructure
    if context.affects_critical_infrastructure:
        score += 25

    return min(score, 100)


# ============================================================
# EVIDENCE QUALITY SCORE
#
# This score represents evidence strength.
# It is NOT a confidence score.
# ============================================================

def evidence_score(
    evidence: EvidenceAssessment,
) -> int:

    score = 0

    # --------------------------------------------------------
    # Evidence quality
    # --------------------------------------------------------

    if evidence.quality == EvidenceQuality.STRONG:

        score += 30

    elif evidence.quality == EvidenceQuality.MODERATE:

        score += 20

    elif evidence.quality == EvidenceQuality.WEAK:

        score += 10

    elif evidence.quality == EvidenceQuality.INSUFFICIENT:

        score += 0

    # --------------------------------------------------------
    # Primary sources
    # --------------------------------------------------------

    score += min(
        evidence.primary_source_count * 8,
        24,
    )

    # --------------------------------------------------------
    # Official sources
    # --------------------------------------------------------

    score += min(
        evidence.official_source_count * 5,
        15,
    )

    # --------------------------------------------------------
    # Independent source diversity
    # --------------------------------------------------------

    if evidence.source_diversity >= 3:

        score += 10

    elif evidence.source_diversity == 2:

        score += 5

    return min(score, 70)


# ============================================================
# UNCERTAINTY SCORE
#
# Higher score = greater uncertainty
# ============================================================

def uncertainty_score(
    evidence: EvidenceAssessment,
    ai: AIAnalysis,
) -> int:

    score = 0

    # --------------------------------------------------------
    # Evidence state
    # --------------------------------------------------------

    if evidence.evidence_status == (
        EvidenceStatus.CONFLICTING
    ):

        score += 30

    elif evidence.evidence_status == (
        EvidenceStatus.INSUFFICIENT
    ):

        score += 35

    elif evidence.evidence_status == (
        EvidenceStatus.AMBIGUOUS
    ):

        score += 25

    # --------------------------------------------------------
    # Contradicting evidence
    # --------------------------------------------------------

    if evidence.contradicting_count > 0:

        score += min(
            evidence.contradicting_count * 8,
            24,
        )

    # --------------------------------------------------------
    # Missing evidence
    # --------------------------------------------------------

    if evidence.missing_evidence:

        score += min(
            len(evidence.missing_evidence) * 5,
            20,
        )

    # --------------------------------------------------------
    # AI confidence
    # --------------------------------------------------------

    if ai.confidence < 0.50:

        score += 25

    elif ai.confidence < 0.70:

        score += 15

    elif ai.confidence < 0.85:

        score += 5

    # --------------------------------------------------------
    # Hallucination risk
    # --------------------------------------------------------

    score += min(
        int(ai.hallucination_risk * 30),
        30,
    )

    # --------------------------------------------------------
    # Novel situation
    # --------------------------------------------------------

    if ai.novel_situation:

        score += 15

    return min(
        int(score),
        100,
    )


# ============================================================
# RISK LEVEL
# ============================================================

def determine_risk_level(
    score: int,
):

    if score >= 75:

        from .models import RiskLevel

        return RiskLevel.CRITICAL

    if score >= 50:

        from .models import RiskLevel

        return RiskLevel.HIGH

    if score >= 25:

        from .models import RiskLevel

        return RiskLevel.MODERATE

    from .models import RiskLevel

    return RiskLevel.LOW


# ============================================================
# MANDATORY ESCALATION RULES
#
# These rules cannot be overridden by high AI confidence.
# ============================================================

def determine_mandatory_escalation(
    context: DecisionContext,
    evidence: EvidenceAssessment,
    ai: AIAnalysis,
):

    reasons = []

    required_rank = 0

    # --------------------------------------------------------
    # RULE 1
    # Public safety / critical infrastructure
    # --------------------------------------------------------

    if (
        context.affects_public_safety
        or context.affects_critical_infrastructure
    ):

        reasons.append(
            "Decision affects public safety "
            "or critical infrastructure."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 2
    # Conflicting authoritative evidence
    # --------------------------------------------------------

    if (
        evidence.evidence_status
        == EvidenceStatus.CONFLICTING
        and evidence.primary_source_count > 0
    ):

        reasons.append(
            "Authoritative evidence is conflicting."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 3
    # Insufficient evidence
    # --------------------------------------------------------

    if (
        evidence.evidence_status
        == EvidenceStatus.INSUFFICIENT
    ):

        reasons.append(
            "Evidence is insufficient to support "
            "a reliable decision."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.ANALYST_REVIEW
            ],
        )

    # --------------------------------------------------------
    # RULE 4
    # Ambiguous applicability
    # --------------------------------------------------------

    if (
        evidence.evidence_status
        == EvidenceStatus.AMBIGUOUS
    ):

        reasons.append(
            "Applicability of the evidence or "
            "requirement is ambiguous."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 5
    # Legal / regulatory interpretation
    # --------------------------------------------------------

    if context.legal_or_regulatory_interpretation:

        reasons.append(
            "Decision involves legal or regulatory "
            "interpretation."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 6
    # External action
    # --------------------------------------------------------

    if context.external_action:

        reasons.append(
            "The proposed outcome would trigger "
            "an external action."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.ANALYST_REVIEW
            ],
        )

    # --------------------------------------------------------
    # RULE 7
    # Production change
    # --------------------------------------------------------

    if context.production_change:

        reasons.append(
            "The decision would modify "
            "a production system."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 8
    # Sensitive information
    # --------------------------------------------------------

    if context.sensitive_information:

        reasons.append(
            "Decision involves sensitive information."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.ANALYST_REVIEW
            ],
        )

    # --------------------------------------------------------
    # RULE 9
    # Novel situation
    # --------------------------------------------------------

    if ai.novel_situation:

        reasons.append(
            "Situation is outside the established "
            "operating pattern."
        )

        required_rank = max(
            required_rank,
            ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ],
        )

    # --------------------------------------------------------
    # RULE 10
    # Explicit authority requirement
    # --------------------------------------------------------

    authority_rank = AUTHORITY_LEVEL[
        context.authority_requirement
    ]

    if authority_rank > 0:

        reasons.append(
            "Required authority level: "
            f"{context.authority_requirement.value}."
        )

        required_rank = max(
            required_rank,
            authority_rank,
        )

    return (
        required_rank > 0,
        reasons,
        required_rank,
    )