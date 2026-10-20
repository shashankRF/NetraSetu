import re
from typing import Dict, List, Tuple

from .models import QueryClassification, DOMAINS, INTENTS
from .retrieval_profiles import get_profile


DOMAIN_KEYWORDS: Dict[str, List[str]] = {

    "Maritime": [
        "maritime",
        "vessel",
        "ship",
        "ships",
        "boat",
        "cargo ship",
        "container ship",
        "tanker",
        "merchant vessel",
        "naval vessel",
        "ais",
        "automatic identification system",
        "imo",
        "mmsi",
        "port",
        "harbor",
        "harbour",
        "seaport",
        "shipping",
        "shipping lane",
        "voyage",
        "voyage data",
        "anchorage",
        "collision",
        "grounding",
        "piracy",
        "smuggling at sea",
        "coastal",
        "offshore",
        "marine",
    ],

    "Telecom/5G": [
        "5g",
        "4g",
        "6g",
        "telecom",
        "telecommunications",
        "mobile network",
        "cellular",
        "ran",
        "o-ran",
        "oran",
        "open ran",
        "5gc",
        "5g core",
        "network slicing",
        "slice",
        "network slice",
        "amf",
        "smf",
        "upf",
        "udm",
        "ausf",
        "nef",
        "pcf",
        "nrf",
        "gnb",
        "base station",
        "radio access network",
        "srsran",
        "open5gs",
        "3gpp",
        "itu",
        "mmwave",
        "mimo",
        "ran security",
        "telecom security",
    ],

    "Defence": [
        "defence",
        "defense",
        "military",
        "armed forces",
        "army",
        "navy",
        "air force",
        "airforce",
        "soldier",
        "battlefield",
        "warfare",
        "combat",
        "surveillance",
        "reconnaissance",
        "isr",
        "intelligence surveillance reconnaissance",
        "radar",
        "radar swarm",
        "drone",
        "uav",
        "unmanned aerial vehicle",
        "missile",
        "air defence",
        "air defense",
        "electronic warfare",
        "ew",
        "military communication",
        "military communications",
        "strategic defence",
        "strategic defense",
    ],

    "Policy/Compliance": [
        "policy",
        "regulation",
        "regulatory",
        "compliance",
        "law",
        "legal requirement",
        "regulatory requirement",
        "mandatory requirement",
        "applicable requirement",
        "standard",
        "standards",
        "framework",
        "governance",
        "jurisdiction",
        "legislation",
        "act",
        "rule",
        "guideline",
        "guidelines",
        "notification",
        "directive",
        "audit requirement",
        "certification",
        "certification requirement",
        "statutory",
        "regulator",
        "regulatory framework",
        "policy gap",
        "compliance gap",
    ],

    "Research": [
        "research",
        "paper",
        "papers",
        "literature",
        "journal",
        "publication",
        "study",
        "studies",
        "research gap",
        "literature gap",
        "hypothesis",
        "experiment",
        "experimental",
        "methodology",
        "method",
        "novel",
        "novelty",
        "state of the art",
        "sota",
        "benchmark",
        "dataset",
        "review paper",
        "systematic review",
        "future work",
        "research direction",
    ],

    "Enterprise Incident": [
        "incident",
        "enterprise incident",
        "security incident",
        "cyber incident",
        "outage",
        "service outage",
        "system failure",
        "production failure",
        "breach",
        "data breach",
        "intrusion",
        "attack",
        "malware",
        "ransomware",
        "phishing",
        "compromise",
        "compromised",
        "unauthorized access",
        "service disruption",
        "downtime",
        "alert",
        "alerts",
        "siem",
        "soc",
        "log",
        "logs",
        "incident response",
        "forensic",
        "forensics",
    ],
}


