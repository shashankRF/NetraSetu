import json

from Backend.query_analysis.domain_classifier import classify


TEST_CASES = [
    {
        "query": "Analyze AIS data to determine whether a vessel behaved anomalously.",
        "domain": "Maritime",
        "intent": "Incident Analysis",
    },
    {
        "query": "What are the security requirements for 5G network slicing in India?",
        "domain": "Telecom/5G",
        "intent": "Compliance",
    },
    {
        "query": "Analyze the threat posed by an attack against an O-RAN deployment.",
        "domain": "Telecom/5G",
        "intent": "Threat Analysis",
    },
    {
        "query": "Determine the root cause of a 5G core network failure.",
        "domain": "Telecom/5G",
        "intent": "Root Cause Analysis",
    },
    {
        "query": "Does the Indian regulatory framework cover AI-based telecom network orchestration?",
        "domain": "Policy/Compliance",
        "intent": "Compliance",
    },
    {
        "query": "Does the evidence establish a regulatory gap for AI-based network orchestration?",
        "domain": "Policy/Compliance",
        "intent": "Policy Gap",
    },
    {
        "query": "What are the major research gaps in AI-native 6G networks?",
        "domain": "Research",
        "intent": "Research Gap",
    },
    {
        "query": "Assess the evidence supporting the claim that this system is vulnerable.",
        "domain": "General Evidence",
        "intent": "Evidence Assessment",
    },
    {
        "query": "Analyze the root cause of the enterprise ransomware incident.",
        "domain": "Enterprise Incident",
        "intent": "Root Cause Analysis",
    },
    {
        "query": "Assess the threat from a military radar surveillance system.",
        "domain": "Defence",
        "intent": "Threat Analysis",
    },
]


def test_domain_and_intent_classification():
    failures = []

    for case in TEST_CASES:
        result = classify(case["query"])

        if result["domain"] != case["domain"]:
            failures.append(
                {
                    "query": case["query"],
                    "field": "domain",
                    "expected": case["domain"],
                    "actual": result["domain"],
                }
            )

        if result["intent"] != case["intent"]:
            failures.append(
                {
                    "query": case["query"],
                    "field": "intent",
                    "expected": case["intent"],
                    "actual": result["intent"],
                }
            )

        if not 0.0 <= result["domain_confidence"] <= 1.0:
            failures.append(
                {
                    "query": case["query"],
                    "field": "domain_confidence",
                    "actual": result["domain_confidence"],
                }
            )

        if not 0.0 <= result["intent_confidence"] <= 1.0:
            failures.append(
                {
                    "query": case["query"],
                    "field": "intent_confidence",
                    "actual": result["intent_confidence"],
                }
            )

        if not result["retrieval_strategy"]:
            failures.append(
                {
                    "query": case["query"],
                    "field": "retrieval_strategy",
                }
            )

        if not result["agents"]:
            failures.append(
                {
                    "query": case["query"],
                    "field": "agents",
                }
            )

        if not result["response_profile"]:
            failures.append(
                {
                    "query": case["query"],
                    "field": "response_profile",
                }
            )

    assert not failures, json.dumps(
        failures,
        indent=2,
    )


def test_unknown_query_falls_back_safely():
    result = classify(
        "Explain the historical development of information systems."
    )

    assert result["domain"] == "General Evidence"
    assert result["intent"] == "General Analysis"


def test_empty_query_rejected():
    try:
        classify("")
        assert False, "Empty query should raise ValueError"
    except ValueError:
        pass