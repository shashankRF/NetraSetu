from __future__ import annotations
import re
from typing import Any, Dict, Optional

from .models import SourceType


def classify_source_type(
    metadata: Dict[str, Any],
    text: Optional[str] = None,
) -> SourceType:
    """
    Deterministic source-type classifier grounded in NetraSetu KB provenance.
    Strictly distinguishes:
    - INTERNATIONAL_RECOMMENDATION / INTERNATIONAL_TECHNICAL_STANDARD
    - NATIONAL_REGULATION / NATIONAL_POLICY / NATIONAL_TECHNICAL_STANDARD
    - LAW / RULE / GUIDANCE
    """
    doc = str(metadata.get("document") or "").lower().strip()
    source_file = str(metadata.get("source_file") or "").lower().strip()
    folder = str(metadata.get("folder") or "").lower().strip()
    jurisdiction = str(metadata.get("jurisdiction") or "").strip()
    publisher = str(metadata.get("publisher") or "").lower().strip()
    full_text = str(text or "")[:500].lower()

        # 0. LOCAL OPERATOR POLICY / ORGANIZATIONAL REQUIREMENT
    if any(
        term in full_text or term in doc or term in source_file or term in folder
        for term in [
            "operator internal",
            "operator policy",
            "internal security policy",
            "internal security baseline",
            "operator-specific",
            "operator requirement",
            "local security requirement",
            "local operator requirement",
            "local operator policy",
            "enterprise baseline",
            "operator x",
            "internal baseline",
            "internal standard",
            "private network policy",
            "deployment-specific requirement",
            "organizational requirement",
        ]
    ):
        return SourceType.LOCAL_OPERATOR_POLICY

    # 1. ITU-T RECOMMENDATION
    if (
        "t-rec-" in doc
        or "t-rec-" in source_file
        or "itu-t" in doc
        or "itu_rules_framework" in source_file
        or "itu_rules_framework" in folder
        or "recommendation itu-t" in full_text
        or "y.3172" in doc
        or "y.3174" in doc
        or "y.3181" in doc
    ):
        return SourceType.INTERNATIONAL_RECOMMENDATION

    # 2. 3GPP TECHNICAL SPECIFICATION
    if (
        "3gpp" in doc
        or "3gpp" in source_file
        or "3gpp" in folder
        or "ts 23." in full_text
        or "ts 33." in full_text
        or "3gpp ts" in full_text
    ):
        return SourceType.INTERNATIONAL_TECHNICAL_STANDARD

    # 3. ETSI TECHNICAL SPECIFICATION / STANDARD
    if "etsi" in doc or "etsi" in source_file or "etsi" in folder:
        return SourceType.INTERNATIONAL_TECHNICAL_STANDARD

    # 4. TEC / TSDSI NATIONAL TECHNICAL STANDARD
    if (
        "tec guidelines" in folder
        or "tec guidelines" in source_file
        or " tec" in doc
        or doc.endswith("tec")
        or "oran gr" in doc
        or "gr of gnodeb" in doc
        or "tsdsi" in doc
        or "tsdsi" in source_file
    ):
        return SourceType.NATIONAL_TECHNICAL_STANDARD

    # 5. INDIAN STATUTORY ACTS / LAWS
    if (
        "indian_acts" in folder
        or "indian_acts" in source_file
        or "dpdp acts" in folder
        or "dpdp acts" in source_file
        or "it act" in doc
        or "it-act" in doc
        or "it_act" in doc
        or "dpdp act" in doc
        or "telecommunications act" in doc
        or "indian telegraph act" in doc
    ):
        return SourceType.LAW

    # 6. INDIAN NATIONAL REGULATIONS / STATUTORY RULES
    if (
        "dot_rules" in folder
        or "dot_rules" in source_file
        or "trai_act" in folder
        or "trai_act" in source_file
        or "mtcte" in folder
        or "mtcte" in source_file
        or "rules, 202" in doc
        or "rules 202" in doc
        or "rules, 19" in doc
        or "rules 19" in doc
        or "regulation_" in doc
        or "amendment_" in doc
        or "tccpr" in doc
        or "gazette" in doc
    ):
        return SourceType.NATIONAL_REGULATION

    # 7. NATIONAL POLICIES
    if (
        "vision" in doc
        or "governance" in doc
        or "policy" in doc
        or "national telecom policy" in doc
        or "ndcp" in doc
        or "bharat 6g" in doc
    ):
        return SourceType.NATIONAL_POLICY

    # 8. EU REGULATIONS & DIRECTIVES
    if "eu rules" in folder or "eu rules" in source_file or "artificial intelligence act eu" in doc or "nis2" in doc:
        return SourceType.NATIONAL_REGULATION

    # 9. MARITIME & DEFENCE
    if "maritime" in folder or "imo" in doc or "ais" in doc:
        if jurisdiction == "India":
            return SourceType.NATIONAL_REGULATION
        return SourceType.INTERNATIONAL_TECHNICAL_STANDARD

    if "defence" in folder or "drdo" in doc or "drone rules" in doc:
        if "rules" in doc:
            return SourceType.NATIONAL_REGULATION
        return SourceType.NATIONAL_TECHNICAL_STANDARD

    # Guard against unknown or unverified authority metadata
    if any(k in doc for k in ["unknown", "unverified", "blog", "anonymous", "draft note", "informal"]):
        return SourceType.OTHER

    # Fallbacks based on jurisdiction metadata
    if jurisdiction == "International":
        return SourceType.INTERNATIONAL_TECHNICAL_STANDARD
    if jurisdiction == "India":
        if "rule" in doc or "order" in doc:
            return SourceType.NATIONAL_REGULATION
        if "act" in doc:
            return SourceType.LAW
        if any(term in doc or term in folder or term in source_file for term in ["dot", "trai", "tec", "telecom", "license", "guideline", "standard"]):
            return SourceType.NATIONAL_REGULATION
        return SourceType.OTHER

    return SourceType.OTHER
