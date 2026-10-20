from __future__ import annotations
import re
from typing import Any, Dict, List, Optional


def validate_regional_claims(
    synthesis_result: Dict[str, Any],
    regional_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not regional_analysis or not isinstance(synthesis_result, dict):
        return synthesis_result

    host = regional_analysis.get("host_jurisdiction", "India")
    host_lower = host.lower()
    claims: List[Any] = synthesis_result.get("claims", [])
    validated_claims: List[Any] = []

    banned_absence_patterns = [
        re.compile(rf"no\s+{host_lower}\s+regulation\s+exists", re.IGNORECASE),
        re.compile(rf"{host_lower}\s+has\s+no\s+(?:applicable\s+)?laws?", re.IGNORECASE),
        re.compile(rf"{host_lower}\s+completely\s+lacks\s+regulation", re.IGNORECASE),
    ]

    banned_foreign_law_patterns = [
        re.compile(rf"neighbouring\s+country\s+.*creates\s+a\s+legal\s+requirement\s+for\s+{host_lower}", re.IGNORECASE),
        re.compile(rf"regional\s+evidence\s+mandates\s+that\s+{host_lower}", re.IGNORECASE),
        re.compile(rf"bangladesh\s+.*is\s+binding\s+on\s+{host_lower}", re.IGNORECASE),
        re.compile(rf"pakistan\s+.*is\s+binding\s+on\s+{host_lower}", re.IGNORECASE),
    ]

    for item in claims:
        if isinstance(item, dict):
            claim_text = item.get("claim") or item.get("statement") or item.get("text") or ""
            for pat in banned_absence_patterns:
                if pat.search(claim_text):
                    claim_text = pat.sub(
                        f"an applicable host-country provision was not established in the evidence examined for {host}",
                        claim_text,
                    )
            for pat in banned_foreign_law_patterns:
                if pat.search(claim_text):
                    claim_text = (
                        f"Regional comparative evidence was identified; however, its direct legal applicability "
                        f"to {host} is NOT established by the supplied evidence."
                    )
            item_copy = dict(item)
            if "claim" in item_copy:
                item_copy["claim"] = claim_text
            elif "statement" in item_copy:
                item_copy["statement"] = claim_text
            else:
                item_copy["text"] = claim_text
            validated_claims.append(item_copy)
        elif isinstance(item, str):
            claim_text = item
            for pat in banned_absence_patterns:
                if pat.search(claim_text):
                    claim_text = pat.sub(
                        f"an applicable host-country provision was not established in the evidence examined for {host}",
                        claim_text,
                    )
            for pat in banned_foreign_law_patterns:
                if pat.search(claim_text):
                    claim_text = (
                        f"Regional comparative evidence was identified; however, its direct legal applicability "
                        f"to {host} is NOT established by the supplied evidence."
                    )
            validated_claims.append(claim_text)
        else:
            validated_claims.append(item)

    synthesis_result["claims"] = validated_claims

    assessment = synthesis_result.get("assessment", "")
    if assessment and isinstance(assessment, str):
        for pat in banned_absence_patterns:
            assessment = pat.sub(
                f"an applicable host-country provision was not established in the evidence examined for {host}",
                assessment,
            )
        synthesis_result["assessment"] = assessment

    return synthesis_result
