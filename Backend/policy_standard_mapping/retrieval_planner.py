from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from rag.retrieval import retrieve


COMPARISON_TERMS = [
    "compare",
    "comparison",
    "vs",
    "versus",
    "mapping",
    "map",
    "crosswalk",
    "align",
    "alignment",
    "gap",
    "gaps",
    "harmonize",
    "harmonization",
    "equivalent",
    "relationship between",
]

INTERNATIONAL_STANDARDS = [
    ("y.3172", "ITU-T Y.3172 machine learning architectural framework future networks"),
    ("y.3174", "ITU-T Y.3174 machine learning architecture data handling"),
    ("y.3181", "ITU-T Y.3181 machine learning intelligence levels"),
    ("3gpp", "3GPP technical specification network slicing architecture security"),
    ("etsi", "ETSI security standards specification telecom"),
]


def is_comparison_intent(question: str) -> bool:
    """
    Detect whether user question requests a comparison or standard-to-policy mapping.
    """
    lower = question.lower()
    has_comp_term = any(t in lower for t in COMPARISON_TERMS)
    has_intl = any(name in lower for name, _ in INTERNATIONAL_STANDARDS) or "standard" in lower or "international" in lower
    has_national = any(nat in lower for nat in ["india", "indian", "national", "dot", "trai", "tec", "eu", "european"])
    
    return (has_comp_term and (has_intl or has_national)) or (has_intl and has_national)


def plan_and_retrieve_evidence(
    question: str,
    k: int = 10,
    jurisdiction: Optional[str] = "India",
    domains: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Intent-aware multi-sided retrieval for HackGrid.
    Ensures that comparison/mapping queries retrieve BOTH international technical standards
    and applicable national provisions from the Knowledge Base.
    """
    # 1. Base retrieval
    base_results = retrieve(
        query=question,
        k=k,
        jurisdiction=jurisdiction,
        domains=domains,
    )

    if not is_comparison_intent(question):
        return base_results

    # 2. Check representation of both sides
    intl_results = []
    nat_results = []
    for r in base_results:
        jur = r.get("metadata", {}).get("jurisdiction")
        if jur == "International":
            intl_results.append(r)
        elif jur == jurisdiction:
            nat_results.append(r)

    merged = list(base_results)
    seen_keys = {
        (r.get("kb"), r.get("metadata", {}).get("chunk_id") or r.get("metadata", {}).get("document") or r.get("text", "")[:80])
        for r in base_results
    }

    # 3. Retrieve National side if under-represented
    min_side_quota = max(2, min(k // 4, 4))
    if len(nat_results) < min_side_quota and jurisdiction:
        domain_str = " ".join(domains) if domains else "telecom"
        nat_query = f"{jurisdiction} telecom network security regulations requirements architecture {domain_str}"
        extra_nat = retrieve(
            query=nat_query,
            k=min_side_quota * 2,
            jurisdiction=jurisdiction,
            domains=domains,
        )
        for r in extra_nat:
            key = (r.get("kb"), r.get("metadata", {}).get("chunk_id") or r.get("metadata", {}).get("document") or r.get("text", "")[:80])
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(r)

    # 4. Retrieve International side if specific standard requested but under-represented
    lower_q = question.lower()
    for std_name, std_query in INTERNATIONAL_STANDARDS:
        if std_name in lower_q and len(intl_results) < min_side_quota:
            extra_intl = retrieve(
                query=std_query,
                k=min_side_quota * 2,
                jurisdiction=jurisdiction,
                domains=domains,
            )
            for r in extra_intl:
                key = (r.get("kb"), r.get("metadata", {}).get("chunk_id") or r.get("metadata", {}).get("document") or r.get("text", "")[:80])
                if key not in seen_keys:
                    seen_keys.add(key)
                    merged.append(r)
            break

    return merged
