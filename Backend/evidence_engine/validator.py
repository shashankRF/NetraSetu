from __future__ import annotations

from typing import Any, Dict, List


VALID_ROLES = {
    "SUPPORTING",
    "CONTRADICTING",
    "LIMITING",
    "CONTEXTUAL",
}

VALID_STRENGTHS = {
    "STRONG",
    "MODERATE",
    "WEAK",
    "INSUFFICIENT",
}

VALID_APPLICABILITY = {
    "DIRECT",
    "PARTIAL",
    "UNCERTAIN",
    "NOT_APPLICABLE",
    "NOT_ESTABLISHED",
}

VALID_REQUIREMENT_TYPES = {
    "MANDATORY",
    "ADVISORY",
    "TECHNICAL",
    "UNKNOWN",
}


def validate_evidence_consistency(
    classifications: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:

    errors = []
    warnings = []

    evidence_map = {
        item["evidence_id"]: item
        for item in evidence_records
    }

    for item in classifications.get("classifications", []):

        evidence_id = item.get("evidence_id")

        if evidence_id not in evidence_map:
            errors.append(
                f"Unknown evidence ID: {evidence_id}"
            )
            continue

        role = item.get("evidence_role")
        strength = item.get("evidence_strength")
        applicability = item.get("applicability")
        requirement_type = item.get("requirement_type")

        if role not in VALID_ROLES:
            errors.append(
                f"{evidence_id}: invalid evidence role"
            )

        if strength not in VALID_STRENGTHS:
            errors.append(
                f"{evidence_id}: invalid evidence strength"
            )

        if applicability not in VALID_APPLICABILITY:
            errors.append(
                f"{evidence_id}: invalid applicability"
            )

        if requirement_type not in VALID_REQUIREMENT_TYPES:
            errors.append(
                f"{evidence_id}: invalid requirement type"
            )

        confidence = item.get("confidence")

        if not isinstance(confidence, (int, float)):
            errors.append(
                f"{evidence_id}: invalid confidence"
            )
        elif not 0.0 <= confidence <= 1.0:
            errors.append(
                f"{evidence_id}: confidence outside 0-1"
            )

        if (
            applicability == "NOT_APPLICABLE"
            and role == "SUPPORTING"
        ):
            warnings.append(
                f"{evidence_id}: NOT_APPLICABLE "
                "evidence classified as SUPPORTING"
            )

        if (
            applicability == "NOT_ESTABLISHED"
            and role == "SUPPORTING"
        ):
            warnings.append(
                f"{evidence_id}: applicability not established "
                "but evidence is SUPPORTING"
            )

        if (
            requirement_type == "MANDATORY"
            and strength == "INSUFFICIENT"
        ):
            warnings.append(
                f"{evidence_id}: MANDATORY classification "
                "has INSUFFICIENT evidence strength"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "classification_count": len(
            classifications.get("classifications", [])
        ),
    }