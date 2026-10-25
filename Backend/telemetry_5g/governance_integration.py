"""Evidence-aware adapter from synthetic simulator rows to the real risk engine.

This adapter deliberately keeps telemetry observations separate from legal or
operational evidence. Retrieved quotes are verified against their local PDF,
but their applicability to an incident is never inferred by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from Backend.evidence_engine.clause_verifier import verify_claim_evidence
from Backend.evidence_engine.rag_adapter import adapt_retrieval_results
from Backend.risk_engine import (
    AIAnalysis,
    AuthorityRequirement,
    DecisionContext,
    DecisionImpact,
    EvidenceAssessment,
    EvidenceQuality,
    EvidenceStatus,
    RiskEngine,
)


@dataclass(frozen=True)
class SimulationRiskInput:
    """Typed record preserving simulator input and observations for assessment."""

    run_id: str
    scenario_id: Optional[str]
    profile: str
    failure_types: List[str]
    seed: int
    samples: int
    simulator_version: str
    metrics: Dict[str, Any]
    simulator_provenance: Dict[str, Any]


def retrieve_and_verify_simulation_sources(
    *,
    query: str,
    jurisdiction: Optional[str],
    limit: int = 5,
) -> Dict[str, Any]:
    """Use the existing jurisdiction-aware BGE-M3/FAISS retrieval and PDF verifier."""
    if not jurisdiction:
        return {
            "status": "EVIDENCE_PENDING",
            "jurisdiction": None,
            "query": query,
            "sources": [],
            "limitations": ["Jurisdiction was not supplied; retrieval was not run."],
        }
    try:
        from rag.retrieval import retrieve

        retrieved = retrieve(query, k=limit, jurisdiction=jurisdiction)
        adapted = adapt_retrieval_results(retrieved)
        sources: List[Dict[str, Any]] = []
        for evidence in adapted:
            verification = verify_claim_evidence(
                claim=str(evidence.get("text") or ""),
                evidence_records=[evidence],
                claim_id=str(evidence.get("evidence_id") or "SIM-EVIDENCE"),
            )
            citation = verification.to_dict() if hasattr(verification, "to_dict") else {
                name: getattr(verification, name)
                for name in verification.__dataclass_fields__
            }
            citation["applicability"] = "NOT_ASSESSED"
            citation["retrieval_score"] = (retrieved[len(sources)].get("score")
                                           if len(sources) < len(retrieved) else None)
            citation["evidence_id"] = evidence.get("evidence_id")
            sources.append(citation)
        return {
            "status": "RETRIEVED" if sources else "NO_RESULTS",
            "jurisdiction": jurisdiction,
            "query": query,
            "sources": sources,
            "limitations": (["Retrieved sources are not an assessment of requirement applicability or compliance."]
                            if sources else ["No source passages were retrieved."]),
        }
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "jurisdiction": jurisdiction,
            "query": query,
            "sources": [],
            "limitations": [f"Retrieval or PDF verification failed ({type(exc).__name__})."],
        }


def _risk_payload(result: Any, source_assessment: Dict[str, Any],
                  risk_input: SimulationRiskInput,
                  context_data: Dict[str, Any]) -> Dict[str, Any]:
    blocking = list(result.blocking_conditions)
    decision = "BLOCKED" if blocking else (
        "REVIEW_REQUIRED" if result.human_review_required else "NOT_EVALUATED"
    )
    return {
        "engine": "Backend.risk_engine.RiskEngine",
        "risk_level": result.risk_level.value,
        "risk_score": result.risk_score,
        "escalation_level": result.escalation_level.value,
        "mandatory_review": result.mandatory_review,
        "human_review_required": result.human_review_required,
        "blocking_conditions": blocking,
        "reasons": list(result.reasons),
        "recommended_action": result.recommended_action,
        "evidence_quality": result.evidence_quality.value,
        "evidence_status": result.evidence_status.value,
        "decision_status": decision,
        "risk_engine_input": {
            "decision_context": context_data,
            "evidence_assessment": {
                "quality": "INSUFFICIENT",
                "supporting_count": 0,
                "contradicting_count": 0,
                "primary_source_count": 0,
                "official_source_count": 0,
                "source_diversity": 0,
                "evidence_status": "INSUFFICIENT",
                "missing_evidence": [
                    "Applicability of retrieved guidance to these synthetic measurements has not been established.",
                    "No independently verified operational requirement or incident-specific consequence assessment is available.",
                ],
            },
            "ai_analysis": {
                "status": "NOT_USED",
                "confidence": 0.0,
                "factual_claims": 0,
                "supported_claims": 0,
                "unsupported_claims": 0,
                "hallucination_risk": 0.0,
                "novel_situation": False,
            },
            "simulation_observations": {
                "run_id": risk_input.run_id,
                "scenario_id": risk_input.scenario_id,
                "profile": risk_input.profile,
                "failure_types": risk_input.failure_types,
                "seed": risk_input.seed,
                "samples": risk_input.samples,
                "simulator_version": risk_input.simulator_version,
                "metrics": risk_input.metrics,
                "provenance": risk_input.simulator_provenance,
                "mapping_note": "Telemetry metrics remain typed synthetic observations; DecisionContext has no metric fields, so no metric was silently mapped to consequence_score or a legal finding.",
            },
        },
        "evidence_status_detail": source_assessment.get("status", "EVIDENCE_PENDING"),
        "review_status": decision,
    }


def assess_simulation_row(
    risk_input: SimulationRiskInput,
    source_assessment: Dict[str, Any],
    *,
    decision_impact: str = "OPERATIONAL",
    consequence_score: int = 0,
    authority_requirement: str = "NONE",
    affects_public_safety: bool = False,
    affects_critical_infrastructure: bool = False,
) -> Dict[str, Any]:
    """Invoke the existing deterministic engine; keep absent evidence blocking."""
    context = DecisionContext(
        domain="Telecom/5G simulation",
        decision_impact=DecisionImpact(decision_impact),
        consequence_score=consequence_score,
        authority_requirement=AuthorityRequirement(authority_requirement),
        affects_public_safety=affects_public_safety,
        affects_critical_infrastructure=affects_critical_infrastructure,
        # This workflow does not propose legal interpretation or external actions.
        legal_or_regulatory_interpretation=False,
        external_action=False,
        production_change=False,
        sensitive_information=False,
    )
    evidence = EvidenceAssessment(
        quality=EvidenceQuality.INSUFFICIENT,
        supporting_count=0,
        contradicting_count=0,
        primary_source_count=0,
        official_source_count=0,
        source_diversity=0,
        evidence_status=EvidenceStatus.INSUFFICIENT,
        missing_evidence=[
            "Applicability of retrieved guidance to these synthetic measurements has not been established.",
            "No independently verified operational requirement or incident-specific consequence assessment is available.",
        ],
    )
    # There is no LLM in this simulator. Zero confidence is explicit and is
    # conservatively consumed by the existing risk formula, not fabricated.
    ai = AIAnalysis(confidence=0.0)
    assessment = RiskEngine().assess(context=context, evidence=evidence, ai=ai)
    context_data = {
        "domain": context.domain,
        "decision_impact": context.decision_impact.value,
        "consequence_score": context.consequence_score,
        "authority_requirement": context.authority_requirement.value,
        "affects_public_safety": context.affects_public_safety,
        "affects_critical_infrastructure": context.affects_critical_infrastructure,
        "legal_or_regulatory_interpretation": context.legal_or_regulatory_interpretation,
        "external_action": context.external_action,
        "production_change": context.production_change,
        "sensitive_information": context.sensitive_information,
        "input_origin": "explicit request values plus documented defaults; no metric-derived consequence score",
    }
    return _risk_payload(assessment, source_assessment, risk_input, context_data)
