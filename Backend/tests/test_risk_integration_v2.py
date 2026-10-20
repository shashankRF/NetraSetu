from __future__ import annotations

import json

from Backend.evidence_engine.models import (
    ClaimAssessment,
    EvidenceAssessment,
    EvidenceStatus,
    EvidenceStrength,
)

from Backend.risk_engine.models import (
    AIAnalysis,
    DecisionContext,
    DecisionImpact,
    AuthorityRequirement,
)

from Backend.risk_integration_v2 import (
    assess_with_evidence_engine,
    build_risk_evidence_assessment,
    risk_assessment_to_dict,
)


def main():

    print("=" * 80)
    print("HACKGRID — MISSION 10")
    print("EVIDENCE ENGINE → RISK ENGINE INTEGRATION")
    print("=" * 80)

    # --------------------------------------------------------
    # STRUCTURED EVIDENCE ENGINE RESULT
    # --------------------------------------------------------

    print("\n[1/4] Building Evidence Engine assessment...")

    evidence = EvidenceAssessment(
        claims=[],
        overall_status=EvidenceStatus.SUFFICIENT,
        overall_strength=EvidenceStrength.MODERATE,
        supporting_count=8,
        contradicting_count=0,
        primary_source_count=3,
        official_source_count=4,
        source_diversity=3,
        missing_evidence=[
            "Additional authoritative implementation guidance"
        ],
        overall_confidence=0.82,
    )

    print("Evidence Engine assessment: PASS")

    # --------------------------------------------------------
    # CONVERT TO RISK ENGINE FORMAT
    # --------------------------------------------------------

    print("\n[2/4] Converting evidence assessment...")

    risk_evidence = build_risk_evidence_assessment(
        evidence
    )

    assert risk_evidence.supporting_count == 8
    assert risk_evidence.contradicting_count == 0
    assert risk_evidence.primary_source_count == 3
    assert risk_evidence.official_source_count == 4
    assert risk_evidence.source_diversity == 3
    assert risk_evidence.missing_evidence

    print("Evidence mapping: PASS")

    # --------------------------------------------------------
    # HIGH-CONSEQUENCE DECISION CONTEXT
    # --------------------------------------------------------

    print("\n[3/4] Running Risk Engine...")

    context = DecisionContext(
        domain="5G telecommunications",
        decision_impact=DecisionImpact.REGULATORY,
        consequence_score=85,
        authority_requirement=(
            AuthorityRequirement.SENIOR_AUTHORITY
        ),
        sensitive_information=True,
        external_action=True,
        production_change=False,
        legal_or_regulatory_interpretation=True,
        affects_public_safety=True,
        affects_critical_infrastructure=True,
    )

    ai = AIAnalysis(
        confidence=0.82,
        factual_claims=8,
        supported_claims=8,
        unsupported_claims=0,
        hallucination_risk=0.10,
        novel_situation=False,
    )

    assessment = assess_with_evidence_engine(
        decision_context=context,
        evidence_assessment=evidence,
        ai_analysis=ai,
    )

    assert assessment is not None
    assert assessment.risk_score >= 0
    assert assessment.risk_score <= 100

    print("Risk Engine execution: PASS")

    # --------------------------------------------------------
    # SERIALIZATION
    # --------------------------------------------------------

    print("\n[4/4] Validating final risk output...")

    output = risk_assessment_to_dict(
        assessment
    )

    required_fields = [
        "risk_level",
        "risk_score",
        "escalation_level",
        "human_review_required",
        "mandatory_review",
        "reasons",
        "blocking_conditions",
        "recommended_action",
        "evidence_quality",
        "evidence_status",
        "ai_confidence",
        "governance_decision",
    ]

    for field in required_fields:
        assert field in output, (
            f"Missing risk output field: {field}"
        )

    print("\nRISK ASSESSMENT")
    print("=" * 80)
    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\n✓ Evidence Engine assessment: PASS")
    print("✓ Evidence → Risk mapping: PASS")
    print("✓ Risk Engine execution: PASS")
    print("✓ Risk assessment serialization: PASS")

    print("\nMISSION 10 RISK INTEGRATION: PASS")


if __name__ == "__main__":
    main()