INTENT_KEYWORDS: Dict[str, List[str]] = {

    "Incident Analysis": [
        "incident",
        "event",
        "what happened",
        "analyze the incident",
        "analyse the incident",
        "incident analysis",
        "event analysis",
        "investigate",
        "investigation",
        "timeline",
        "sequence of events",
        "analyze",
        "analyse",
        "anomalously",
        "anomaly",
        "anomalous",
        "behavior",
        "behaviour",
        "vessel behaved",
    ],

    "Threat Analysis": [
        "threat",
        "threat analysis",
        "threat assessment",
        "attack",
        "attacker",
        "adversary",
        "malicious",
        "vulnerability",
        "exploit",
        "exploitation",
        "risk from",
        "security threat",
        "cyber threat",
        "threat actor",
    ],

    "Root Cause Analysis": [
        "root cause",
        "root-cause",
        "why did",
        "why did this happen",
        "cause of",
        "caused by",
        "underlying cause",
        "failure cause",
        "fault analysis",
        "diagnose",
        "diagnosis",
        "determine the cause",
    ],

    "Compliance": [
        "compliance",
        "compliant",
        "comply",
        "requirement",
        "requirements",
        "regulatory requirement",
        "legal requirement",
        "applicable regulation",
        "does this meet",
        "does this satisfy",
        "is this allowed",
        "mandatory",
        "certification",
        "audit",
        "cover",
        "covers",
        "covered",
        "framework",
        "satisfy",
        "meets",
        "meet",
        "applicable",
    ],

    "Policy Gap": [
        "policy gap",
        "regulatory gap",
        "compliance gap",
        "standards gap",
        "gap in regulation",
        "gap in policy",
        "missing regulation",
        "missing policy",
        "no regulation",
        "no policy",
        "does not cover",
        "not covered by regulation",
        "coverage gap",
        "establish a regulatory gap",
        "establishes a regulatory gap",
        "evidence establish a regulatory gap",
        "evidence establishes a regulatory gap",
        "regulatory gap",
        "policy gap",
    ],

    "Research Gap": [
        "research gap",
        "research gaps",
        "literature gap",
        "knowledge gap",
        "what is missing in research",
        "open research problem",
        "open problem",
        "future research",
        "research direction",
        "what remains unsolved",
        "unsolved problem",
        "novel research",
    ],

    "Evidence Assessment": [
        "evidence",
        "assess the evidence",
        "evaluate the evidence",
        "evidence assessment",
        "supporting evidence",
        "contradicting evidence",
        "contradictory evidence",
        "counter evidence",
        "counter-evidence",
        "is there evidence",
        "what evidence",
        "prove",
        "proves",
        "establish",
        "establishes",
        "substantiated",
        "supported by the evidence",
    ],
}


