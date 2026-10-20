from __future__ import annotations

from typing import Any, Dict

from .models import (
    EvidenceRole,
    EvidenceStrength,
)


def classify_role(value: Any) -> EvidenceRole:
    value = str(value or "").upper().strip()

    mapping = {
        "SUPPORTING": EvidenceRole.SUPPORTING,
        "CONTRADICTING": EvidenceRole.CONTRADICTING,
        "LIMITING": EvidenceRole.LIMITING,
        "CONTEXTUAL": EvidenceRole.CONTEXTUAL,
    }

    return mapping.get(
        value,
        EvidenceRole.CONTEXTUAL,
    )


def classify_strength(
    value: Any,
) -> EvidenceStrength:
    value = str(value or "").upper().strip()

    mapping = {
        "STRONG": EvidenceStrength.STRONG,
        "MODERATE": EvidenceStrength.MODERATE,
        "WEAK": EvidenceStrength.WEAK,
        "INSUFFICIENT": EvidenceStrength.INSUFFICIENT,
    }

    return mapping.get(
        value,
        EvidenceStrength.INSUFFICIENT,
    )


def count_source_types(
    evidence_items,
) -> Dict[str, int]:

    result = {}

    for item in evidence_items:
        source_type = item.metadata.source_type

        if not source_type:
            continue

        result[source_type] = (
            result.get(source_type, 0) + 1
        )

    return result