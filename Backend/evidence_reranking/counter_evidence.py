from typing import Any, Dict, List


COUNTER_TERMS = [
    "however",
    "but",
    "contrary",
    "contradict",
    "contradicts",
    "contradictory",
    "inconsistent",
    "not supported",
    "does not support",
    "does not establish",
    "not covered",
    "not applicable",
    "exception",
    "limitation",
    "except",
    "alternative",
    "dispute",
    "disputed",
    "unresolved",
    "uncertain",
    "unclear",
]


def build_counter_query(
    original_query: str,
) -> str:

    return (
        f"{original_query} "
        "contradicting evidence counter evidence "
        "limitations exceptions alternative findings "
        "conflicting evidence"
    )


def counter_signal_score(
    text: str,
) -> float:

    normalized = text.lower()

    matches = 0

    for term in COUNTER_TERMS:
        if term in normalized:
            matches += 1

    if matches == 0:
        return 0.0

    return min(
        1.0,
        matches / 5.0,
    )


def identify_counter_candidates(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    results = []

    for candidate in candidates:
        item = dict(candidate)

        score = counter_signal_score(
            candidate.get("text", "")
        )

        item["counter_signal_score"] = score

        if score > 0:
            results.append(item)

    results.sort(
        key=lambda item: item["counter_signal_score"],
        reverse=True,
    )

    return results