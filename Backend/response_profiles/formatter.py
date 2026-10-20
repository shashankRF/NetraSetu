from typing import Any, Dict

from .profiles import get_profile


def build_response_profile(
    classification: Dict[str, Any],
) -> Dict[str, Any]:

    domain = classification.get(
        "domain",
        "General Evidence",
    )

    intent = classification.get(
        "intent",
        "Evidence Assessment",
    )

    confidence = classification.get(
        "confidence",
        0.0,
    )

    profile = get_profile(domain)

    return {
        "domain": profile.domain,
        "intent": intent,
        "confidence": confidence,
        "sections": profile.sections,
        "description": profile.description,
    }