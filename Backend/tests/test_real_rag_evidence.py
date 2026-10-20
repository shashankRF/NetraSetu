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


# ============================================================
# CONFIGURATION
# ============================================================

QUESTION = (
    "What security requirements apply to "
    "5G network slicing in India?"
)

TOP_K = 5


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 80)
    print("HACKGRID — REAL RAG EVIDENCE CLASSIFICATION")
    print("=" * 80)

    print("\nQuestion:")
    print(QUESTION)

    # ========================================================
    # 1. REAL RAG RETRIEVAL
    # ========================================================

    print("\n[1/5] Running real RAG retrieval...")

    results = retrieve(
        QUESTION,
        k=TOP_K,
    )

    if not results:
        raise RuntimeError(
            "RAG returned no evidence."
        )

    print(
        f"Retrieved {len(results)} evidence chunks."
    )

    # ========================================================
    # 2. RAG → EVIDENCE ADAPTER
    # ========================================================

    print(
        "\n[2/5] Converting retrieved chunks "
        "into evidence records..."
    )

    evidence_records = adapt_retrieval_results(
        results
    )

    if not evidence_records:
        raise RuntimeError(
            "Evidence adapter returned no records."
        )

    print(
        f"Created {len(evidence_records)} "
        "evidence records."
    )

    # ========================================================
    # 3. DISPLAY REAL PROVENANCE
    # ========================================================

    print("\nRetrieved Evidence")
    print("-" * 80)

    for evidence in evidence_records:

        provenance = evidence["provenance"]

        print(
            f"{evidence['evidence_id']} | "
            f"Rank={evidence['retrieval']['rank']} | "
            f"Document={provenance.get('document')} | "
            f"Page={provenance.get('page')} | "
            f"Chunk={provenance.get('chunk_id')}"
        )

    # ========================================================
    # 4. GPT-OSS CLASSIFICATION
    # ========================================================

    print(
        "\n[3/5] Sending real evidence to GPT-OSS..."
    )

    classification = classify_evidence(
        claim=QUESTION,
        evidence_records=evidence_records,
    )

    if classification.get("status") != "SUCCESS":

        print("\nGPT-OSS classification failed:")

        print(
            json.dumps(
                classification,
                indent=2,
                ensure_ascii=False,
            )
        )

        raise RuntimeError(
            "GPT-OSS evidence classification failed."
        )

    print(
        "\nGPT-OSS classification completed."
    )

    # ========================================================
    # 5. EVIDENCE CONSISTENCY VALIDATION
    # ========================================================

    print(
        "\n[4/5] Running evidence consistency validation..."
    )

    validation = validate_evidence_consistency(
        classifications=classification,
        evidence_records=evidence_records,
    )

    print(
        json.dumps(
            validation,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not validation["valid"]:

        raise AssertionError(
            "Evidence consistency validation failed: "
            + str(validation["errors"])
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n[5/5] Final integrated evidence result"
    )

    print("=" * 80)

    print(
        json.dumps(
            classification,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # INTEGRITY CHECKS
    # ========================================================

    print("\n" + "=" * 80)
    print("INTEGRATION VALIDATION")
    print("=" * 80)

    # --------------------------------------------------------
    # Evidence IDs
    # --------------------------------------------------------

    supplied_ids = {
        evidence["evidence_id"]
        for evidence in evidence_records
    }

    returned_ids = {
        item["evidence_id"]
        for item in classification.get(
            "classifications",
            [],
        )
    }

    unknown_ids = returned_ids - supplied_ids

    assert not unknown_ids, (
        f"GPT-OSS returned unknown evidence IDs: "
        f"{unknown_ids}"
    )

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    for evidence in evidence_records:

        evidence_id = evidence["evidence_id"]
        provenance = evidence["provenance"]

        assert provenance.get(
            "chunk_id"
        ), (
            f"{evidence_id} has no chunk_id."
        )

        assert provenance.get(
            "document"
        ), (
            f"{evidence_id} has no document."
        )

        assert provenance.get(
            "page"
        ) is not None, (
            f"{evidence_id} has no page."
        )

        assert evidence.get(
            "text"
        ), (
            f"{evidence_id} has no evidence text."
        )

    # --------------------------------------------------------
    # Classification vocabulary
    # --------------------------------------------------------

    valid_roles = {
        "SUPPORTING",
        "CONTRADICTING",
        "LIMITING",
        "CONTEXTUAL",
    }

    valid_strengths = {
        "STRONG",
        "MODERATE",
        "WEAK",
        "INSUFFICIENT",
    }

    valid_applicability = {
        "DIRECT",
        "PARTIAL",
        "UNCERTAIN",
        "NOT_APPLICABLE",
        "NOT_ESTABLISHED",
    }

    valid_requirement_types = {
        "MANDATORY",
        "ADVISORY",
        "TECHNICAL",
        "UNKNOWN",
    }

    for item in classification.get(
        "classifications",
        [],
    ):

        assert (
            item["evidence_role"]
            in valid_roles
        )

        assert (
            item["evidence_strength"]
            in valid_strengths
        )

        assert (
            item["applicability"]
            in valid_applicability
        )

        assert (
            item["requirement_type"]
            in valid_requirement_types
        )

        assert (
            0.0
            <= item["confidence"]
            <= 1.0
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "\n✓ Real RAG retrieval: PASS"
    )

    print(
        "✓ Evidence adapter: PASS"
    )

    print(
        "✓ Provenance preservation: PASS"
    )

    print(
        "✓ GPT-OSS classification: PASS"
    )

    print(
        "✓ Evidence ID integrity: PASS"
    )

    print(
        "✓ Classification vocabulary: PASS"
    )

    print(
        "✓ Evidence consistency validation: PASS"
    )

    print(
        "\nMISSION 6 REAL-RAG INTEGRATION TEST: PASS"
    )


if __name__ == "__main__":
    main()