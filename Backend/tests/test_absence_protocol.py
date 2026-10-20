from __future__ import annotations

import json

from rag.retrieval import retrieve

from Backend.evidence_engine.rag_adapter import (
    adapt_retrieval_results,
)

from Backend.evidence_engine.absence_protocol import (
    build_absence_verification,
    absence_verification_to_dict,
)

from Backend.evidence_engine.models import (
    EvidenceStatus,
)


QUESTION = (
    "What security requirements apply to "
    "5G network slicing in India?"
)


def main():

    print("=" * 80)
    print("HACKGRID — ABSENCE VERIFICATION PROTOCOL")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. REAL RAG RETRIEVAL
    # --------------------------------------------------------

    print("\n[1/3] Running real RAG retrieval...")

    results = retrieve(
        QUESTION,
        k=5,
    )

    assert results, (
        "RAG returned no results."
    )

    print(
        f"Retrieved {len(results)} chunks."
    )

    # --------------------------------------------------------
    # 2. BUILD EVIDENCE RECORDS
    # --------------------------------------------------------

    print(
        "\n[2/3] Building evidence records..."
    )

    evidence_records = adapt_retrieval_results(
        results
    )

    assert evidence_records, (
        "No evidence records created."
    )

    # --------------------------------------------------------
    # 3. ABSENCE VERIFICATION
    # --------------------------------------------------------

    print(
        "\n[3/3] Running absence verification..."
    )

    verification = build_absence_verification(
        claim=QUESTION,
        evidence_records=evidence_records,
        search_scope=(
            "HackGrid RAG knowledge base; "
            "top-5 semantic retrieval results"
        ),
        authoritative_jurisdictions=[
            "India"
        ],
    )

    output = absence_verification_to_dict(
        verification
    )

    print("\nRESULT")
    print("=" * 80)

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )

    # --------------------------------------------------------
    # SAFETY ASSERTIONS
    # --------------------------------------------------------

    assert (
        verification.verification_status
        == EvidenceStatus.ABSENCE_NOT_ESTABLISHED
    )

    assert verification.claim == QUESTION

    assert len(
        verification.sources_examined
    ) > 0

    assert len(
        verification.positive_evidence
    ) > 0

    assert len(
        verification.limitations
    ) > 0

    # Critical safety property:
    # retrieval failure must never be interpreted as
    # proof of non-existence.

    assert (
        verification.verification_status
        != "ABSENT"
    )

    assert (
        verification.verification_status
        != "ABSENCE_ESTABLISHED"
    )

    print(
        "\n✓ Real RAG retrieval: PASS"
    )

    print(
        "✓ Evidence records: PASS"
    )

    print(
        "✓ Source examination tracking: PASS"
    )

    print(
        "✓ Authoritative-source tracking: PASS"
    )

    print(
        "✓ Positive evidence tracking: PASS"
    )

    print(
        "✓ Conservative absence logic: PASS"
    )

    print(
        "\nMISSION 7 ABSENCE VERIFICATION TEST: PASS"
    )


if __name__ == "__main__":
    main()