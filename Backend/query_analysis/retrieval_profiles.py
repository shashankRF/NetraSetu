PROFILES = {
    "Maritime": {
        "retrieval_strategy": "maritime_evidence",
        "agents": [
            "Maritime Incident Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "MARITIME",
    },

    "Telecom/5G": {
        "retrieval_strategy": "telecom_technical_standards",
        "agents": [
            "Network Analysis Agent",
            "Compliance Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "TELECOM_5G",
    },

    "Defence": {
        "retrieval_strategy": "defence_evidence",
        "agents": [
            "Defence Analysis Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "DEFENCE",
    },

    "Policy/Compliance": {
        "retrieval_strategy": "policy_regulatory",
        "agents": [
            "Compliance Agent",
            "Policy Analysis Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "POLICY_COMPLIANCE",
    },

    "Research": {
        "retrieval_strategy": "research_literature",
        "agents": [
            "Research Analysis Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "RESEARCH",
    },

    "Enterprise Incident": {
        "retrieval_strategy": "enterprise_incident",
        "agents": [
            "Incident Analysis Agent",
            "Root Cause Analysis Agent",
            "Evidence Analysis Agent",
        ],
        "response_profile": "ENTERPRISE_INCIDENT",
    },

    "General Evidence": {
        "retrieval_strategy": "general_evidence",
        "agents": [
            "Evidence Analysis Agent",
        ],
        "response_profile": "GENERAL_EVIDENCE",
    },
}


def get_profile(domain: str) -> dict:
    return PROFILES.get(
        domain,
        PROFILES["General Evidence"],
    )