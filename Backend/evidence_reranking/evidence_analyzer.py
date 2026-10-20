from typing import Any, Dict, List

from .counter_evidence import identify_counter_candidates
from .models import EvidenceAnalysisResult


SUPPORT_TERMS = [
    "requires",
    "requirement",
    "requires that",
    "shall",
    "must",
    "supports",
    "support",
    "covered",
    "provides",
    "prohibits",
    "mandates",
    "specified",
    "defined",
]


CONTRADICT_TERMS = [
    "contradicts",
    "contradict",
    "not supported",
    "does not support",
    "does not establish",
    "not covered",
    "not applicable",
    "exception",
    "inconsistent",
    "conflicting",
]


CONTEXT_TERMS = [
    "definition",
    "background",
    "overview",
    "context",
    "describes",
    "refers to",
    "introduction",
]


def _term_score(
    text: str,
    terms: List[str],
) -> float:

    normalized = text.lower()

    count = sum(
        1
        for term in terms
        if term in normalized
    )

    return min(
        1.0,
        count / 3.0,
    )


def classify_evidence_role(
    text: str,
) -> tuple[str, float]:

    normalized = text.lower()

    # Contradicting language has priority over
    # generic supporting language.
    contradicting = _term_score(
        normalized,
        CONTRADICT_TERMS,
    )

    supporting = _term_score(
        normalized,
        SUPPORT_TERMS,
    )

    contextual = _term_score(
        normalized,
        CONTEXT_TERMS,
    )

    # Explicit contradiction is stronger than a generic
    # occurrence of words such as "requirement", "shall",
    # or "supports".
    explicit_contradiction_phrases = [
        "does not establish",
        "does not support",
        "not supported",
        "not covered",
        "not applicable",
        "contradicts",
        "contradict",
        "inconsistent",
        "conflicting",
    ]

    explicit_contradiction = any(
        phrase in normalized
        for phrase in explicit_contradiction_phrases
    )

    if explicit_contradiction:
        return (
            "Contradicting Evidence",
            max(contradicting, 0.75),
        )

    scores = {
        "Supporting Evidence": supporting,
        "Contradicting Evidence": contradicting,
        "Contextual Evidence": contextual,
    }

    role = max(
        scores,
        key=scores.get,
    )

    confidence = scores[role]

    if confidence <= 0:
        return (
            "Contextual Evidence",
            0.30,
        )

    return (
        role,
        confidence,
    )

def analyze_evidence(
    candidates: List[Dict[str, Any]],
    query: str,
    final_top_k: int,
) -> EvidenceAnalysisResult:

    if not isinstance(candidates, list):
        raise TypeError(
            "candidates must be a list"
        )

    supporting = []
    contradicting = []
    contextual = []

    for candidate in candidates[:final_top_k]:

        role, confidence = classify_evidence_role(
            candidate.get("text", "")
        )

        item = dict(candidate)

        item["role"] = role
        item["role_confidence"] = confidence

        if role == "Supporting Evidence":
            supporting.append(item)

        elif role == "Contradicting Evidence":
            contradicting.append(item)

        else:
            contextual.append(item)

    counter_candidates = identify_counter_candidates(
        candidates
    )

    existing_ids = {
        item.get("evidence_id")
        for item in contradicting
    }

    for candidate in counter_candidates:

        evidence_id = candidate.get(
            "evidence_id"
        )

        if evidence_id in existing_ids:
            continue

        if len(contradicting) >= final_top_k:
            break

        item = dict(candidate)

        item["role"] = "Contradicting Evidence"
        item["role_confidence"] = candidate.get(
            "counter_signal_score",
            0.0,
        )

        contradicting.append(item)
        existing_ids.add(evidence_id)

    gaps = []

    if not supporting:
        gaps.append(
            "No clearly supporting evidence was identified "
            "within the selected evidence."
        )

    if not contradicting:
        gaps.append(
            "No clearly contradicting evidence was identified "
            "within the selected evidence."
        )

    if not contextual:
        gaps.append(
            "No contextual evidence was identified "
            "within the selected evidence."
        )

    return EvidenceAnalysisResult(
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        contextual_evidence=contextual,
        evidence_gaps=gaps,
        candidate_count=len(candidates),
        final_top_k=min(
            final_top_k,
            len(candidates),
        ),
        contradiction_search_performed=True,
    )