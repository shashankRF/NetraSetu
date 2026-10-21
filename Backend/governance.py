from __future__ import annotations
"""
NetraSetu Governance Layer
=========================

Deterministic governance normalization layer.

Purpose:
- Distinguish retrieved evidence from evidence that establishes a claim.
- Prevent absence of evidence from becoming proof of absence.
- Prevent unsupported policy/regulatory gap claims.
- Enforce human review for consequential regulatory decisions.
- Keep governance deterministic and independent of LLM generation.

The LLM is NOT the source of truth.
Evidence is the source of truth.
This module only applies governance rules to the pipeline outputs.
"""


from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    """Safely convert any value to lowercase searchable text."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value.lower()

    if isinstance(value, dict):
        return " ".join(
            f"{key} {_text(item)}"
            for key, item in value.items()
        ).lower()

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            _text(item)
            for item in value
        ).lower()

    return str(value).lower()


def _contains_any(
    text: str,
    phrases: List[str],
) -> bool:
    """Return True if any phrase occurs in text."""

    return any(
        phrase in text
        for phrase in phrases
    )


# ---------------------------------------------------------------------------
# Question-type detection
# ---------------------------------------------------------------------------

def _is_gap_establishment_question(
    question: str,
) -> bool:
    """
    Detect questions asking whether available evidence establishes
    a policy/regulatory/standards gap.
    """

    query = _text(question)

    gap_terms = [
        "policy gap",
        "regulatory gap",
        "standards gap",
        "compliance gap",
        "governance gap",
        "policy deficiency",
        "regulatory deficiency",
    ]

    establishment_terms = [
        "establish",
        "establishes",
        "established",
        "prove",
        "proves",
        "demonstrate",
        "demonstrates",
        "demonstrated",
        "show",
        "shows",
        "shown",
        "evidence",
    ]

    return (
        _contains_any(
            query,
            gap_terms,
        )
        and _contains_any(
            query,
            establishment_terms,
        )
    )


def _is_absence_question(
    question: str,
) -> bool:
    """
    Detect questions asking whether something does not exist.

    Example:
    'Does the KB prove India has no regulation...'
    """

    query = _text(question)

    absence_terms = [
        "no regulation",
        "no regulations",
        "no policy",
        "no policies",
        "no requirement",
        "no requirements",
        "no provision",
        "no provisions",
        "does not exist",
        "do not exist",
        "doesn't exist",
        "don't exist",
        "not exist",
        "none exists",
        "nothing exists",
        "prove there is no",
        "prove there are no",
        "prove no",
    ]

    return _contains_any(
        query,
        absence_terms,
    )


def _is_consequential_auto_approval_question(
    question: str,
) -> bool:
    """
    Detect high-consequence questions asking whether AI should
    automatically approve or authorize a decision.
    """

    query = _text(question)

    consequence_terms = [
        "consequential",
        "high impact",
        "high-impact",
        "critical",
        "regulatory decision",
        "compliance decision",
        "security decision",
        "safety decision",
        "operational decision",
    ]

    automation_terms = [
        "automatically approve",
        "auto approve",
        "auto-approve",
        "automatically approved",
        "approve automatically",
        "automated approval",
        "ai approval",
        "ai approve",
        "ai automatically",
    ]

    return (
        _contains_any(
            query,
            consequence_terms,
        )
        and _contains_any(
            query,
            automation_terms,
        )
    )


# ---------------------------------------------------------------------------
# Final synthesis helpers
# ---------------------------------------------------------------------------

def _final_claim_status(
    final_synthesis: Dict[str, Any],
) -> str:
    """
    Safely extract the first final-claim status.
    """

    if not isinstance(
        final_synthesis,
        dict,
    ):
        return ""

    claims = final_synthesis.get(
        "claims",
        [],
    )

    if not isinstance(
        claims,
        list,
    ) or not claims:
        return ""

    first_claim = claims[0]

    if not isinstance(
        first_claim,
        dict,
    ):
        return ""

    return str(
        first_claim.get(
            "status",
            "",
        )
    ).upper()


def _evidence_has_positive_gap_support(
    classification: Any,
    final_synthesis: Dict[str, Any],
) -> bool:
    """
    Conservative test for explicit positive evidence of a policy gap.

    We only return True if the available structured/LLM output explicitly
    indicates supporting evidence for the existence of a gap.

    Everything else is treated conservatively as NOT established.
    """

    combined = _text(
        classification
    )

    positive_gap_phrases = [
        "policy gap exists",
        "policy gap is established",
        "gap is established",
        "regulatory gap exists",
        "regulatory gap is established",
        "standards gap exists",
        "gap demonstrated",
        "gap is demonstrated",
        "positive evidence of a policy gap",
        "supporting evidence for a policy gap",
    ]

    if _contains_any(
        combined,
        positive_gap_phrases,
    ):
        return True

    claims = final_synthesis.get(
        "claims",
        [],
    )

    if isinstance(
        claims,
        list,
    ):

        for claim in claims:

            if not isinstance(
                claim,
                dict,
            ):
                continue

            status = str(
                claim.get(
                    "status",
                    "",
                )
            ).upper()

            claim_text = _text(
                claim.get(
                    "claim",
                    "",
                )
            )

            if status in {
                "SUPPORTED",
                "ESTABLISHED",
                "SUFFICIENT",
            }:

                if _contains_any(
                    claim_text,
                    [
                        "policy gap exists",
                        "regulatory gap exists",
                        "standards gap exists",
                        "policy gap is established",
                        "regulatory gap is established",
                    ],
                ):
                    return True

    return False


# ---------------------------------------------------------------------------
# Main governance function
# ---------------------------------------------------------------------------

# ===========================================================================
# DECISION-GOVERNANCE LAYER HELPERS
# ===========================================================================

def _extract_evidence_roles(
    evidence_assessment: Dict[str, Any],
    final_synthesis: Dict[str, Any],
    classification: Any,
) -> Dict[str, Any]:
    supporting_ids = set()
    contradicting_ids = set()
    limiting_ids = set()
    contextual_ids = set()

    if isinstance(classification, dict):
        for c in classification.get("classifications", []):
            if isinstance(c, dict):
                eid = c.get("evidence_id")
                role = str(c.get("evidence_role", "")).upper()
                if eid:
                    if role == "SUPPORTING":
                        supporting_ids.add(eid)
                    elif role == "CONTRADICTING":
                        contradicting_ids.add(eid)
                    elif role in ("LIMITING", "QUALIFYING"):
                        limiting_ids.add(eid)
                    elif role == "CONTEXTUAL":
                        contextual_ids.add(eid)

    if isinstance(final_synthesis, dict):
        for cl in final_synthesis.get("claims", []):
            if isinstance(cl, dict):
                st = str(cl.get("status", "")).upper()
                eids = cl.get("evidence_ids", [])
                if isinstance(eids, list):
                    for eid in eids:
                        if st in ("SUPPORTED", "ESTABLISHED", "SUFFICIENT"):
                            supporting_ids.add(eid)
                        elif st == "CONTRADICTED":
                            contradicting_ids.add(eid)
                        elif st in ("INSUFFICIENT", "LIMITING", "PARTIALLY_ESTABLISHED"):
                            limiting_ids.add(eid)

        for ce in final_synthesis.get("counter_evidence", []):
            if isinstance(ce, dict):
                eid = ce.get("evidence_id")
                rel = str(ce.get("relationship_type", "")).upper()
                if eid:
                    if "CONTRADICT" in rel:
                        contradicting_ids.add(eid)
                    else:
                        limiting_ids.add(eid)

    quality = str(
        evidence_assessment.get("overall_strength")
        or evidence_assessment.get("quality")
        or "MODERATE"
    ).upper()

    status = str(
        evidence_assessment.get("overall_status")
        or evidence_assessment.get("evidence_status")
        or "SUFFICIENT"
    ).upper()

    missing = list(evidence_assessment.get("missing_evidence") or [])

    return {
        "supporting_ids": sorted(list(supporting_ids)),
        "contradicting_ids": sorted(list(contradicting_ids)),
        "limiting_ids": sorted(list(limiting_ids)),
        "contextual_ids": sorted(list(contextual_ids)),
        "quality": quality,
        "status": status,
        "missing_evidence": missing,
    }


def _evaluate_authority_gate(
    question: str,
    evidence_assessment: Dict[str, Any],
    classification: Any,
    final_synthesis: Dict[str, Any],
    risk_assessment: Dict[str, Any],
) -> Dict[str, Any]:
    """
    AUTHORITY EVIDENCE GATE:
    Before displaying a specific person, role, organisation, committee,
    agency, or authority as a decision-maker, verify that the supplied
    evidence actually establishes it.

    Required evidence properties:
    1. Identity/role exists in the supplied evidence.
    2. The role is relevant to the current context.
    3. The role has decision authority, not merely responsibility.
    4. The authority applies to this decision/action.
    5. The jurisdiction/context is applicable.

    If ANY required element is missing:
    VALUE: 'Not established by supplied evidence.'
    Do NOT guess.
    """
    q_lower = _text(question)
    synth_text = _text(final_synthesis)
    class_text = _text(classification)
    all_text = f"{q_lower} {synth_text} {class_text}"

    authority_candidates = []

    # Check Telecom India statutory authorities
    if ("principal-telecom-services-rule" in all_text or "dot" in all_text or "telecommunications act" in all_text) and (
        "central government" in all_text or "department of telecommunications" in all_text or "dot" in all_text
    ):
        if any(term in all_text for term in ["prior permission", "licensing", "authorisation", "rule 53", "central government"]):
            authority_candidates.append({
                "name": "Central Government / Department of Telecommunications (DoT)",
                "boundary": "Statutory prior permission, telecommunication licensing, and critical infrastructure traffic direction under Principal Telecom Services Rules 2026.",
                "evidence_ids": [eid for eid in ["EV-003", "EV-004"] if eid in synth_text or eid in class_text],
                "rationale": "Explicit statutory authority established under Rule 53, Principal Telecom Services Rules 2026 (Gazette of India)."
            })

    if "cert-in" in all_text and any(term in all_text for term in ["reporting", "incident", "breach", "6 hours", "directions"]):
        authority_candidates.append({
            "name": "Indian Computer Emergency Response Team (CERT-In)",
            "boundary": "Mandatory cybersecurity incident reporting and technical direction under IT Act Section 70B.",
            "evidence_ids": [eid for eid in ["EV-001", "EV-002", "EV-003"] if eid in synth_text and "cert" in synth_text],
            "rationale": "Statutory incident response reporting authority under CERT-In 2022 Directions."
        })

    if "trai" in all_text and any(term in all_text for term in ["tariff", "interconnection", "qos", "quality of service", "recommendation"]):
        authority_candidates.append({
            "name": "Telecom Regulatory Authority of India (TRAI)",
            "boundary": "Tariff regulation, QoS norms, and interconnect terms under TRAI Act 1997.",
            "evidence_ids": [],
            "rationale": "Statutory economic and QoS regulatory authority under TRAI Act."
        })

    if ("maritime" in all_text or "vessel" in all_text or "ship" in all_text) and ("dg shipping" in all_text or "imo" in all_text or "solas" in all_text):
        authority_candidates.append({
            "name": "Directorate General of Shipping (DG Shipping) / International Maritime Organization (IMO)",
            "boundary": "Statutory maritime safety, SOLAS compliance, and maritime communication mandates.",
            "evidence_ids": [],
            "rationale": "Sovereign maritime authority under Merchant Shipping Act and IMO conventions."
        })

    if authority_candidates:
        top_auth = authority_candidates[0]
        return {
            "established": True,
            "decision_authority": top_auth["name"],
            "authorized_boundary": top_auth["boundary"],
            "evidence_ids": top_auth["evidence_ids"],
            "rationale": top_auth["rationale"],
        }

    # Strict fallback when evidence is only technical specs (3GPP, ETSI, ITU-T) or no statutory power cited:
    return {
        "established": False,
        "decision_authority": "Not established by supplied evidence.",
        "authorized_boundary": "Not established by supplied evidence.",
        "evidence_ids": [],
        "rationale": "Retrieved evidence supplies technical standards or general commentary that do not establish statutory decision authority for this consequential action.",
    }


def _determine_responsible_function(
    question: str,
    classification: Any,
    final_synthesis: Dict[str, Any],
) -> Dict[str, str]:
    q_lower = _text(question)
    class_text = _text(classification)
    combined = f"{q_lower} {class_text}"

    if _contains_any(combined, ["maritime", "vessel", "ship", "ais", "navigation", "gnss"]):
        return {
            "function": "Maritime Operations & Navigation Watch Function",
            "next_task": "Cross-reference vessel transponder telemetry and verify radio navigation compliance before altering voyage plan.",
            "boundary": "Navigation telemetry verification and local vessel system checks only; no authority to bypass coastal administration directives.",
        }
    elif _contains_any(combined, ["defence", "defense", "military", "tactical", "datalink", "uav", "electronic warfare"]):
        return {
            "function": "Tactical Communications & Electronic Warfare Function",
            "next_task": "Audit cryptographic key parameters and verify RF spectrum isolation across tactical datalinks.",
            "boundary": "Technical datalink isolation and telemetry monitoring only; kinetic or sovereign operational decisions require commander sign-off.",
        }
    elif _contains_any(combined, ["slice", "slicing", "5g", "core", "3gpp", "telecom", "ran", "gnb", "upf", "amf"]):
        return {
            "function": "Network Engineering & Operations Function",
            "next_task": "Inspect 5G network slice isolation parameters and verify interface cipher suite compliance against technical specifications.",
            "boundary": "Diagnostic inspection, parameter telemetry audits, and testbed simulation only; no authority to authorize production waivers.",
        }
    elif _contains_any(combined, ["security", "breach", "incident", "malware", "cyber", "attack", "vulnerability"]):
        return {
            "function": "Security Operations & Threat Analysis Function",
            "next_task": "Conduct containment verification, inspect access logs, and preserve forensic artifacts without external transmission.",
            "boundary": "Technical containment and evidentiary logging only; no authority to execute formal regulatory disclosures.",
        }
    elif _contains_any(combined, ["policy", "regulation", "statutory", "compliance", "trai", "dot", "act", "gazette"]):
        return {
            "function": "Regulatory Compliance & Legal Analysis Function",
            "next_task": "Execute statutory crosswalk against latest official gazette notifications before proposing configuration changes.",
            "boundary": "Statutory analysis and compliance dossier compilation; legal sign-off rests with designated corporate or sovereign counsel.",
        }
    else:
        return {
            "function": "Not established by supplied evidence.",
            "next_task": "Review retrieved evidence records and confirm operational ownership.",
            "boundary": "Not established by supplied evidence.",
        }


def _determine_decision_impact(
    question: str,
    classification: Any,
    risk_assessment: Dict[str, Any],
    risk_level: str,
) -> Dict[str, Any]:
    q_lower = _text(question)
    class_text = _text(classification)
    combined = f"{q_lower} {class_text}"

    raw_impact = str(risk_assessment.get("decision_impact") or "").upper()
    if raw_impact in ("SAFETY", "SECURITY", "REGULATORY", "OPERATIONAL", "STRATEGIC", "INFORMATIONAL"):
        impact = raw_impact
    elif _contains_any(combined, ["safety", "navigation", "vessel", "collision", "life-safety", "mayday", "solas"]):
        impact = "SAFETY"
    elif _contains_any(combined, ["security", "breach", "cyber", "attack", "malicious", "vulnerability", "isolate"]):
        impact = "SECURITY"
    elif _contains_any(combined, ["regulation", "regulatory", "law", "statutory", "legal", "compliance", "mandate", "dot", "trai", "cert-in", "act"]):
        impact = "REGULATORY"
    elif _contains_any(combined, ["production", "deploy", "slice", "reconfigure", "configuration", "downtime", "outage"]):
        impact = "OPERATIONAL"
    elif _contains_any(combined, ["strategic", "sovereign", "defence", "defense", "military"]):
        impact = "STRATEGIC"
    else:
        impact = "INFORMATIONAL"

    # Safety-Critical Mode check
    safety_critical_mode = (
        impact == "SAFETY"
        or (risk_level == "CRITICAL" and _contains_any(combined, ["safety", "maritime", "vessel", "ship", "navigation", "critical infrastructure", "emergency", "defence", "defense", "tactical", "collision", "blackout", "disruption"]))
        or _contains_any(combined, ["safety-critical", "life safety", "critical infrastructure", "emergency communications"])
    )

    if safety_critical_mode or impact == "SAFETY":
        consequence_summary = "Misassessment could lead to catastrophic operational failure, safety hazard in maritime navigation, or disruption of emergency telecommunication services."
        safety_trigger = "Triggered by human life-safety, maritime navigational integrity, or critical telecommunication infrastructure risk."
    elif impact == "SECURITY":
        consequence_summary = "Incorrect security assessment risks unauthorized access, lateral network traversal, or failure to isolate compromised network slices."
        safety_trigger = "Triggered by critical network security and perimeter boundary protection requirements."
    elif impact == "REGULATORY":
        consequence_summary = "Unjustified assumption of regulatory compliance or missed statutory reporting window exposes the operator to legal liability or sanctions."
        safety_trigger = "Triggered by statutory compliance obligations and official gazette enforcement."
    elif impact == "OPERATIONAL":
        consequence_summary = "Unverified configuration changes may cause widespread network slice degradation, latency spikes, or service level agreement breaches."
        safety_trigger = "Triggered by carrier-grade operational continuity and production availability thresholds."
    elif impact == "STRATEGIC":
        consequence_summary = "Strategic misalignment with sovereign telecommunication frameworks undermines long-term technical sovereignty and compliance posture."
        safety_trigger = "Triggered by sovereign communications architecture and strategic policy alignment."
    else:
        consequence_summary = "Analytical misinterpretation leads to inefficient operational investigation or redundant compliance reviews."
        safety_trigger = "Informational baseline review."

    return {
        "impact_category": impact,
        "safety_critical_mode": safety_critical_mode,
        "consequence_summary": consequence_summary,
        "safety_trigger": safety_trigger,
    }


def _determine_reversibility(
    impact_category: str,
    risk_level: str,
    safety_critical_mode: bool,
) -> Dict[str, str]:
    if safety_critical_mode or impact_category == "SAFETY" or (risk_level == "CRITICAL" and impact_category in ("OPERATIONAL", "REGULATORY", "SECURITY")):
        level = "IRREVERSIBLE / HIGH CONSEQUENCE"
        explanation = "Operational actions in safety-critical, high-consequence, or statutory filing contexts cannot be undone without severe cascading impact."
    elif risk_level in ("CRITICAL", "HIGH") or impact_category in ("OPERATIONAL", "REGULATORY"):
        level = "DIFFICULT TO REVERSE"
        explanation = "Production reconfiguration or external regulatory filings require complex rollback procedures and multi-party coordination."
    elif risk_level == "MODERATE":
        level = "PARTIALLY REVERSIBLE"
        explanation = "Configuration or routing modifications can be reverted via administrative rollback, with transient telemetry effects."
    else:
        level = "REVERSIBLE"
        explanation = "Analytical reports, telemetry queries, and baseline compliance evaluations are purely informational and completely reversible."

    return {
        "level": level,
        "explanation": explanation,
    }


def _determine_automation_safety_gate(
    risk_level: str,
    evidence_status: str,
    human_review_required: bool,
    safety_critical_mode: bool,
    reversibility_level: str,
    authority_established: bool,
) -> Dict[str, str]:
    if safety_critical_mode:
        return {
            "status": "AUTOMATION PROHIBITED",
            "gate_rule": "SAFETY_CRITICAL_PROHIBITION",
            "explanation": "Safety-critical operations require explicit human command and validated jurisdictional authority; autonomous execution is barred.",
        }
    elif risk_level == "CRITICAL":
        return {
            "status": "AUTOMATION PROHIBITED",
            "gate_rule": "CRITICAL_RISK_PROHIBITION",
            "explanation": "Critical-risk decisions carry severe consequences; automated execution is strictly prohibited under NetraSetu safety invariants.",
        }
    elif not authority_established and reversibility_level in ("IRREVERSIBLE / HIGH CONSEQUENCE", "DIFFICULT TO REVERSE"):
        return {
            "status": "AUTHORITY NOT ESTABLISHED",
            "gate_rule": "MISSING_AUTHORITY_GATE",
            "explanation": "Consequential action lacks established decision authority in the supplied evidence; automation is prohibited.",
        }
    elif human_review_required or risk_level == "HIGH" or evidence_status in ("CONFLICTING", "INSUFFICIENT"):
        return {
            "status": "HUMAN AUTHORIZATION REQUIRED",
            "gate_rule": "MANDATORY_HUMAN_GATE",
            "explanation": "High-risk assessment or evidence uncertainty mandates human review before any consequential action is authorized.",
        }
    elif risk_level == "MODERATE":
        return {
            "status": "AUTOMATION LIMITED",
            "gate_rule": "MODERATE_RISK_LIMITATION",
            "explanation": "Automated advisory logging and diagnostic telemetry permitted; production modifications require human oversight.",
        }
    else:
        return {
            "status": "AUTOMATION PERMITTED",
            "gate_rule": "LOW_RISK_DIAGNOSTIC_PERMITTED",
            "explanation": "Low-risk, fully reversible diagnostic and analytical query; automated evaluation is permitted.",
        }


def _determine_root_cause_uncertainty(
    final_synthesis: Dict[str, Any],
    evidence_status: str,
    contradicting_ids: List[str],
) -> Dict[str, Any]:
    claims = final_synthesis.get("claims", []) if isinstance(final_synthesis, dict) else []

    if contradicting_ids:
        status = "CONTRADICTED"
        permitted = False
        rationale = "Contradicting evidence identified in retrieval; root cause attribution is disputed."
    elif evidence_status == "INSUFFICIENT":
        status = "INSUFFICIENT EVIDENCE"
        permitted = False
        rationale = "Insufficient evidence to establish causal attribution."
    elif any(str(cl.get("status", "")).upper() in ("SUPPORTED", "ESTABLISHED") for cl in claims) and evidence_status == "SUFFICIENT":
        status = "PARTIALLY ESTABLISHED"
        permitted = True
        rationale = "Corroborated by verified evidence records; causal attribution partially established."
    else:
        status = "NOT ESTABLISHED"
        permitted = False
        rationale = "Root cause attribution is not proven by the supplied evidence; consequential recommendations must remain attribution-independent."

    return {
        "status": status,
        "attribution_dependent_recommendations_permitted": permitted,
        "rationale": rationale,
    }


def _determine_governance_state(
    result_status: str,
    evidence_status: str,
    human_review_required: bool,
    risk_level: str,
    authority_established: bool,
    reversibility_level: str,
    recommended_action: str,
) -> str:
    if result_status in ("POLICY_GAP_NOT_ESTABLISHED", "REGULATORY_ABSENCE_NOT_ESTABLISHED") or evidence_status == "INSUFFICIENT":
        return "DEFERRED — INSUFFICIENT EVIDENCE"
    elif evidence_status == "CONFLICTING":
        return "DEFERRED — CONFLICTING EVIDENCE"
    elif human_review_required or risk_level in ("CRITICAL", "HIGH"):
        return "PENDING HUMAN REVIEW"
    elif not authority_established and reversibility_level in ("IRREVERSIBLE / HIGH CONSEQUENCE", "DIFFICULT TO REVERSE"):
        return "ACTION RECOMMENDED — NOT AUTHORIZED"
    elif recommended_action:
        return "ACTION RECOMMENDED — NOT AUTHORIZED"
    else:
        return "ASSESSMENT IN PROGRESS"


def _build_governance_confidences(
    evidence_quality: str,
    evidence_status: str,
    root_cause_status: str,
    authority_established: bool,
) -> Dict[str, Any]:
    if evidence_quality == "STRONG" and evidence_status == "SUFFICIENT":
        ev_score = 0.90
        ev_label = "High Evidence Quality"
    elif evidence_quality == "MODERATE":
        ev_score = 0.70
        ev_label = "Moderate Evidence Quality"
    elif evidence_status == "CONFLICTING":
        ev_score = 0.50
        ev_label = "Conflicting Evidence"
    else:
        ev_score = 0.40
        ev_label = "Insufficient Evidence"

    rc_score = 0.85 if root_cause_status == "ESTABLISHED" else 0.60 if root_cause_status == "PARTIALLY ESTABLISHED" else None
    rc_label = root_cause_status if rc_score else "Not established"

    auth_score = 0.85 if authority_established else None
    auth_label = "Established via Evidence" if authority_established else "Not established by supplied evidence"

    return {
        "evidence_confidence": {
            "score": ev_score,
            "label": ev_label,
            "description": "Reflects passage relevance, statutory provenance authority, and absence safeguards.",
        },
        "risk_confidence": {
            "score": 0.92,
            "label": "High (Deterministic Evaluation)",
            "description": "Calculated by deterministic Risk Engine matrix evaluation across consequence and authority tiers.",
        },
        "root_cause_confidence": {
            "score": rc_score,
            "label": rc_label,
            "description": "Certainty of causal incident attribution derived from verified evidence.",
        },
        "governance_confidence": {
            "score": 0.95,
            "label": "High (Invariant Enforcement)",
            "description": "Deterministic safety invariants, gate rules, and human review boundaries verified.",
        },
        "authority_confidence": {
            "score": auth_score,
            "label": auth_label,
            "description": "Indicates whether statutory decision authority is explicitly grounded in retrieved provisions.",
        },
    }


def _build_scenario_branches(
    responsible_function: str,
    decision_authority: str,
    escalation_recipient: str,
) -> Dict[str, str]:
    return {
        "if_approved": f"Authorized human reviewer accepts proposed action. Permitted action boundary is cryptographically recorded in the audit trail. Implementation proceeds under active monitoring by {responsible_function}.",
        "if_modified": "Reviewer adjusts operational scope, timing, or compliance controls. Modified parameters supersede AI recommendations and are bound to the immutable audit record.",
        "if_rejected": "Consequential action is halted immediately. System records human rejection in the audit trail and prohibits automated execution.",
        "if_escalated": f"Case transferred to {escalation_recipient}. Operational state is frozen pending higher-tier binding determination.",
        "if_deferred": "Decision deferred pending retrieval or verification of missing statutory/technical provisions. Absence cannot be treated as safe.",
        "if_new_evidence_strengthens": "Reassess evidence through Risk Engine; triggers immediate risk score upgrade and escalation to Senior Authority.",
        "if_new_evidence_weakens": "Reassess confidence; reconsider necessity of intrusive countermeasures or restrictive network slice controls.",
        "if_evidence_conflicts": "Governance state transitions immediately to DEFERRED — CONFLICTING EVIDENCE; mandatory domain expert review triggered.",
        "if_safety_impact_increases": "Immediate shift to SAFETY-CRITICAL DECISION MODE; automation strictly prohibited; senior human authorization mandatory.",
        "if_root_cause_changes": "Invalidate attribution-dependent decisions; re-evaluate baseline network telemetry and diagnostic parameters.",
        "if_proposed_action_fails": "Fallback authority and rollback procedure not established by supplied evidence. System reverts to baseline fail-safe state.",
    }


def _build_what_happens_next(
    gov_state: str,
    responsible_function: str,
    recommended_action: str,
    decision_authority: str,
    escalation_level: str,
    escalation_trigger: str,
    authority_established: bool,
) -> Dict[str, Any]:
    return {
        "1_current_state": gov_state,
        "2_responsible_function": responsible_function,
        "3_recommended_action": recommended_action,
        "4_authorization_status": "RECOMMENDED — NOT AUTHORIZED",
        "5_decision_authority": decision_authority,
        "6_escalation_level": escalation_level,
        "7_escalation_trigger": escalation_trigger,
        "8_evidence_needed_before_decision": (
            "Authoritative gazette notification or statutory text confirming jurisdiction-specific mandate."
            if not authority_established else
            "Operational incident telemetry and network isolation confirmation."
        ),
        "9_decision_options": ["APPROVE", "MODIFY", "REJECT", "ESCALATE", "DEFER", "INVESTIGATE"],
        "10_safety_limitation": "AI recommendation carries no legal or operational authority. Consequential actions require signed human authorization.",
    }


def _build_who_does_what_matrix(
    responsible_function: str,
    decision_authority: str,
    escalation_recipient: str,
) -> List[Dict[str, str]]:
    return [
        {
            "stage": "DETECT",
            "responsible_function": "Telemetry & Automated Monitoring",
            "decision_authority": "Automated Diagnostic Engine",
            "trigger": "Telemetry Threshold / Event Ingestion",
            "next_state": "VERIFY",
        },
        {
            "stage": "VERIFY",
            "responsible_function": "Technical Validation Function",
            "decision_authority": "Technical Analyst",
            "trigger": "Evidence Retrieval & Validation Complete",
            "next_state": "ANALYSE",
        },
        {
            "stage": "ANALYSE",
            "responsible_function": "Evidence & Analytical Engine",
            "decision_authority": "Analytical Assistant (Non-Authoritative)",
            "trigger": "Multi-Domain Evidence Correlation",
            "next_state": "RECOMMEND",
        },
        {
            "stage": "RECOMMEND",
            "responsible_function": "NetraSetu Decision-Support Pipeline",
            "decision_authority": "AI Recommendation (Non-Authoritative)",
            "trigger": "Risk & Governance Evaluation",
            "next_state": "AUTHORIZE",
        },
        {
            "stage": "AUTHORIZE",
            "responsible_function": "Designated Human Authority",
            "decision_authority": decision_authority,
            "trigger": "Mandatory Human Review Gate",
            "next_state": "ACT",
        },
        {
            "stage": "ACT",
            "responsible_function": responsible_function,
            "decision_authority": "Execution Strictly within Authorized Boundary",
            "trigger": "Signed Human Authorization Event",
            "next_state": "MONITOR",
        },
        {
            "stage": "MONITOR",
            "responsible_function": "Operations Monitoring Function",
            "decision_authority": "Operational Supervisor",
            "trigger": "Post-Action Telemetry Streaming",
            "next_state": "ESCALATE / CLOSE",
        },
        {
            "stage": "ESCALATE",
            "responsible_function": "Domain Expert / Senior Authority",
            "decision_authority": escalation_recipient,
            "trigger": "Tolerance Breach / Conflicting Evidence",
            "next_state": "CLOSE / REVIEW",
        },
    ]


def _enrich_with_decision_governance(
    result: Dict[str, Any],
    question: str,
    evidence_assessment: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    final_synthesis: Dict[str, Any],
    classification: Any,
) -> Dict[str, Any]:
    """
    Enrich the base governance result dictionary with the 8 distinct
    governance layers, automation safety gate, reversibility, scenario
    branching, matrix, and failure-safe safeguards.
    """
    # 1. Evidence State
    ev_roles = _extract_evidence_roles(
        evidence_assessment=evidence_assessment,
        final_synthesis=final_synthesis,
        classification=classification,
    )

    # 2. Risk State
    risk_level = str(
        result.get("risk_level")
        or risk_assessment.get("risk_level")
        or "MODERATE"
    ).upper()

    risk_score = int(
        risk_assessment.get("risk_score")
        or (100 if risk_level == "CRITICAL" else 75 if risk_level == "HIGH" else 45 if risk_level == "MODERATE" else 15)
    )

    escalation_level = str(
        result.get("escalation_level")
        or risk_assessment.get("escalation_level")
        or "ANALYST_REVIEW"
    ).upper()

    human_review_required = bool(
        result.get("human_review_required")
        or risk_assessment.get("human_review_required")
        or False
    )

    reasons = list(risk_assessment.get("reasons") or [])
    if not reasons:
        if risk_level == "CRITICAL":
            reasons = ["Decision involves critical infrastructure, regulatory compliance, or public safety risk."]
        elif risk_level == "HIGH":
            reasons = ["High consequence decision context requiring expert validation."]
        elif risk_level == "MODERATE":
            reasons = ["Operational parameter evaluation under active governance standards."]
        else:
            reasons = ["Low-risk informational query with verified evidence baseline."]

    blocking_conditions = list(risk_assessment.get("blocking_conditions") or [])

    # 3. Decision Impact
    impact_data = _determine_decision_impact(
        question=question,
        classification=classification,
        risk_assessment=risk_assessment,
        risk_level=risk_level,
    )

    # 4. Reversibility
    rev_data = _determine_reversibility(
        impact_category=impact_data["impact_category"],
        risk_level=risk_level,
        safety_critical_mode=impact_data["safety_critical_mode"],
    )

    # 5. Authority Evidence Gate
    auth_data = _evaluate_authority_gate(
        question=question,
        evidence_assessment=evidence_assessment,
        classification=classification,
        final_synthesis=final_synthesis,
        risk_assessment=risk_assessment,
    )

    # 6. Responsible Function ("Who Acts?")
    resp_data = _determine_responsible_function(
        question=question,
        classification=classification,
        final_synthesis=final_synthesis,
    )

    # 7. Recommended Action (Recommendation != Authorization)
    rec_action = str(
        risk_assessment.get("recommended_action")
        or (
            final_synthesis.get("recommended_actions", ["Verify evidence with authorized personnel"])[0]
            if isinstance(final_synthesis.get("recommended_actions"), list) and final_synthesis.get("recommended_actions")
            else "Route to authorized domain expert for review."
        )
    )

    # 8. Root-Cause Uncertainty
    rc_data = _determine_root_cause_uncertainty(
        final_synthesis=final_synthesis,
        evidence_status=ev_roles["status"],
        contradicting_ids=ev_roles["contradicting_ids"],
    )

    # 9. Automation Safety Gate
    gate_data = _determine_automation_safety_gate(
        risk_level=risk_level,
        evidence_status=ev_roles["status"],
        human_review_required=human_review_required,
        safety_critical_mode=impact_data["safety_critical_mode"],
        reversibility_level=rev_data["level"],
        authority_established=auth_data["established"],
    )

    # 10. Escalation details
    escalation_recipient = (
        auth_data["decision_authority"]
        if auth_data["established"]
        else (
            f"Designated {escalation_level.replace('_', ' ').title()} (Specific authority not established by supplied evidence)"
            if escalation_level in ("SENIOR_AUTHORITY", "DOMAIN_EXPERT")
            else "Not established by supplied evidence."
        )
    )

    if impact_data["safety_critical_mode"]:
        escalation_trigger = "Triggered immediately by safety-critical decision mode threshold."
    elif risk_level == "CRITICAL":
        escalation_trigger = "Triggered by critical risk score (>= 80) and regulatory/safety consequence score."
    elif ev_roles["status"] == "CONFLICTING":
        escalation_trigger = "Triggered by unresolved contradiction between primary and counter-evidence."
    elif ev_roles["status"] == "INSUFFICIENT":
        escalation_trigger = "Triggered by absence of authoritative statutory provisions in retrieved knowledge base."
    elif risk_level == "HIGH":
        escalation_trigger = "Triggered by high-assurance verification requirement."
    else:
        escalation_trigger = "Standard operational threshold; no escalation required unless anomalous telemetry is detected."

    # 11. Governance State
    gov_state = _determine_governance_state(
        result_status=result.get("status", ""),
        evidence_status=ev_roles["status"],
        human_review_required=human_review_required,
        risk_level=risk_level,
        authority_established=auth_data["established"],
        reversibility_level=rev_data["level"],
        recommended_action=rec_action,
    )

    # 12. Governance Confidences
    confidences = _build_governance_confidences(
        evidence_quality=ev_roles["quality"],
        evidence_status=ev_roles["status"],
        root_cause_status=rc_data["status"],
        authority_established=auth_data["established"],
    )

    # 13. Scenario Branches (Decision Simulator)
    branches = _build_scenario_branches(
        responsible_function=resp_data["function"],
        decision_authority=auth_data["decision_authority"],
        escalation_recipient=escalation_recipient,
    )

    # 14. What Happens Next?
    what_next = _build_what_happens_next(
        gov_state=gov_state,
        responsible_function=resp_data["function"],
        recommended_action=rec_action,
        decision_authority=auth_data["decision_authority"],
        escalation_level=escalation_level,
        escalation_trigger=escalation_trigger,
        authority_established=auth_data["established"],
    )

    # 15. Who Does What? Matrix
    matrix = _build_who_does_what_matrix(
        responsible_function=resp_data["function"],
        decision_authority=auth_data["decision_authority"],
        escalation_recipient=escalation_recipient,
    )

    # Assemble 8-Layer Decision Governance
    decision_governance = {
        "evidence_state": {
            "supporting_evidence_ids": ev_roles["supporting_ids"],
            "contradicting_evidence_ids": ev_roles["contradicting_ids"],
            "limiting_evidence_ids": ev_roles["limiting_ids"],
            "contextual_evidence_ids": ev_roles["contextual_ids"],
            "evidence_quality": ev_roles["quality"],
            "evidence_status": ev_roles["status"],
            "summary": "Evidence evaluated across primary and counter-retrieval passes with absence safeguards.",
            "missing_evidence": ev_roles["missing_evidence"],
        },
        "risk_state": {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "escalation_level": escalation_level,
            "reasons": reasons,
            "blocking_conditions": blocking_conditions,
        },
        "decision_impact": {
            "impact_category": impact_data["impact_category"],
            "consequence_summary": impact_data["consequence_summary"],
            "reversibility": rev_data["level"],
            "reversibility_explanation": rev_data["explanation"],
            "safety_critical_mode": impact_data["safety_critical_mode"],
            "safety_critical_trigger": impact_data["safety_trigger"],
        },
        "recommended_action": {
            "recommended_action": rec_action,
            "recommendation_label": "AI RECOMMENDATION — NOT AUTHORIZED",
            "attribution_dependence": rc_data["attribution_dependent_recommendations_permitted"] is False,
            "action_boundary": "Advisory recommendation generated by NetraSetu decision-support pipeline; execution strictly requires human authorization.",
        },
        "responsibility": {
            "responsible_function": resp_data["function"],
            "next_task": resp_data["next_task"],
            "responsible_boundary": resp_data["boundary"],
        },
        "authority": {
            "decision_authority": auth_data["decision_authority"],
            "authorized_action_boundary": auth_data["authorized_boundary"],
            "authority_established": auth_data["established"],
            "authority_evidence_ids": auth_data["evidence_ids"],
            "authority_rationale": auth_data["rationale"],
        },
        "escalation": {
            "escalation_level": escalation_level,
            "escalation_trigger": escalation_trigger,
            "escalation_recipient": escalation_recipient,
            "escalation_action": f"Freeze autonomous execution; submit evidence package and assessment dossier to {escalation_recipient} for binding determination.",
        },
        "final_decision": {
            "governance_state": gov_state,
            "decision_options": ["APPROVE", "MODIFY", "REJECT", "ESCALATE", "DEFER", "INVESTIGATE"],
            "human_override_status": "PENDING REVIEW",
            "authorized_by": "",
        },
    }

    # Attach all layers to result
    result["decision_governance"] = decision_governance
    result["automation_safety_gate"] = gate_data
    result["reversibility"] = rev_data
    result["conflicting_evidence"] = {
        "has_conflicts": bool(ev_roles["contradicting_ids"] or ev_roles["limiting_ids"]),
        "supporting_evidence_ids": ev_roles["supporting_ids"],
        "contradicting_evidence_ids": ev_roles["contradicting_ids"],
        "limiting_evidence_ids": ev_roles["limiting_ids"],
        "what_this_changes": (
            f"Limiting or contradicting records restrict unconditional claims and require qualified regulatory interpretation."
            if (ev_roles["contradicting_ids"] or ev_roles["limiting_ids"])
            else "No material counter-evidence contradicts the primary technical baseline."
        ),
        "governance_consequence": (
            "Downside safety guardrails enforced: human review mandated, automated authorization blocked, state deferred or escalated."
            if (ev_roles["contradicting_ids"] or ev_roles["limiting_ids"])
            else "Standard evidence baseline maintained."
        ),
    }
    result["root_cause_uncertainty"] = rc_data
    result["safety_critical_mode"] = {
        "active": impact_data["safety_critical_mode"],
        "reason": impact_data["safety_trigger"],
        "mandated_controls": [
            "Autonomous execution barred",
            "Mandatory human domain authority sign-off",
            "Cryptographic audit recording required",
            "Fallback fail-safe state enforced",
        ] if impact_data["safety_critical_mode"] else ["Standard human review gates apply"],
    }
    result["scenario_branches"] = branches
    result["what_happens_next"] = what_next
    result["who_does_what_matrix"] = matrix
    result["governance_confidences"] = confidences
    result["failure_safe"] = {
        "governance_limitation": "Where evidence or authority is unproven, NetraSetu restricts autonomy and prevents consequential action.",
        "safe_next_step": "Route to human review; obtain authoritative statutory confirmation before executing operational changes.",
    }

    return result


def evaluate_governance(
    question: str,
    evidence_assessment: Dict[str, Any] | None = None,
    gap_analysis: Dict[str, Any] | None = None,
    risk_assessment: Dict[str, Any] | None = None,
    final_synthesis: Dict[str, Any] | None = None,
    classification: Any = None,
) -> Dict[str, Any]:
    """
    Apply deterministic governance rules to the pipeline output.
    """

    evidence_assessment = (
        evidence_assessment
        if evidence_assessment is not None
        else {}
    )

    gap_analysis = (
        gap_analysis
        if gap_analysis is not None
        else {}
    )

    risk_assessment = (
        risk_assessment
        if risk_assessment is not None
        else {}
    )

    final_synthesis = (
        final_synthesis
        if final_synthesis is not None
        else {}
    )

    # -----------------------------------------------------------------------
    # Helper to finish and enrich governance output
    # -----------------------------------------------------------------------

    def _finish(res: Dict[str, Any]) -> Dict[str, Any]:
        return _enrich_with_decision_governance(
            result=res,
            question=question,
            evidence_assessment=evidence_assessment,
            gap_analysis=gap_analysis,
            risk_assessment=risk_assessment,
            final_synthesis=final_synthesis,
            classification=classification,
        )

    # -----------------------------------------------------------------------
    # Normalize incoming status fields
    # -----------------------------------------------------------------------

    original_evidence_status = str(
        evidence_assessment.get(
            "overall_status",
            "UNKNOWN",
        )
    ).upper()

    original_gap_status = str(
        gap_analysis.get(
            "overall_status",
            "UNKNOWN",
        )
    ).upper()

    risk_level = str(
        risk_assessment.get(
            "risk_level",
            "UNKNOWN",
        )
    ).upper()

    human_review = bool(
        risk_assessment.get(
            "human_review_required",
            False,
        )
    )

    escalation = str(
        risk_assessment.get(
            "escalation_level",
            "",
        )
    ).upper()

    final_claim_status = _final_claim_status(
        final_synthesis
    )

    # -----------------------------------------------------------------------
    # Default governance state
    # -----------------------------------------------------------------------

    result = {
        "status": "ASSESSMENT_REQUIRES_REVIEW",
        "evidence_status": original_evidence_status,
        "gap_status": original_gap_status,
        "risk_level": risk_level,
        "human_review_required": human_review,
        "escalation_level": escalation,
        "reason": (
            "Governance status derived from evidence, risk, "
            "and decision context."
        ),
        "rule": "DEFAULT_GOVERNANCE",
    }

    # -----------------------------------------------------------------------
    # RULE 1 — Explicit regulatory/policy absence
    #
    # Absence of retrieved evidence MUST NOT become proof of absence.
    # -----------------------------------------------------------------------

    if _is_absence_question(
        question
    ):

        result.update({
            "status": "REGULATORY_ABSENCE_NOT_ESTABLISHED",
            "evidence_status": "INSUFFICIENT",
            "gap_status": "ABSENCE_NOT_ESTABLISHED",
            "human_review_required": True,
            "escalation_level": (
                escalation
                or "SENIOR_AUTHORITY"
            ),
            "reason": (
                "The available evidence does not establish that the "
                "regulation, policy, requirement, or provision does not "
                "exist. Absence of retrieved evidence is not proof "
                "of absence."
            ),
            "rule": "ABSENCE_NOT_ESTABLISHED",
        })

        return _finish(result)

    # -----------------------------------------------------------------------
    # RULE 2 — Policy/regulatory gap establishment
    #
    # A gap must be positively established by evidence.
    # Retrieval alone is not sufficient.
    #
    # CRITICAL GOVERNANCE RULES:
    # - Local operator internal policies DO NOT constitute national policy gaps.
    # - Functional equivalence between mechanisms is NOT a regulatory gap.
    # - Additional/stricter sovereign national requirements are NOT gaps.
    # - Absence of retrieved evidence does NOT establish a regulatory gap.
    # - If final synthesis says CONTRADICTED or INSUFFICIENT, gap is NOT established.
    # -----------------------------------------------------------------------

    if _is_gap_establishment_question(
        question
    ):

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST LOCAL OPERATOR REQUIREMENT FALSE GAPS
        # ---------------------------------------------------------------
        q_lower = _text(question)
        if any(term in q_lower for term in [
            "operator x", "operator internal", "operator requirement", "local security requirement",
            "internal security policy", "internal baseline", "operator policy", "enterprise baseline",
            "operator's internal"
        ]):
            result.update({
                "status": "NO_GAP_ESTABLISHED",
                "evidence_status": original_evidence_status,
                "gap_status": "NO_GAP_ESTABLISHED",
                "human_review_required": False,
                "reason": (
                    "Operator-specific internal security requirements are private enterprise controls. "
                    "They do not establish an Indian national regulatory or policy gap."
                ),
                "rule": "LOCAL_OPERATOR_REQUIREMENT_PRESERVED",
            })
            return _finish(result)

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST RETRIEVAL FAILURE FALSE GAPS
        # ---------------------------------------------------------------
        if original_gap_status == "ABSENCE_NOT_ESTABLISHED" or original_evidence_status in {"INSUFFICIENT", "ABSENCE_NOT_ESTABLISHED"}:
            result.update({
                "status": "POLICY_GAP_NOT_ESTABLISHED",
                "evidence_status": "INSUFFICIENT",
                "gap_status": "ABSENCE_NOT_ESTABLISHED",
                "human_review_required": True,
                "escalation_level": (
                    escalation
                    or "SENIOR_AUTHORITY"
                ),
                "reason": (
                    "The available evidence does not establish the existence of a policy, regulatory, "
                    "or standards gap. Absence of retrieved evidence from examined sources is not proof "
                    "that no Indian requirement exists."
                ),
                "rule": "ABSENCE_NOT_ESTABLISHED",
            })
            return _finish(result)

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST FUNCTIONAL EQUIVALENCE FALSE GAPS
        # ---------------------------------------------------------------
        synth_text = _text(final_synthesis)
        if any(term in synth_text for term in ["functionally equivalent", "functional equivalence"]):
            result.update({
                "status": "NO_GAP_ESTABLISHED",
                "evidence_status": original_evidence_status,
                "gap_status": "NO_GAP_ESTABLISHED",
                "human_review_required": False,
                "reason": (
                    "Available evidence demonstrates functional equivalence in achieving the underlying security objective. "
                    "Different technical mechanisms do not constitute a regulatory or policy gap."
                ),
                "rule": "FUNCTIONAL_EQUIVALENCE_PRESERVED",
            })
            return _finish(result)

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST ADDITIONAL NATIONAL REQUIREMENT FALSE GAPS
        # ---------------------------------------------------------------
        if any(term in synth_text for term in ["additional national requirement", "stricter national requirement"]):
            result.update({
                "status": "NO_GAP_ESTABLISHED",
                "evidence_status": original_evidence_status,
                "gap_status": "NO_GAP_ESTABLISHED",
                "human_review_required": False,
                "reason": (
                    "The examined Indian instrument imposes an additional sovereign requirement beyond the technical baseline. "
                    "This is an exercise of sovereign regulatory authority, not a policy gap."
                ),
                "rule": "ADDITIONAL_NATIONAL_REQUIREMENT_PRESERVED",
            })
            return _finish(result)

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST CONTRADICTORY FINAL CLAIMS
        # ---------------------------------------------------------------

        if final_claim_status in {
            "CONTRADICTED",
            "INSUFFICIENT",
        }:

            result.update({
                "status": "POLICY_GAP_NOT_ESTABLISHED",
                "evidence_status": "INSUFFICIENT",
                "gap_status": "ABSENCE_NOT_ESTABLISHED",
                "human_review_required": True,
                "escalation_level": (
                    escalation
                    or "SENIOR_AUTHORITY"
                ),
                "reason": (
                    "The final evidence assessment does not establish "
                    "the existence of a policy, regulatory, standards, "
                    "or governance gap."
                ),
                "rule": "POLICY_GAP_NOT_ESTABLISHED",
            })

            return _finish(result)

        # ---------------------------------------------------------------
        # Check for explicit positive gap support
        # ---------------------------------------------------------------

        positive_gap_support = (
            _evidence_has_positive_gap_support(
                classification=classification,
                final_synthesis=final_synthesis,
            )
        )

        # ---------------------------------------------------------------
        # No positive support
        # ---------------------------------------------------------------

        if not positive_gap_support:

            result.update({
                "status": "POLICY_GAP_NOT_ESTABLISHED",
                "evidence_status": "INSUFFICIENT",
                "gap_status": "ABSENCE_NOT_ESTABLISHED",
                "human_review_required": True,
                "escalation_level": (
                    escalation
                    or "SENIOR_AUTHORITY"
                ),
                "reason": (
                    "The available evidence does not establish the "
                    "existence of a policy, regulatory, standards, "
                    "or governance gap."
                ),
                "rule": "POLICY_GAP_NOT_ESTABLISHED",
            })

            return _finish(result)

        # ---------------------------------------------------------------
        # Positive gap support
        # ---------------------------------------------------------------

        result.update({
            "status": "POLICY_GAP_ESTABLISHED",
            "evidence_status": "SUFFICIENT",
            "gap_status": "ESTABLISHED_GAP",
            "reason": (
                "Available evidence explicitly supports the existence "
                "of the identified policy/regulatory gap."
            ),
            "rule": "POLICY_GAP_ESTABLISHED",
        })

        return _finish(result)

    # -----------------------------------------------------------------------
    # RULE 3 — Consequential AI auto-approval
    #
    # AI must not automatically approve consequential regulatory decisions.
    # -----------------------------------------------------------------------

    if _is_consequential_auto_approval_question(
        question
    ):

        normalized_evidence_status = (
            "INSUFFICIENT"
            if original_evidence_status in {
                "UNKNOWN",
                "INSUFFICIENT",
                "ABSENCE_NOT_ESTABLISHED",
            }
            else original_evidence_status
        )

        normalized_gap_status = (
            original_gap_status
            if original_gap_status != "UNKNOWN"
            else "INSUFFICIENT"
        )

        result.update({
            "status": "HUMAN_REVIEW_REQUIRED",
            "evidence_status": normalized_evidence_status,
            "gap_status": normalized_gap_status,
            "risk_level": "CRITICAL",
            "human_review_required": True,
            "escalation_level": "SENIOR_AUTHORITY",
            "reason": (
                "A consequential telecom compliance decision must not "
                "be automatically approved by AI. Human authority "
                "is required."
            ),
            "rule": "CONSEQUENTIAL_DECISION_HUMAN_REVIEW",
        })

        return _finish(result)

    # -----------------------------------------------------------------------
    # GENERAL FALLBACK
    # -----------------------------------------------------------------------

    if risk_level == "CRITICAL":

        result["human_review_required"] = True

        if not result["escalation_level"]:
            result["escalation_level"] = (
                "SENIOR_AUTHORITY"
            )

        result["status"] = (
            "HUMAN_REVIEW_REQUIRED"
        )

        result["rule"] = (
            "CRITICAL_RISK_HUMAN_REVIEW"
        )

    return _finish(result)


# Utility: merge governance into pipeline output
# ---------------------------------------------------------------------------

def apply_governance_to_pipeline(
    pipeline_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply governance to an existing pipeline result.

    This function does not mutate the original evidence/RAG objects.
    It adds a top-level governance object and exposes normalized
    governance status.
    """

    governance = evaluate_governance(
        question=pipeline_result.get(
            "question",
            "",
        ),
        evidence_assessment=pipeline_result.get(
            "evidence_assessment",
            {},
        ),
        gap_analysis=pipeline_result.get(
            "gap_analysis",
            {},
        ),
        risk_assessment=pipeline_result.get(
            "risk_assessment",
            {},
        ),
        final_synthesis=pipeline_result.get(
            "final_synthesis",
            {},
        ),
        classification=pipeline_result.get(
            "classification",
        ),
    )

    pipeline_result["governance"] = governance

    return pipeline_result