# Some phrases are much stronger indicators than individual words.
STRONG_DOMAIN_PHRASES = {
    "Maritime": [
        "automatic identification system",
        "ais data",
        "vessel tracking",
        "maritime incident",
        "ship tracking",
    ],
    "Telecom/5G": [
        "5g network slicing",
        "5g core",
        "open ran",
        "o-ran",
        "radio access network",
        "3gpp security",
    ],
    "Defence": [
        "electronic warfare",
        "radar swarm",
        "military communication",
        "air defence",
        "air defense",
    ],
    "Policy/Compliance": [
        "regulatory framework",
        "regulatory requirement",
        "policy gap",
        "compliance requirement",
        "legal requirement",
    ],
    "Research": [
        "research gap",
        "literature review",
        "state of the art",
        "research direction",
    ],
    "Enterprise Incident": [
        "security incident",
        "incident response",
        "data breach",
        "service outage",
        "root cause analysis",
    ],
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _find_matches(
    text: str,
    keywords: List[str],
) -> List[str]:
    matches = []

    for keyword in keywords:
        keyword = keyword.lower().strip()

        if not keyword:
            continue

        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"

        if re.search(pattern, text):
            matches.append(keyword)

    return matches

def _score_domain(
    text: str,
    domain: str,
) -> Tuple[float, List[str]]:
    keywords = DOMAIN_KEYWORDS.get(domain, [])
    matches = _find_matches(text, keywords)

    score = 0.0

    # Normal keyword matches
    score += len(matches)

    # Strong phrase matches receive additional weight.
    strong_phrases = STRONG_DOMAIN_PHRASES.get(domain, [])

    for phrase in strong_phrases:
        if phrase in text:
            score += 3.0

    return score, matches


def _score_intent(
    text: str,
    intent: str,
) -> Tuple[float, List[str]]:
    keywords = INTENT_KEYWORDS.get(intent, [])
    matches = _find_matches(text, keywords)

    score = float(len(matches))

    strong_intent_phrases = {
        "Incident Analysis": [
            "analyze the incident",
            "analyse the incident",
            "incident analysis",
            "event analysis",
            "sequence of events",
        ],

        "Threat Analysis": [
            "threat analysis",
            "threat assessment",
            "security threat",
            "cyber threat",
            "threat actor",
        ],

        "Root Cause Analysis": [
            "root cause",
            "root-cause",
            "root cause analysis",
            "underlying cause",
            "failure cause",
            "determine the cause",
            "why did this happen",
        ],

        "Compliance": [
            "regulatory framework cover",
            "regulatory framework",
            "does this meet",
            "does this satisfy",
            "applicable regulation",
            "legal requirement",
        ],

        "Policy Gap": [
            "regulatory gap",
            "policy gap",
            "establish a regulatory gap",
            "evidence establish a regulatory gap",
            "gap in regulation",
            "gap in policy",
        ],

        "Research Gap": [
            "research gap",
            "literature gap",
            "knowledge gap",
            "open research problem",
            "future research",
        ],

        "Evidence Assessment": [
            "assess the evidence",
            "evaluate the evidence",
            "supporting evidence",
            "contradicting evidence",
            "counter evidence",
            "is there evidence",
        ],
    }

    for phrase in strong_intent_phrases.get(intent, []):
        if phrase in text:
            score += 3.0

    return score, matches

def _confidence(
    winning_score: float,
    second_score: float,
    total_score: float,
) -> float:
    if winning_score <= 0:
        return 0.30

    if total_score <= 0:
        return 0.30

    dominance = winning_score / total_score

    margin = 0.0

    if winning_score > 0:
        margin = (winning_score - second_score) / winning_score

    confidence = (
        0.60 * dominance
        + 0.40 * max(0.0, margin)
    )

    return max(0.30, min(0.99, confidence))


def classify_domain(text: str) -> Tuple[str, float, Dict[str, List[str]]]:
    normalized = _normalize(text)

    scores = {}
    matches = {}

    for domain in DOMAIN_KEYWORDS:
        score, domain_matches = _score_domain(
            normalized,
            domain,
        )

        scores[domain] = score
        matches[domain] = domain_matches

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    winning_domain, winning_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    # No domain evidence.
    if winning_score <= 0:
        return (
            "General Evidence",
            0.30,
            matches,
        )

    total_score = sum(scores.values())

    confidence = _confidence(
        winning_score,
        second_score,
        total_score,
    )

    return (
        winning_domain,
        confidence,
        matches,
    )


def classify_intent(text: str) -> Tuple[str, float, Dict[str, List[str]]]:
    normalized = _normalize(text)

    scores = {}
    matches = {}

    for intent in INTENTS:
        if intent == "General Analysis":
            continue

        score, intent_matches = _score_intent(
            normalized,
            intent,
        )

        scores[intent] = score
        matches[intent] = intent_matches

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not ranked or ranked[0][1] <= 0:
        return (
            "General Analysis",
            0.30,
            matches,
        )

    winning_intent, winning_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    total_score = sum(scores.values())

    confidence = _confidence(
        winning_score,
        second_score,
        total_score,
    )

    return (
        winning_intent,
        confidence,
        matches,
    )


def _secondary_domains(
    domain: str,
    matches: Dict[str, List[str]],
) -> List[str]:
    ranked = []

    for candidate, candidate_matches in matches.items():
        if candidate == domain:
            continue

        if candidate_matches:
            ranked.append(
                (
                    candidate,
                    len(candidate_matches),
                )
            )

    ranked.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        candidate
        for candidate, _ in ranked[:2]
    ]


def classify_query(query: str) -> QueryClassification:
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    if not query.strip():
        raise ValueError("query cannot be empty")

    domain, domain_confidence, domain_matches = classify_domain(query)

    intent, intent_confidence, intent_matches = classify_intent(query)

    profile = get_profile(domain)

    secondary_domains = _secondary_domains(
        domain,
        domain_matches,
    )

    return QueryClassification(
        query=query,
        domain=domain,
        domain_confidence=domain_confidence,
        intent=intent,
        intent_confidence=intent_confidence,
        secondary_domains=secondary_domains,
        retrieval_strategy=profile["retrieval_strategy"],
        agents=profile["agents"],
        response_profile=profile["response_profile"],
        matched_domain_terms={
            key: value
            for key, value in domain_matches.items()
            if value
        },
        matched_intent_terms={
            key: value
            for key, value in intent_matches.items()
            if value
        },
    )


def classify(query: str) -> dict:
    """
    Public API for the rest of HackGrid.

    Returns a JSON-serializable dictionary.
    """
    return classify_query(query).to_dict()