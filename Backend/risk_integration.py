from __future__ import annotations

from typing import Any, Dict

from .risk_engine import (
    AIAnalysis,
    AuthorityRequirement,
    DecisionContext,
    DecisionImpact,
    EvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus,
    RiskEngine,
)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _combined_text(*values: Any) -> str:
    return " ".join(str(v) for v in values).lower()


def _contains(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def build_risk_context(
    question: str,
    network_result: Any,
    compliance_result: Any,
    policy_result: Any,
    gap_result: Any,
    final_answer: str = "",
):
    """
    Convert the current RAG/agent outputs into the structured
    inputs required by the deterministic Risk Engine.

    IMPORTANT:
    This adapter provides an initial integration layer.
    It does not allow the LLM to directly choose escalation.
    """

    network = _as_dict(network_result)
    compliance = _as_dict(compliance_result)
    policy = _as_dict(policy_result)
    gap = _as_dict(gap_result)

    gap_analysis = str(
        gap.get("analysis", "")
    )

    combined = _combined_text(
        question,
        network,
        compliance,
        policy,
        gap,
        final_answer,
    )

    # ========================================================
    # DOMAIN
    # ========================================================

    if _contains(
        combined,
        ["maritime", "vessel", "ship", "ais", "coast guard"],
    ):
        domain = "maritime"

    elif _contains(
        combined,
        ["defence", "defense", "military", "tactical"],
    ):
        domain = "defence"

    elif _contains(
        combined,
        ["policy", "regulation", "regulatory", "compliance"],
    ):
        domain = "policy"

    else:
        domain = "telecom"

    # ========================================================
    # DECISION IMPACT
    # ========================================================

    decision_impact = DecisionImpact.INFORMATIONAL

    if _contains(
        combined,
        [
            "security",
            "cyber attack",
            "cybersecurity",
            "breach",
            "threat",
        ],
    ):
        decision_impact = DecisionImpact.SECURITY

    if _contains(
        combined,
        [
            "production change",
            "network configuration",
            "deploy",
            "deployment",
        ],
    ):
        decision_impact = DecisionImpact.OPERATIONAL

    if _contains(
        combined,
        [
            "public safety",
            "life safety",
            "emergency",
        ],
    ):
        decision_impact = DecisionImpact.SAFETY

    if _contains(
        combined,
        [
            "regulatory interpretation",
            "legal interpretation",
            "legal requirement",
        ],
    ):
        decision_impact = DecisionImpact.REGULATORY

    # ========================================================
    # GOVERNANCE FLAGS
    # ========================================================

    sensitive_information = _contains(
        combined,
        [
            "classified",
            "sensitive information",
            "confidential",
            "intelligence",
        ],
    )

    external_action = _contains(
        combined,
        [
            "execute",
            "intercept",
            "block",
            "deploy",
            "notify authority",
        ],
    )

    production_change = _contains(
        combined,
        [
            "production change",
            "production system",
            "network configuration",
            "configuration change",
        ],
    )

    legal_or_regulatory_interpretation = _contains(
        combined,
        [
            "legal interpretation",
            "regulatory interpretation",
        ],
    )

    affects_public_safety = _contains(
        combined,
        [
            "public safety",
            "life safety",
        ],
    )

    affects_critical_infrastructure = _contains(
        combined,
        [
            "critical infrastructure",
            "critical telecommunication infrastructure",
            "cti",
        ],
    )

    # ========================================================
    # AUTHORITY
    # ========================================================

    authority_requirement = AuthorityRequirement.NONE

    if legal_or_regulatory_interpretation:
        authority_requirement = AuthorityRequirement.DOMAIN_EXPERT

    if (
        affects_public_safety
        or affects_critical_infrastructure
        or (sensitive_information and external_action)
    ):
        authority_requirement = AuthorityRequirement.SENIOR_AUTHORITY

    # ========================================================
    # EVIDENCE STATUS
    # ========================================================

    gap_lower = gap_analysis.lower()

    if "insufficient evidence" in gap_lower:
        evidence_status = EvidenceStatus.INSUFFICIENT

    elif "conflicting" in gap_lower:
        evidence_status = EvidenceStatus.CONFLICTING

    elif "ambiguous" in gap_lower:
        evidence_status = EvidenceStatus.AMBIGUOUS

    else:
        evidence_status = EvidenceStatus.SUFFICIENT

    # ========================================================
    # EVIDENCE QUALITY
    # ========================================================

    if evidence_status == EvidenceStatus.INSUFFICIENT:
        evidence_quality = EvidenceQuality.INSUFFICIENT

    elif evidence_status == EvidenceStatus.CONFLICTING:
        evidence_quality = EvidenceQuality.MODERATE

    else:
        evidence_quality = EvidenceQuality.MODERATE

    # ========================================================
    # BASIC EVIDENCE COUNTS
    # ========================================================

    supporting_count = sum(
        combined.count(term)
        for term in [
            "covered",
            "supports",
            "supported",
            "applicable",
        ]
    )

    contradicting_count = sum(
        combined.count(term)
        for term in [
            "conflicting",
            "contradicting",
            "contradiction",
            "inconsistent",
        ]
    )

    missing_evidence = []

    if evidence_status == EvidenceStatus.INSUFFICIENT:
        missing_evidence.append(
            "Additional authoritative evidence is required."
        )

    # ========================================================
    # AI ANALYSIS
    # ========================================================

    if evidence_status == EvidenceStatus.INSUFFICIENT:
        confidence = 0.45

    elif evidence_status == EvidenceStatus.CONFLICTING:
        confidence = 0.60

    else:
        confidence = 0.75

    ai = AIAnalysis(
        confidence=confidence,
        factual_claims=0,
        supported_claims=supporting_count,
        unsupported_claims=0,
        hallucination_risk=1.0 - confidence,
        novel_situation=False,
    )

    # ========================================================
    # EVIDENCE OBJECT
    # ========================================================

    evidence = EvidenceAssessment(
        quality=evidence_quality,
        supporting_count=supporting_count,
        contradicting_count=contradicting_count,
        primary_source_count=0,
        official_source_count=0,
        source_diversity=0,
        evidence_status=evidence_status,
        missing_evidence=missing_evidence,
    )

    # ========================================================
    # DECISION CONTEXT
    # ========================================================

    context = DecisionContext(
        domain=domain,
        decision_impact=decision_impact,
        consequence_score=0,
        authority_requirement=authority_requirement,
        sensitive_information=sensitive_information,
        external_action=external_action,
        production_change=production_change,
        legal_or_regulatory_interpretation=(
            legal_or_regulatory_interpretation
        ),
        affects_public_safety=affects_public_safety,
        affects_critical_infrastructure=(
            affects_critical_infrastructure
        ),
    )

    return context, evidence, ai


def assess_rag_result(
    question: str,
    network_result: Any,
    compliance_result: Any,
    policy_result: Any,
    gap_result: Any,
    final_answer: str = "",
):
    context, evidence, ai = build_risk_context(
        question=question,
        network_result=network_result,
        compliance_result=compliance_result,
        policy_result=policy_result,
        gap_result=gap_result,
        final_answer=final_answer,
    )

    engine = RiskEngine()

    return engine.assess(
        context=context,
        evidence=evidence,
        ai=ai,
    )