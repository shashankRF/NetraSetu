from __future__ import annotations
from typing import Any, Dict, Union

from .models import RegionalComparativeAnalysisResult


def format_regional_comparative_markdown(
    result: Union[RegionalComparativeAnalysisResult, Dict[str, Any]]
) -> str:
    data = result.to_dict() if isinstance(result, RegionalComparativeAnalysisResult) else result

    host = data.get("host_jurisdiction", "India")
    reg_list = ", ".join(data.get("regional_jurisdictions", [])) or "None identified"
    coverage = data.get("coverage_status", "Not Established")
    gap_status = data.get("gap_status", "POTENTIAL GAP - NOT ESTABLISHED")
    why = data.get("reasoning", "")
    impact = data.get("impact", "")
    remediation = data.get("remediation", "")
    counter_ev = data.get("counter_evidence_summary", "None")
    limitation = data.get("limitations", "")

    intl_reqs = data.get("international_requirements", [])
    host_reqs = data.get("host_requirements", [])
    reg_reqs = data.get("regional_requirements", [])

    intl_ev_str = ", ".join(r.get("evidence_id") or "EV-INTL" for r in intl_reqs) if intl_reqs else "None"
    host_ev_str = ", ".join(r.get("evidence_id") or "EV-HOST" for r in host_reqs) if host_reqs else "None retrieved"
    reg_ev_str = ", ".join(r.get("evidence_id") or "EV-REG" for r in reg_reqs) if reg_reqs else "None available in KB"

    intl_summary = (
        intl_reqs[0].get("requirement_summary") or intl_reqs[0].get("requirement_text")
        if intl_reqs else "International technical security requirement"
    )

    reg_summary = (
        f"Comparative evidence evaluated for neighbouring jurisdictions ({reg_list}). "
        + ("Explicit control identified in comparative jurisdiction." if reg_reqs else "Sufficient comparative evidence was not available in current KB.")
    )

    return f"""### Regional Comparative Gap Analysis

HOST:
{host}

REGIONAL COMPARISON:
{host} + relevant neighbouring jurisdictions ({reg_list})

INTERNATIONAL REQUIREMENT:
{intl_summary}

HOST-COUNTRY COVERAGE:
{coverage}

REGIONAL COMPARISON:
{reg_summary}

GAP STATUS:
{gap_status}

EVIDENCE:
International: {intl_ev_str}
Host: {host_ev_str}
Regional: {reg_ev_str}

WHY:
{why}

IMPACT:
{impact}

REMEDIATION:
{remediation}

COUNTER-EVIDENCE:
{counter_ev}

LIMITATION:
{limitation}
"""
