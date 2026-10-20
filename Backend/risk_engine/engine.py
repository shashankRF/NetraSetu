from .models import (
    AIAnalysis,
    DecisionContext,
    EvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus,
    RiskAssessment,
    RiskLevel,
    EscalationLevel,
)

from .rules import (
    calculate_base_score,
    evidence_score,
    uncertainty_score,
    determine_risk_level,
    determine_mandatory_escalation,
)

from .policy import (
    ESCALATION_RANK,
    escalation_from_rank,
)


class RiskEngine:

    """
    HackGrid Risk & Governance Engine.

    IMPORTANT:

    This engine is intentionally deterministic.

    The LLM may provide:
        - analysis
        - confidence
        - evidence interpretation
        - hallucination risk
        - novelty indication

    But the LLM does NOT decide:
        - whether human review is mandatory
        - who must review
        - whether an action is authorized

    Those decisions belong here.
    """

    def __init__(self):
        pass

    # ========================================================
    # MAIN ASSESSMENT
    # ========================================================

    def assess(
        self,
        context: DecisionContext,
        evidence: EvidenceAssessment,
        ai: AIAnalysis,
    ) -> RiskAssessment:

        reasons = []

        blocking_conditions = []

        # ----------------------------------------------------
        # STEP 1
        # Calculate decision impact
        # ----------------------------------------------------

        base_score = calculate_base_score(
            context
        )

        # ----------------------------------------------------
        # STEP 2
        # Calculate evidence strength
        # ----------------------------------------------------

        evidence_component = evidence_score(
            evidence
        )

        # ----------------------------------------------------
        # STEP 3
        # Calculate uncertainty
        # ----------------------------------------------------

        uncertainty_component = uncertainty_score(
            evidence,
            ai,
        )

        # ----------------------------------------------------
        # STEP 4
        # Calculate overall risk
        #
        # Evidence reduces risk.
        # Uncertainty increases risk.
        # ----------------------------------------------------

        risk_score = (
            base_score
            + uncertainty_component
            - int(
                evidence_component * 0.35
            )
        )

        risk_score = max(
            0,
            min(
                risk_score,
                100,
            ),
        )

        risk_level = determine_risk_level(
            risk_score
        )

        # ----------------------------------------------------
        # STEP 5
        # Mandatory governance rules
        # ----------------------------------------------------

        (
            mandatory_review,
            mandatory_reasons,
            mandatory_rank,
        ) = determine_mandatory_escalation(
            context,
            evidence,
            ai,
        )

        reasons.extend(
            mandatory_reasons
        )

        # ----------------------------------------------------
        # STEP 6
        # Risk-based escalation
        # ----------------------------------------------------

        if risk_level == RiskLevel.CRITICAL:

            risk_rank = ESCALATION_RANK[
                EscalationLevel.SENIOR_AUTHORITY
            ]

        elif risk_level == RiskLevel.HIGH:

            risk_rank = ESCALATION_RANK[
                EscalationLevel.DOMAIN_EXPERT
            ]

        elif risk_level == RiskLevel.MODERATE:

            risk_rank = ESCALATION_RANK[
                EscalationLevel.ANALYST_REVIEW
            ]

        else:

            risk_rank = ESCALATION_RANK[
                EscalationLevel.AUTO_RESPONSE
            ]

        # Highest required escalation wins.
        final_rank = max(
            risk_rank,
            mandatory_rank,
        )

        escalation_level = escalation_from_rank(
            final_rank
        )

        # ----------------------------------------------------
        # STEP 7
        # Blocking conditions
        # ----------------------------------------------------

        if (
            evidence.evidence_status
            == EvidenceStatus.INSUFFICIENT
        ):

            blocking_conditions.append(
                "Cannot approve a consequential "
                "decision with insufficient evidence."
            )

        if (
            evidence.evidence_status
            == EvidenceStatus.CONFLICTING
        ):

            blocking_conditions.append(
                "Conflicting evidence must be "
                "resolved before consequential action."
            )

        if (
            evidence.evidence_status
            == EvidenceStatus.AMBIGUOUS
        ):

            blocking_conditions.append(
                "Applicability must be established "
                "before consequential action."
            )

        if ai.hallucination_risk >= 0.70:

            blocking_conditions.append(
                "AI hallucination risk is too high "
                "for consequential action."
            )

        # ----------------------------------------------------
        # STEP 8
        # Human review requirement
        # ----------------------------------------------------

        human_review_required = (
            mandatory_review
            or final_rank > 0
            or len(blocking_conditions) > 0
        )

        # ----------------------------------------------------
        # STEP 9
        # Recommended action
        # ----------------------------------------------------

        if blocking_conditions:

            recommended_action = (
                "DO NOT EXECUTE ACTION. "
                "Resolve evidence or governance "
                "blockers and escalate for review."
            )

        elif (
            escalation_level
            == EscalationLevel.AUTO_RESPONSE
        ):

            recommended_action = (
                "AI analysis may be returned as "
                "an informational response."
            )

        elif (
            escalation_level
            == EscalationLevel.ANALYST_REVIEW
        ):

            recommended_action = (
                "Route to analyst review before "
                "taking consequential action."
            )

        elif (
            escalation_level
            == EscalationLevel.DOMAIN_EXPERT
        ):

            recommended_action = (
                "Route to a qualified domain expert "
                "before consequential action."
            )

        else:

            recommended_action = (
                "Route to authorized senior authority "
                "for final decision."
            )

        # ----------------------------------------------------
        # STEP 10
        # Additional reasoning
        # ----------------------------------------------------

        if (
            evidence.quality
            == EvidenceQuality.STRONG
        ):

            reasons.append(
                "Evidence quality is strong."
            )

        elif (
            evidence.quality
            == EvidenceQuality.MODERATE
        ):

            reasons.append(
                "Evidence quality is moderate."
            )

        elif (
            evidence.quality
            == EvidenceQuality.WEAK
        ):

            reasons.append(
                "Evidence quality is weak."
            )

        elif (
            evidence.quality
            == EvidenceQuality.INSUFFICIENT
        ):

            reasons.append(
                "Evidence quality is insufficient."
            )

        if evidence.supporting_count > 0:

            reasons.append(
                f"{evidence.supporting_count} "
                "supporting evidence item(s) detected."
            )

        if evidence.contradicting_count > 0:

            reasons.append(
                f"{evidence.contradicting_count} "
                "contradicting evidence item(s) detected."
            )

        if evidence.missing_evidence:

            reasons.append(
                f"{len(evidence.missing_evidence)} "
                "evidence gap(s) identified."
            )

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        return RiskAssessment(

            risk_level=risk_level,

            risk_score=risk_score,

            escalation_level=escalation_level,

            human_review_required=(
                human_review_required
            ),

            mandatory_review=mandatory_review,

            reasons=reasons,

            blocking_conditions=(
                blocking_conditions
            ),

            recommended_action=(
                recommended_action
            ),

            evidence_quality=(
                evidence.quality
            ),

            evidence_status=(
                evidence.evidence_status
            ),

            ai_confidence=(
                ai.confidence
            ),

            governance_decision=(
                escalation_level.value
            ),
        )