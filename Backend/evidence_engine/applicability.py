from __future__ import annotations

from typing import Any

from .models import (
    Applicability,
    RequirementType,
)


def classify_applicability(
    value: Any,
) -> Applicability:

    value = str(value or "").upper().strip()

    mapping = {
        "DIRECT": Applicability.DIRECT,
        "PARTIAL": Applicability.PARTIAL,
        "UNCERTAIN": Applicability.UNCERTAIN,
        "NOT_APPLICABLE": Applicability.NOT_APPLICABLE,
        "NOT_ESTABLISHED": Applicability.NOT_ESTABLISHED,
    }

    return mapping.get(
        value,
        Applicability.NOT_ESTABLISHED,
    )


def classify_requirement_type(
    value: Any,
) -> RequirementType:

    value = str(value or "").upper().strip()

    mapping = {
        "MANDATORY": RequirementType.MANDATORY,
        "ADVISORY": RequirementType.ADVISORY,
        "TECHNICAL": RequirementType.TECHNICAL,
        "UNKNOWN": RequirementType.UNKNOWN,
    }

    return mapping.get(
        value,
        RequirementType.UNKNOWN,
    )