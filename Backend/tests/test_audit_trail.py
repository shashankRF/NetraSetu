from __future__ import annotations

from Backend.audit.recorder import (
    append_audit_record,
    create_audit_record,
    load_audit_records,
)


def main():

    print("=" * 80)
    print("HACKGRID — MISSION 12")
    print("AUDIT TRAIL")
    print("=" * 80)

    record = create_audit_record(
        question=(
            "What security requirements apply to "
            "5G network slicing in India?"
        ),
        model="openai/gpt-oss-120b",
        retrieved_evidence=[
            {
                "evidence_id": "EV-001",
                "document": "Example Standard",
                "page": 10,
                "chunk_id": "kb-test-001",
            }
        ],
        evidence_classification={
            "classifications": [
                {
                    "evidence_id": "EV-001",
                    "evidence_role": "SUPPORTING",
                }
            ]
        },
        evidence_assessment={
            "overall_status": "SUFFICIENT",
            "supporting_count": 1,
        },
        absence_verification=[
            {
                "claim": "Example claim",
                "verification_status": (
                    "ABSENCE_NOT_ESTABLISHED"
                ),
            }
        ],
        gap_analysis={
            "overall_status": "SUFFICIENT",
        },
        risk_assessment={
            "risk_level": "HIGH",
            "risk_score": 75,
            "human_review_required": True,
        },
        final_synthesis={
            "assessment": "Example assessment.",
            "claims": [
                {
                    "claim_id": "CLAIM-001",
                    "evidence_ids": ["EV-001"],
                }
            ],
        },
        claim_evidence_mappings=[
            {
                "claim_id": "CLAIM-001",
                "evidence_ids": ["EV-001"],
            }
        ],
        human_review_required=True,
        final_decision="PENDING_HUMAN_REVIEW",
    )

    assert record["audit_id"].startswith("AUD-")
    assert record["retrieved_evidence"]
    assert record["evidence_classification"]
    assert record["evidence_assessment"]
    assert record["absence_verification"]
    assert record["gap_analysis"]
    assert record["risk_assessment"]
    assert record["final_synthesis"]
    assert record["claim_evidence_mappings"]

    audit_id = append_audit_record(record)

    assert audit_id == record["audit_id"]

    records = load_audit_records()

    assert records
    assert any(
        item["audit_id"] == audit_id
        for item in records
    )

    print(f"Audit ID: {audit_id}")
    print(f"Audit records available: {len(records)}")

    print("\n✓ Audit record creation: PASS")
    print("✓ Evidence provenance storage: PASS")
    print("✓ Risk/governance storage: PASS")
    print("✓ Claim → evidence mapping: PASS")
    print("✓ Append-only JSONL storage: PASS")

    print("\nMISSION 12 AUDIT TRAIL: PASS")


if __name__ == "__main__":
    main()