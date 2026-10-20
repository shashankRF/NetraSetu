from __future__ import annotations

import json

from Backend.final_synthesis import synthesize_final_assessment


def main():

    print("=" * 80)
    print("HACKGRID — MISSION 11")
    print("FINAL GPT-OSS SYNTHESIS")
    print("=" * 80)

    evidence_records = [
        {
            "evidence_id": "EV-001",
            "evidence_text": (
                "Network slicing security requires isolation "
                "between slices."
            ),
            "metadata": {
                "document": "Example Technical Standard",
                "page": 10,
                "chunk_id": "kb-test-001",
            },
        },
        {
            "evidence_id": "EV-002",
            "evidence_text": (
                "The supplied national regulatory material "
                "does not establish a complete network-slicing "
                "security requirement."
            ),
            "metadata": {
                "document": "Example National Regulation",
                "page": 20,
                "chunk_id": "kb-test-002",
            },
        },
    ]

    classification = {
        "claim": "5G network slicing requires security controls.",
        "classifications": [
            {
                "evidence_id": "EV-001",
                "evidence_role": "SUPPORTING",
                "evidence_strength": "MODERATE",
                "applicability": "DIRECT",
                "requirement_type": "ADVISORY",
                "confidence": 0.92,
            },
            {
                "evidence_id": "EV-002",
                "evidence_role": "LIMITING",
                "evidence_strength": "MODERATE",
                "applicability": "DIRECT",
                "requirement_type": "UNKNOWN",
                "confidence": 0.85,
            },
        ],
    }

    evidence_assessment = {
        "overall_status": "PARTIALLY_ESTABLISHED",
        "overall_strength": "MODERATE",
        "supporting_count": 1,
        "contradicting_count": 0,
        "primary_source_count": 1,
        "official_source_count": 1,
        "source_diversity": 2,
        "overall_confidence": 0.86,
        "missing_evidence": [],
    }

    absence = [
        {
            "claim": "Complete national requirement exists.",
            "verification_status": "ABSENCE_NOT_ESTABLISHED",
            "sources_examined": [
                "Example National Regulation"
            ],
            "positive_evidence": ["EV-002"],
            "negative_evidence": [],
            "limitations": [
                "Retrieval is not an exhaustive legal database search."
            ],
        }
    ]

    gap_input = {
        "overall_status": "PARTIALLY_ESTABLISHED",
        "overall_strength": "MODERATE",
        "supporting_count": 1,
        "contradicting_count": 0,
        "missing_evidence": [],
        "absence_verifications": absence,
    }

    risk = {
        "risk_level": "HIGH",
        "risk_score": 75,
        "escalation_level": "DOMAIN_EXPERT",
        "human_review_required": True,
        "mandatory_review": True,
        "blocking_conditions": [],
        "recommended_action": (
            "Route to domain expert."
        ),
        "evidence_quality": "MODERATE",
        "evidence_status": "SUFFICIENT",
        "ai_confidence": 0.82,
        "governance_decision": "DOMAIN_EXPERT",
    }

    result = synthesize_final_assessment(
        question=(
            "What security requirements apply to "
            "5G network slicing in India?"
        ),
        evidence_records=evidence_records,
        classification=classification,
        evidence_assessment=evidence_assessment,
        absence_verifications=absence,
        gap_input=gap_input,
        risk_assessment=risk,
    )

    assert result["status"] == "SUCCESS"
    assert result["model"] == "openai/gpt-oss-120b"

    valid_ids = {
        "EV-001",
        "EV-002",
    }

    for claim in result["claims"]:
        for evidence_id in claim["evidence_ids"]:
            assert evidence_id in valid_ids

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\n✓ GPT-OSS synthesis: PASS")
    print("✓ Evidence ID validation: PASS")
    print("✓ Structured final assessment: PASS")
    print("\nMISSION 11 FINAL SYNTHESIS: PASS")


if __name__ == "__main__":
    main()