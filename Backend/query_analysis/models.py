from dataclasses import dataclass, field
from typing import List, Dict, Any


DOMAINS = [
    "Maritime",
    "Telecom/5G",
    "Defence",
    "Policy/Compliance",
    "Research",
    "Enterprise Incident",
    "General Evidence",
]


INTENTS = [
    "Incident Analysis",
    "Threat Analysis",
    "Root Cause Analysis",
    "Compliance",
    "Policy Gap",
    "Research Gap",
    "Evidence Assessment",
    "General Analysis",
]


@dataclass
class QueryClassification:
    query: str

    domain: str
    domain_confidence: float

    intent: str
    intent_confidence: float

    secondary_domains: List[str] = field(default_factory=list)

    retrieval_strategy: str = ""
    agents: List[str] = field(default_factory=list)
    response_profile: str = ""

    matched_domain_terms: Dict[str, List[str]] = field(default_factory=dict)
    matched_intent_terms: Dict[str, List[str]] = field(default_factory=dict)

    classifier_version: str = "domain-intent-classifier-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "domain": self.domain,
            "domain_confidence": round(self.domain_confidence, 4),
            "intent": self.intent,
            "intent_confidence": round(self.intent_confidence, 4),
            "secondary_domains": self.secondary_domains,
            "retrieval_strategy": self.retrieval_strategy,
            "agents": self.agents,
            "response_profile": self.response_profile,
            "matched_domain_terms": self.matched_domain_terms,
            "matched_intent_terms": self.matched_intent_terms,
            "classifier_version": self.classifier_version,
        }