from typing import Dict

from .models import ResponseProfile


PROFILES: Dict[str, ResponseProfile] = {

    "Maritime": ResponseProfile(
        domain="Maritime",
        sections=[
            "Incident Summary",
            "Vessel/AIS Findings",
            "Timeline",
            "Supporting Evidence",
            "Contradicting Evidence",
            "Evidence Gaps",
            "Assessment",
            "Recommendation",
        ],
        description=(
            "Maritime and AIS analysis profile."
        ),
    ),

    "Telecom/5G": ResponseProfile(
        domain="Telecom/5G",
        sections=[
            "Network Components/Topology",
            "Observed Symptoms",
            "Evidence",
            "Possible Causes",
            "Root-Cause Analysis",
            "3GPP/Standards References",
            "Technical Gap",
            "Remediation",
        ],
        description=(
            "Telecommunications and 5G technical analysis profile."
        ),
    ),

    "Policy/Compliance": ResponseProfile(
        domain="Policy/Compliance",
        sections=[
            "Existing Framework",
            "Applicable Requirements",
            "Evidence",
            "Requirement Comparison",
            "Coverage",
            "Gap",
            "Impact",
            "Recommendation",
        ],
        description=(
            "Policy, regulatory and compliance assessment profile."
        ),
    ),

    "Research": ResponseProfile(
        domain="Research",
        sections=[
            "Literature Evidence",
            "Established Findings",
            "Contradictory Findings",
            "Limitations",
            "Research Gaps",
            "Potential Research Directions",
        ],
        description=(
            "Research and literature evidence profile."
        ),
    ),

    "Defence": ResponseProfile(
        domain="Defence",
        sections=[
            "Verified Observations",
            "Evidence",
            "Supporting Evidence",
            "Contradicting Evidence",
            "Assumptions",
            "Uncertainty",
            "Evidence Gaps",
            "Analytical Assessment",
        ],
        description=(
            "Defence analytical assessment profile."
        ),
    ),

    "Enterprise Incident": ResponseProfile(
        domain="Enterprise Incident",
        sections=[
            "Incident Summary",
            "Affected Assets/Services",
            "Timeline",
            "Observed Indicators",
            "Supporting Evidence",
            "Contradicting Evidence",
            "Root-Cause Hypotheses",
            "Evidence Gaps",
            "Impact",
            "Recommended Actions",
        ],
        description=(
            "Enterprise incident investigation profile."
        ),
    ),

    "General Evidence": ResponseProfile(
        domain="General Evidence",
        sections=[
            "Assessment Summary",
            "Supporting Evidence",
            "Contradicting Evidence",
            "Contextual Evidence",
            "Evidence Gaps",
            "Conclusion",
            "Limitations",
        ],
        description=(
            "General evidence assessment profile."
        ),
    ),
}


def get_profile(domain: str) -> ResponseProfile:

    return PROFILES.get(
        domain,
        PROFILES["General Evidence"],
    )