from __future__ import annotations

import json
from typing import Any, Dict, List

from .models import (
    EvidenceRole,
    EvidenceStrength,
    Applicability,
    RequirementType,
)


SYSTEM_PROMPT = """
You are HackGrid's Evidence Classification Engine.

Your job is ONLY to classify supplied evidence.

You are NOT the final decision maker.
You do NOT decide whether human review is required.
You do NOT invent facts, regulations, clauses, pages, sources, or metadata.

Use ONLY the evidence text and metadata provided.

For each claim, determine:

1. evidence_role:
   SUPPORTING
   CONTRADICTING
   LIMITING
   CONTEXTUAL

2. evidence_strength:
   STRONG
   MODERATE
   WEAK
   INSUFFICIENT

3. applicability:
   DIRECT
   PARTIAL
   UNCERTAIN
   NOT_APPLICABLE
   NOT_ESTABLISHED

4. requirement_type:
   MANDATORY
   ADVISORY
   TECHNICAL
   UNKNOWN

5. confidence:
   number from 0.0 to 1.0

6. reasoning:
   concise explanation grounded ONLY in the supplied text.

IMPORTANT:

- Do not infer a regulation merely because a technical standard exists.
- Do not treat a technical recommendation as a legal requirement.
- Do not treat retrieval failure as proof that a requirement does not exist.
- Do not modify source metadata.
- Do not invent page numbers or clauses.
- If applicability is unclear, use UNCERTAIN.
- If the text does not establish a requirement, use NOT_ESTABLISHED.
- If evidence limits a claim without directly contradicting it, use LIMITING.
- If evidence only provides background, use CONTEXTUAL.

Return ONLY valid JSON.
"""


def build_classifier_prompt(
    claim: str,
    evidence_records: List[Dict[str, Any]],
) -> str:

    return f"""
CLAIM:

{claim}

EVIDENCE RECORDS:

{json.dumps(evidence_records, indent=2, ensure_ascii=False)}

Return JSON in exactly this structure:

{{
  "claim": "{claim}",
  "classifications": [
    {{
      "evidence_id": "EV-...",
      "evidence_role": "SUPPORTING",
      "evidence_strength": "STRONG",
      "applicability": "DIRECT",
      "requirement_type": "MANDATORY",
      "confidence": 0.90,
      "reasoning": "..."
    }}
  ]
}}
"""


def validate_classification(
    result: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Validate that the LLM only refers to supplied evidence IDs
    and valid controlled vocabulary.
    """

    valid_ids = {
        record["evidence_id"]
        for record in evidence_records
    }

    valid_roles = {
        item.value for item in EvidenceRole
    }

    valid_strengths = {
        item.value for item in EvidenceStrength
    }

    valid_applicability = {
        item.value for item in Applicability
    }

    valid_requirement_types = {
        item.value for item in RequirementType
    }

    classifications = result.get(
        "classifications",
        [],
    )

    validated = []

    for item in classifications:

        evidence_id = item.get(
            "evidence_id"
        )

        if evidence_id not in valid_ids:
            continue

        role = str(
            item.get("evidence_role", "")
        ).upper()

        strength = str(
            item.get("evidence_strength", "")
        ).upper()

        applicability = str(
            item.get("applicability", "")
        ).upper()

        requirement_type = str(
            item.get("requirement_type", "")
        ).upper()

        if role not in valid_roles:
            role = EvidenceRole.CONTEXTUAL.value

        if strength not in valid_strengths:
            strength = EvidenceStrength.INSUFFICIENT.value

        if applicability not in valid_applicability:
            applicability = Applicability.NOT_ESTABLISHED.value

        if requirement_type not in valid_requirement_types:
            requirement_type = RequirementType.UNKNOWN.value

        try:
            confidence = float(
                item.get("confidence", 0.0)
            )
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        validated.append(
            {
                "evidence_id": evidence_id,
                "evidence_role": role,
                "evidence_strength": strength,
                "applicability": applicability,
                "requirement_type": requirement_type,
                "confidence": confidence,
                "reasoning": str(
                    item.get("reasoning", "")
                ),
            }
        )

    return {
        "claim": result.get(
            "claim",
            "",
        ),
        "classifications": validated,
    }