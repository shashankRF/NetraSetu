from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from .models import (
    ExtractedRequirement,
    RequirementType,
    ApplicabilityStatus,
    SourceType,
)
from .source_classifier import classify_source_type


def _extract_clause_or_section(text: str, meta: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Safely extract clause and section metadata without inventing values.
    Returns (clause, section).
    """
    clause = meta.get("clause")
    section = meta.get("section")

    if clause or section:
        return str(clause) if clause else None, str(section) if section else None

    # Deterministic pattern matching on authoritative headings in text
    clause_match = re.search(r'\b(?:Clause|clause)\s+([0-9]+(?:\.[0-9]+)*)', text)
    if clause_match:
        clause = clause_match.group(1)

    sec_match = re.search(r'\b(?:Section|section)\s+([0-9]+(?:\.[0-9]+)*|[0-9]+[A-Za-z]*)', text)
    if sec_match:
        section = sec_match.group(1)

    return clause, section


def _summarize_requirement_text(text: str, max_words: int = 40) -> str:
    """
    Summarize requirement from actual text without adding external facts.
    """
    clean_lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not clean_lines:
        return "Requirement text not provided."

    # Find the most requirement-dense sentence (containing 'shall', 'must', 'require', 'framework', 'pipeline', 'architecture')
    for line in clean_lines:
        lower_line = line.lower()
        if any(k in lower_line for k in ["shall", "must", "architectural requirement", "specifies", "requires", "responsible for"]):
            words = line.split()
            if len(words) > max_words:
                return " ".join(words[:max_words]) + "..."
            return line

    first_line = clean_lines[0]
    words = first_line.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return first_line


def extract_requirement_from_evidence(
    record: Dict[str, Any],
    index: int,
) -> ExtractedRequirement:
    """
    Extract requirement object from a retrieved evidence record.
    Never invents missing metadata.
    """
    evidence_id = record.get("evidence_id") or f"EV-{index:03d}"
    text = record.get("text") or record.get("content") or ""
    provenance = record.get("provenance", {}) or record.get("metadata", {}) or {}
    
    document = str(provenance.get("document") or provenance.get("source_file") or "Unknown Document")
    source_type = classify_source_type(provenance, text)
    jurisdiction = str(provenance.get("jurisdiction") or "International")
    page = provenance.get("page")
    try:
        page_int = int(page) if page is not None else None
    except (ValueError, TypeError):
        page_int = None

    clause, section = _extract_clause_or_section(text, provenance)

    # Determine status
    lower_text = text.lower()
    if source_type in {SourceType.INTERNATIONAL_RECOMMENDATION, SourceType.INTERNATIONAL_TECHNICAL_STANDARD}:
        status = RequirementType.TECHNICAL
    elif source_type == SourceType.OTHER:
        status = RequirementType.UNKNOWN
    elif any(term in lower_text for term in ["shall", "must", "is required to", "mandatory", "statutory duty"]):
        status = RequirementType.MANDATORY
    elif any(term in lower_text for term in ["should", "recommended", "advisory", "guidelines"]):
        status = RequirementType.ADVISORY
    elif any(term in lower_text for term in ["architecture", "framework", "specification", "format", "interface"]):
        status = RequirementType.TECHNICAL
    else:
        status = RequirementType.UNKNOWN

    # Determine domain
    if "y.3172" in document.lower() or "machine learning in future networks" in lower_text:
        domain = "ML Telecom Architecture (ITU-T Y.3172)"
    elif "5g" in lower_text or "slice" in lower_text or "3gpp" in document.lower():
        domain = "5G Network Architecture / Slicing"
    elif "lawful interception" in document.lower():
        domain = "Lawful Interception Security"
    elif "maritime" in lower_text:
        domain = "Maritime Telecom / AIS"
    elif "defence" in lower_text or "drone" in lower_text:
        domain = "Defence / Strategic Communication"
    else:
        domain = "Telecommunications & Cybersecurity"

    summary = _summarize_requirement_text(text)

    return ExtractedRequirement(
        requirement_id=f"REQ-{index:03d}",
        source=document,
        source_type=source_type,
        document=document,
        clause=clause,
        section=section,
        page=page_int,
        requirement_text=text[:600],
        requirement_summary=summary,
        technology_domain=domain,
        jurisdiction=jurisdiction,
        status=status,
        applicability=ApplicabilityStatus.DIRECT if ("y.3172" in document.lower() or "5g" in lower_text) else ApplicabilityStatus.PARTIAL,
        evidence_id=evidence_id,
    )
