from __future__ import annotations

import json

from rag.retrieval import retrieve

from Backend.evidence_engine.rag_adapter import (
    adapt_retrieval_results,
)

from Backend.evidence_engine.llm_classifier import (
    classify_evidence,
)

from Backend.evidence_engine.validator import (
    validate_evidence_consistency,
)

from Backend.evidence_engine.engine import (
    EvidenceEngine,
)

from Backend.evidence_engine.models import (
    ClaimAssessment,
    EvidenceItem,
    EvidenceRole,
    EvidenceStrength,
    Applicability,
    RequirementType,
    EvidenceStatus,
)


QUESTION = (
    "What security requirements apply to "
    "5G network slicing in India?"
)

TOP_K = 5


def build_claim_assessment(
    classification,
    evidence_records,
):
    evidence_map = {
        item["evidence_id"]: item
        for item in evidence_records
    }

    supporting = []
    contradicting = []
    limiting = []
    contextual = []

    for item in classification["classifications"]:

        record = evidence_map[
            item["evidence_id"]
        ]

        provenance = record["provenance"]

        evidence = EvidenceItem(
            evidence_id=item["evidence_id"],
            claim_id="CLAIM-001",
            claim_text=QUESTION,
            evidence_text=record["text"],
            role=EvidenceRole(
                item["evidence_role"]
            ),
            strength=EvidenceStrength(
                item["evidence_strength"]
            ),
            applicability=Applicability(
                item["applicability"]
            ),
            requirement_type=RequirementType(
                item["requirement_type"]
            ),
            metadata=__import__(
                "Backend.evidence_engine.models",
                fromlist=["EvidenceMetadata"],
            ).EvidenceMetadata(
                document=provenance.get(
                    "document"
                ),
                publisher=record[
                    "normalized_metadata"
                ].get("publisher"),
                source_type=record[
                    "normalized_metadata"
                ].get("source_type"),
                jurisdiction=provenance.get(
                    "jurisdiction"
                ),
                page=provenance.get("page"),
                section=provenance.get(
                    "section"
                ),
                clause=provenance.get(
                    "clause"
                ),
                chunk_id=provenance.get(
                    "chunk_id"
                ),
                retrieval_rank=record[
                    "retrieval"
                ].get("rank"),
                version=record[
                    "normalized_metadata"
                ].get("version"),
                publication_date=record[
                    "normalized_metadata"
                ].get("publication_date"),
                effective_date=record[
                    "normalized_metadata"
                ].get("effective_date"),
                expiry_date=record[
                    "normalized_metadata"
                ].get("expiry_date"),
            ),
            confidence=item["confidence"],
            limitations=[],
        )

        role = item["evidence_role"]

        if role == "SUPPORTING":
            supporting.append(evidence)

        elif role == "CONTRADICTING":
            contradicting.append(evidence)

        elif role == "LIMITING":
            limiting.append(evidence)

        elif role == "CONTEXTUAL":
            contextual.append(evidence)

    if contradicting:
        status = EvidenceStatus.CONFLICTING

    elif supporting:
        status = EvidenceStatus.SUFFICIENT

    else:
        status = EvidenceStatus.INSUFFICIENT

    confidences = [
        item["confidence"]
        for item in classification[
            "classifications"
        ]
    ]

    confidence = (
        sum(confidences)
        / len(confidences)
        if confidences
        else 0.0
    )

    return ClaimAssessment(
        claim_id="CLAIM-001",
        claim_text=QUESTION,
        supporting=supporting,
        contradicting=contradicting,
        limiting=limiting,
        contextual=contextual,
        status=status,
        applicability=Applicability.UNCERTAIN,
        confidence=confidence,
        limitations=[],
    )


def main():

    print("=" * 80)
    print("HACKGRID — EVIDENCE ENGINE INTEGRATION")
    print("=" * 80)

    print("\n[1/5] RAG retrieval...")

    results = retrieve(
        QUESTION,
        k=TOP_K,
    )

    assert results

    print(
        f"Retrieved {len(results)} chunks."
    )

    print("\n[2/5] Evidence adaptation...")

    evidence_records = adapt_retrieval_results(
        results
    )

    assert evidence_records

    print(
        f"Created {len(evidence_records)} evidence records."
    )

    print("\n[3/5] GPT-OSS classification...")

    classification = classify_evidence(
        claim=QUESTION,
        evidence_records=evidence_records,
    )

    assert (
        classification["status"]
        == "SUCCESS"
    )

    print("\n[4/5] Consistency validation...")

    validation = validate_evidence_consistency(
        classifications=classification,
        evidence_records=evidence_records,
    )

    assert validation["valid"]

    claim = build_claim_assessment(
        classification,
        evidence_records,
    )

    print("\nClaim Assessment")
    print("=" * 80)

    print(
        f"Claim ID: {claim.claim_id}"
    )

    print(
        f"Supporting: {len(claim.supporting)}"
    )

    print(
        f"Contradicting: {len(claim.contradicting)}"
    )

    print(
        f"Limiting: {len(claim.limiting)}"
    )

    print(
        f"Contextual: {len(claim.contextual)}"
    )

    print(
        f"Status: {claim.status.value}"
    )

    print(
        f"Confidence: {claim.confidence:.3f}"
    )

    print("\n[5/5] Evidence Engine aggregation...")

    engine = EvidenceEngine()

    assessment = engine.assess(
        claims=[claim]
    )

    print("\nEvidence Assessment")
    print("=" * 80)

    print(
        json.dumps(
            assessment.__dict__,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    assert assessment.claims

    assert (
        assessment.supporting_count
        == len(claim.supporting)
    )

    assert (
        assessment.contradicting_count
        == len(claim.contradicting)
    )

    print(
        "\n✓ RAG retrieval: PASS"
    )

    print(
        "✓ Evidence adaptation: PASS"
    )

    print(
        "✓ GPT-OSS classification: PASS"
    )

    print(
        "✓ Consistency validation: PASS"
    )

    print(
        "✓ ClaimAssessment construction: PASS"
    )

    print(
        "✓ EvidenceEngine aggregation: PASS"
    )

    print(
        "\nMISSION 8 EVIDENCE ENGINE INTEGRATION: PASS"
    )


if __name__ == "__main__":
    main()