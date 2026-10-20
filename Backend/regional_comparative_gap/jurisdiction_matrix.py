from __future__ import annotations
from typing import Any, Dict, List, Set


REGIONAL_NEIGHBOUR_MAP: Dict[str, Dict[str, List[str]]] = {
    "India": {
        "telecom": ["Bangladesh", "Sri Lanka", "Pakistan", "Nepal", "Bhutan", "Singapore", "Japan"],
        "maritime": ["Sri Lanka", "Maldives", "Bangladesh", "Myanmar", "Indonesia", "Seychelles"],
        "defence": ["Pakistan", "Bangladesh", "Nepal", "Sri Lanka"],
        "general": ["Bangladesh", "Nepal", "Sri Lanka", "Pakistan", "Bhutan"],
    },
    "European Union": {
        "telecom": ["United Kingdom", "Switzerland", "Norway"],
        "maritime": ["United Kingdom", "Norway"],
        "defence": ["United Kingdom", "Norway", "Switzerland"],
        "general": ["United Kingdom", "Switzerland", "Norway"],
    },
}

DEFAULT_REGIONAL_NEIGHBOURS = {
    "India": ["Bangladesh", "Sri Lanka", "Pakistan", "Nepal", "Bhutan"],
    "European Union": ["United Kingdom", "Switzerland", "Norway"],
}


def get_relevant_regional_jurisdictions(
    host_jurisdiction: str,
    domain: str = "telecom",
    question: str = "",
) -> List[str]:
    host_norm = "India" if host_jurisdiction.lower() in {"india", "in", "ind"} else host_jurisdiction
    domain_norm = domain.lower() if domain else "telecom"

    host_domains = REGIONAL_NEIGHBOUR_MAP.get(host_norm, {})
    candidates = host_domains.get(domain_norm, host_domains.get("general", DEFAULT_REGIONAL_NEIGHBOURS.get(host_norm, [])))

    q_lower = question.lower()
    all_known = [
        "bangladesh", "sri lanka", "pakistan", "nepal", "bhutan",
        "singapore", "japan", "south korea", "maldives", "myanmar",
        "indonesia", "united kingdom", "switzerland", "norway", "vietnam", "malaysia"
    ]
    specific_mentioned = []
    for c in all_known:
        if c in q_lower:
            name = c.title()
            if name not in specific_mentioned and name.lower() != host_norm.lower():
                specific_mentioned.append(name)

    if specific_mentioned:
        combined = specific_mentioned + [c for c in candidates if c not in specific_mentioned]
        return combined[:5]

    return list(candidates[:4])


def assess_regional_kb_coverage(
    host_jurisdiction: str,
    regional_jurisdictions: List[str],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, str]:
    host_norm = host_jurisdiction.lower()
    has_host = False
    has_intl = False
    found_regional: Set[str] = set()

    for rec in evidence_records:
        rec_jur = (rec.get("jurisdiction") or rec.get("metadata", {}).get("jurisdiction") or "").lower()
        doc = (rec.get("document") or rec.get("metadata", {}).get("document") or "").lower()
        src = (rec.get("source") or rec.get("metadata", {}).get("source_file") or "").lower()

        if host_norm in rec_jur or "dot" in doc or "tec" in doc or "trai" in doc:
            has_host = True
        if "international" in rec_jur or "3gpp" in doc or "3gpp" in src or "itu" in doc or "etsi" in doc:
            has_intl = True

        for rj in regional_jurisdictions:
            rj_l = rj.lower()
            if rj_l in rec_jur or rj_l in doc or rj_l in src:
                found_regional.add(rj)

    host_avail = "AVAILABLE" if has_host else "NOT ESTABLISHED"
    coverage: Dict[str, str] = {
        "Host": f"{host_jurisdiction} - {host_avail}",
        "International": "AVAILABLE" if has_intl else "NOT ESTABLISHED",
    }

    if not regional_jurisdictions:
        coverage["Regional"] = "NOT ESTABLISHED"
    elif len(found_regional) == len(regional_jurisdictions):
        coverage["Regional"] = "AVAILABLE"
    elif len(found_regional) > 0:
        found_sorted = ", ".join(sorted(found_regional))
        coverage["Regional"] = f"PARTIAL ({found_sorted})"
    else:
        coverage["Regional"] = "NOT ESTABLISHED"

    return coverage
