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

from Backend.evidence_engine.absence_protocol import (
    build_absence_verification,
    absence_verification_to_dict,
)

from Backend.evidence_engine.engine import (
    EvidenceEngine,
)

from Backend.tests.test_evidence_engine_integration import (
    build_claim_assessment,
)

from Backend.evidence_engine.gap_adapter import (
    build_gap_input,
)


QUESTION = (
    "What security requirements apply to "
    "5G network slicing in India?"
)


def main():

    print("=" * 80)
    print("HACKGRID — GAP ANALYSIS INTEGRATION")
    print("=" * 80)

    print("\n[1/6] RAG retrieval...")

    results = retrieve(
        QUESTION,
        k=5,
    )

    assert results, "RAG returned no results."

    print(
        f"Retrieved {len(results)} chunks."
    )

    print("\n[2/6] Evidence adaptation...")

    evidence_records = adapt_retrieval_results(
        results
    )

    assert evidence_records

    print(
        f"Created {len(evidence_records)} evidence records."
    )

    print("\n[3/6] GPT-OSS classification...")

    classification = classify_evidence(
        claim=QUESTION,
        evidence_records=evidence_records,
    )

    assert classification["status"] == "SUCCESS"

    print("GPT-OSS classification: PASS")

    print("\n[4/6] Consistency validation...")

    validation = validate_evidence_consistency(
        classifications=classification,
        evidence_records=evidence_records,
    )

    assert validation["valid"], validation["errors"]

    print("Consistency validation: PASS")

    print("\n[5/6] Evidence Engine + Absence Verification...")

    claim = build_claim_assessment(
        classification,
        evidence_records,
    )

    engine = EvidenceEngine()

    assessment = engine.assess(
        claims=[claim]
    )

    absence = build_absence_verification(
        claim=QUESTION,
        evidence_records=evidence_records,
        search_scope=(
            "HackGrid RAG knowledge base; "
            "top-5 semantic retrieval results"
        ),
        authoritative_jurisdictions=["India"],
    )

    absence_dict = absence_verification_to_dict(
        absence
    )

    print("Evidence Engine: PASS")
    print("Absence Verification: PASS")

    print("\n[6/6] Building Gap Analysis input...")

    gap_input = build_gap_input(
        evidence_assessment=assessment,
        absence_verifications=[
            absence_dict
        ],
    )

    print("\nGAP INPUT")
    print("=" * 80)

    print(
        json.dumps(
            gap_input,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    assert gap_input["overall_status"]
    assert gap_input["overall_strength"]
    assert (
        "supporting_count"
        in gap_input
    )
    assert (
        "contradicting_count"
        in gap_input
    )
    assert (
        "absence_verifications"
        in gap_input
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
        "✓ Evidence Engine: PASS"
    )

    print(
        "✓ Absence Verification: PASS"
    )

    print(
        "✓ Gap input construction: PASS"
    )

    print(
        "\nMISSION 9 GAP INTEGRATION INPUT: PASS"
    )


if __name__ == "__main__":
    main()