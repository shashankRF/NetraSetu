from __future__ import annotations

from typing import Any, Dict, List

from .models import (
    Applicability,
    ClaimAssessment,
    EvidenceItem,
    EvidenceMetadata,
    EvidenceRole,
    EvidenceStrength,
    EvidenceStatus,
    RequirementType,
)


def _enum_value(
    enum_class,
    value,
    default,
):
    try:
        return enum_class(value)
    except (ValueError, TypeError):
        return default


def build_claim_assessment(
    classification: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> ClaimAssessment:

    records_by_id = {
        record["evidence_id"]: record
        for record in evidence_records
    }

    supporting = []
    contradicting = []
    limiting = []
    contextual = []

    for item in classification.get(
        "classifications",
        [],
    ):

        evidence_id = item.get(
            "evidence_id"
        )

        record = records_by_id.get(
            evidence_id
        )

        if not record:
            continue

        metadata = record.get(
            "metadata",
            {}
        )

        evidence_metadata = EvidenceMetadata(
            document=metadata.get(
                "document",
                ""
            ),
            publisher=metadata.get(
                "publisher",
                ""
            ),
            source_type=metadata.get(
                "source_type",
                metadata.get(
                    "document_type",
                    ""
                ),
            ),
            jurisdiction=metadata.get(
                "jurisdiction",
                ""
            ),
            page=metadata.get("page"),
            section=metadata.get(
                "section",
                ""
            ),
            clause=metadata.get(
                "clause",
                ""
            ),
            chunk_id=metadata.get(
                "chunk_id",
                ""
            ),
            retrieval_rank=record.get(
                "retrieval_rank"
            ),
            version=metadata.get(
                "version",
                ""
            ),
            publication_date=metadata.get(
                "publication_date"
            ),
            effective_date=metadata.get(
                "effective_date"
            ),
            expiry_date=metadata.get(
                "expiry_date"
            ),
        )

        evidence_item = EvidenceItem(
            evidence_id=evidence_id,
            claim_id="CLAIM-001",
            claim_text=classification.get(
                "claim",
                ""
            ),
            evidence_text=record.get(
                "evidence_text",
                record.get(
                    "text",
                    ""
                ),
            ),
            role=_enum_value(
                EvidenceRole,
                item.get("evidence_role"),
                EvidenceRole.CONTEXTUAL,
            ),
            strength=_enum_value(
                EvidenceStrength,
                item.get("evidence_strength"),
                EvidenceStrength.INSUFFICIENT,
            ),
            applicability=_enum_value(
                Applicability,
                item.get("applicability"),
                Applicability.UNCERTAIN,
            ),
            requirement_type=_enum_value(
                RequirementType,
                item.get("requirement_type"),
                RequirementType.UNKNOWN,
            ),
            metadata=evidence_metadata,
            confidence=float(
                item.get(
                    "confidence",
                    0.0
                )
            ),
            limitations=[],
        )

        if evidence_item.role == EvidenceRole.SUPPORTING:
            supporting.append(evidence_item)

        elif evidence_item.role == EvidenceRole.CONTRADICTING:
            contradicting.append(evidence_item)

        elif evidence_item.role == EvidenceRole.LIMITING:
            limiting.append(evidence_item)

        else:
            contextual.append(evidence_item)

    if contradicting:
        status = EvidenceStatus.CONFLICTING

    elif supporting:
        status = EvidenceStatus.SUFFICIENT

    elif limiting:
        status = EvidenceStatus.PARTIALLY_ESTABLISHED

    else:
        status = EvidenceStatus.INSUFFICIENT

    all_items = (
        supporting
        + contradicting
        + limiting
        + contextual
    )

    confidence_values = [
        item.confidence
        for item in all_items
    ]

    confidence = (
        sum(confidence_values)
        / len(confidence_values)
        if confidence_values
        else 0.0
    )

    return ClaimAssessment(
        claim_id="CLAIM-001",
        claim_text=classification.get(
            "claim",
            ""
        ),
        supporting=supporting,
        contradicting=contradicting,
        limiting=limiting,
        contextual=contextual,
        status=status,
        applicability=(
            supporting[0].applicability
            if supporting
            else Applicability.UNCERTAIN
        ),
        confidence=confidence,
        limitations=[],
    )