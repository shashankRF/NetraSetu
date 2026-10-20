from __future__ import annotations
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    JurisdictionRole,
    RegionalRelationshipType,
    RegionalGapStatus,
    RegionalActionType,
    RegionalCoverageStatus,
    RegionalEvidenceItem,
    RegionalComparisonMapping,
    RegionalComparativeAnalysisResult,
)
from .jurisdiction_matrix import (
    get_relevant_regional_jurisdictions,
    assess_regional_kb_coverage,
)


class RegionalComparativeGapEngine:
    """
    Regional Comparative Gap Analysis Engine for HackGrid.
    Enforces the strict distinction between:
    1. HOST-COUNTRY APPLICABLE REQUIREMENTS
    2. INTERNATIONAL TECHNICAL REQUIREMENTS
    3. REGIONAL / NEIGHBOURING COMPARATIVE EVIDENCE
    Foreign/regional evidence NEVER silently becomes a legal or regulatory requirement of host country.
    """

    def __init__(
        self,
        host_jurisdiction: str = "India",
        regional_mode: str = "COMPARATIVE",
    ):
        self.host_jurisdiction = host_jurisdiction
        self.regional_mode = regional_mode

    def classify_evidence_item(
        self,
        record: Dict[str, Any],
        idx: int = 1,
    ) -> RegionalEvidenceItem:
        ev_id = record.get("id") or record.get("evidence_id") or f"EV-{idx:03d}"
        doc = record.get("document") or record.get("metadata", {}).get("document") or "Unknown Document"
        src = record.get("source") or record.get("metadata", {}).get("source_file") or doc
        jur = record.get("jurisdiction") or record.get("metadata", {}).get("jurisdiction") or ""
        text = record.get("text") or record.get("chunk_text") or record.get("requirement_text") or ""
        clause = record.get("clause") or record.get("metadata", {}).get("clause")
        sec = record.get("section") or record.get("metadata", {}).get("section")
        page = record.get("page") or record.get("metadata", {}).get("page")
        confidence = float(record.get("confidence") or 0.85)

        jur_lower = jur.lower()
        doc_lower = doc.lower()
        src_lower = src.lower()
        text_lower = text.lower()
        host_lower = self.host_jurisdiction.lower()

        explicit_role = record.get("jurisdiction_role")
        if explicit_role:
            role = JurisdictionRole(explicit_role) if explicit_role in JurisdictionRole._value2member_map_ else JurisdictionRole.UNKNOWN
        elif host_lower in jur_lower or "dot" in doc_lower or "tec" in doc_lower or "trai" in doc_lower or "telecommunications act" in doc_lower:
            role = JurisdictionRole.HOST
        elif (
            "international" in jur_lower
            or "3gpp" in doc_lower
            or "3gpp" in src_lower
            or "itu" in doc_lower
            or "etsi" in doc_lower
            or "iso" in doc_lower
            or "ieee" in doc_lower
        ):
            role = JurisdictionRole.INTERNATIONAL
        elif any(country in jur_lower or country in doc_lower or country in text_lower for country in [
            "bangladesh", "sri lanka", "pakistan", "nepal", "bhutan", "singapore", "japan", "united kingdom", "norway"
        ]):
            role = JurisdictionRole.REGIONAL_COMPARATIVE
        else:
            role = JurisdictionRole.UNKNOWN

        if role == JurisdictionRole.HOST:
            app_reason = f"Directly applicable host-country requirement/provision ({self.host_jurisdiction})."
            reg_rel = RegionalRelationshipType.HOST_APPLICABLE
        elif role == JurisdictionRole.INTERNATIONAL:
            app_reason = "International technical standard / baseline security requirement."
            reg_rel = RegionalRelationshipType.INTERNATIONAL_TECHNICAL_REQUIREMENT
        elif role == JurisdictionRole.REGIONAL_COMPARATIVE:
            app_reason = (
                f"Regional comparative requirement/evidence point. Direct legal or regulatory "
                f"applicability to {self.host_jurisdiction} is NOT established by supplied evidence."
            )
            reg_rel = RegionalRelationshipType.REGIONAL_COMPARATIVE_REQUIREMENT
        else:
            app_reason = "Contextual or auxiliary evidence item of unestablished jurisdiction."
            reg_rel = RegionalRelationshipType.NOT_COMPARABLE

        return RegionalEvidenceItem(
            evidence_id=ev_id,
            source=src,
            source_type="NATIONAL_REGULATION" if role == JurisdictionRole.HOST else ("INTERNATIONAL_TECHNICAL_STANDARD" if role == JurisdictionRole.INTERNATIONAL else "REGIONAL_COMPARATIVE_PROVISION"),
            country=jur or ("India" if role == JurisdictionRole.HOST else ("International" if role == JurisdictionRole.INTERNATIONAL else "Regional")),
            document=doc,
            requirement_text=text,
            clause=clause,
            section=sec,
            page=page,
            confidence=confidence,
            jurisdiction_role=role,
            comparative_relevance="DIRECT" if role != JurisdictionRole.UNKNOWN else "CONTEXTUAL",
            applicability_reason=app_reason,
            regional_relationship=reg_rel,
        )

    def compare(
        self,
        evidence_records: List[Dict[str, Any]],
        question: str = "",
        domain: str = "telecom",
    ) -> RegionalComparativeAnalysisResult:
        comp_id = f"RCG-{uuid.uuid4().hex[:8].upper()}"
        regional_jurisdictions = get_relevant_regional_jurisdictions(
            self.host_jurisdiction,
            domain=domain,
            question=question,
        )

        classified_items: List[RegionalEvidenceItem] = []
        for i, rec in enumerate(evidence_records, start=1):
            item = self.classify_evidence_item(rec, i)
            classified_items.append(item)

        coverage_matrix = assess_regional_kb_coverage(
            self.host_jurisdiction,
            regional_jurisdictions,
            evidence_records,
        )

        intl_items = [it for it in classified_items if it.jurisdiction_role == JurisdictionRole.INTERNATIONAL]
        host_items = [it for it in classified_items if it.jurisdiction_role == JurisdictionRole.HOST]
        reg_items = [it for it in classified_items if it.jurisdiction_role == JurisdictionRole.REGIONAL_COMPARATIVE]

        mappings: List[RegionalComparisonMapping] = []
        human_review_required = False
        counter_evidence_ids: List[str] = []
        counter_evidence_summaries: List[str] = []

        if len(reg_items) >= 2:
            reg_texts = [r.requirement_text.lower() for r in reg_items]
            has_divergence = any("alternative" in t or "exception" in t or "optional" in t for t in reg_texts) and any("mandatory" in t or "strict" in t or "require" in t for t in reg_texts)
            if has_divergence:
                human_review_required = True
                counter_evidence_ids.extend([r.evidence_id for r in reg_items])
                counter_evidence_summaries.append(
                    "Regional evidence exhibits divergent implementations: one regional jurisdiction allows alternative controls while another mandates strict specific measures. Human review is required to evaluate comparative relevance."
                )

        if not intl_items:
            intl_req_summary = "Technical security and integrity requirement defined by international standard (e.g. 3GPP / ITU-T)."
            intl_dict = {
                "requirement_id": "REQ-INTL-001",
                "standard": "3GPP / ITU-T",
                "requirement_summary": intl_req_summary,
                "evidence_id": "NOT_RETRIEVED",
            }
        else:
            intl_first = intl_items[0]
            intl_dict = {
                "requirement_id": intl_first.evidence_id,
                "standard": intl_first.document,
                "requirement_summary": intl_first.requirement_text[:200].strip(),
                "evidence_id": intl_first.evidence_id,
            }

        if not host_items:
            # STRICT ABSENCE PROTOCOL
            gap_status = RegionalGapStatus.ABSENCE_NOT_ESTABLISHED
            action = RegionalActionType.INVESTIGATE
            coverage_status = "Not Established"
            reason = (
                f"An applicable host-country provision was not established in the evidence examined for {self.host_jurisdiction}. "
                "Regional evidence cannot be used to prove absence of regulation in the host jurisdiction."
            )
            remediation = f"Conduct targeted regulatory discovery and verify whether authoritative provisions exist in {self.host_jurisdiction}."
            impact = "Regulatory applicability remains unverified; absence of requirement cannot be asserted without exhaustive proof."
            limitations = f"Knowledge base retrieval did not establish host-country provisions for {self.host_jurisdiction}."
            human_review_required = True

            map_record = RegionalComparisonMapping(
                mapping_id=f"MAP-{comp_id}-01",
                international_requirement=intl_dict,
                host_provision=None,
                regional_provision=reg_items[0].to_dict() if reg_items else None,
                coverage=coverage_status,
                missing_element=None,
                gap_status=gap_status,
                action=action,
                reason=reason,
                impact=impact,
                remediation=remediation,
                limitations=limitations,
            )
            mappings.append(map_record)

        else:
            host_text_corpus = " ".join(h.requirement_text.lower() for h in host_items)
            host_primary = host_items[0].to_dict()
            reg_primary = reg_items[0].to_dict() if reg_items else None

            is_terminology_diff = ("partitioning" in host_text_corpus or "logical separation" in host_text_corpus) and ("slice isolation" in question.lower() or "slice isolation" in intl_dict["requirement_summary"].lower())
            
            is_fully_covered = any(k in host_text_corpus for k in ["mandatory", "must adhere", "strictly comply", "isolation and authentication", "explicit requirement satisfied"]) and not any(k in host_text_corpus for k in ["missing", "not addressed", "uncovered"])

            is_authoritative_gap = any(k in host_text_corpus for k in ["not addressed in national regulations", "unaddressed in indian requirements", "gap established", "lacks explicit provision", "no corresponding requirement in dot"])

            is_partially_covered = any(k in host_text_corpus for k in ["partially", "general security", "baseline security", "does not explicitly establish", "not explicitly addressed"]) or (not is_fully_covered and not is_authoritative_gap and not is_terminology_diff)

            regional_has_stricter = False
            if reg_items:
                reg_text_corpus = " ".join(r.requirement_text.lower() for r in reg_items)
                if "explicit" in reg_text_corpus or "stricter" in reg_text_corpus or "mandatory isolation" in reg_text_corpus:
                    regional_has_stricter = True

            is_alternative_approach = any("alternative" in host_text_corpus or "equivalent control" in host_text_corpus for _ in [1])

            if is_terminology_diff:
                gap_status = RegionalGapStatus.NOT_A_GAP
                action = RegionalActionType.NO_ACTION
                coverage_status = "Covered (Terminology Difference)"
                reason = (
                    f"{self.host_jurisdiction} provision establishes substantive technical control under different terminology. "
                    "Linguistic difference does not constitute a regulatory gap."
                )
                remediation = "Document terminology cross-mapping between international specification and national standard."
                impact = "Operational controls align substantively; no compliance deficiency."
                limitations = "Terminology varies across standards bodies but control intent is satisfied."

            elif is_fully_covered:
                gap_status = RegionalGapStatus.NO_ESTABLISHED_GAP
                action = RegionalActionType.NO_ACTION
                coverage_status = "Covered"
                if regional_has_stricter:
                    reason = (
                        f"{self.host_jurisdiction} provisions adequately address the international technical requirement. "
                        "Regional neighbouring country enforces an additional regional control, but this does not create a gap for the host country."
                    )
                else:
                    reason = f"{self.host_jurisdiction} provisions adequately cover the international security baseline."
                remediation = "Maintain existing technical compliance controls and regular audit monitoring."
                impact = "No operational risk; controls satisfy established host and international mandates."
                limitations = "Continuous verification recommended upon future standard revisions."

            elif is_authoritative_gap:
                gap_status = RegionalGapStatus.ESTABLISHED_GAP
                action = RegionalActionType.FIX
                coverage_status = "Uncovered"
                reason = (
                    f"Authoritative host evidence demonstrates that the technical control is not adequately addressed in {self.host_jurisdiction} provisions. "
                    "Genuine gap test criteria are satisfied."
                )
                remediation = "Implement explicit technical controls (e.g., cryptographic isolation, mutual authentication) and seek compliance alignment."
                impact = "Potential compliance non-conformance and operational vulnerability in multi-tenant environments."
                limitations = "Applies specifically to the technical domain evaluated."

            elif is_alternative_approach:
                gap_status = RegionalGapStatus.NO_ESTABLISHED_GAP
                action = RegionalActionType.NO_ACTION
                coverage_status = "Covered via Alternative Approach"
                reason = (
                    f"{self.host_jurisdiction} evidence demonstrates an alternative implementation approach that achieves equivalent security objectives."
                )
                remediation = "Document technical equivalence and validate control effectiveness."
                impact = "Equivalent security posture maintained through alternative architecture."
                limitations = "Equivalence must be audited during accreditation."

            else:
                gap_status = RegionalGapStatus.PARTIALLY_COVERED if is_partially_covered else RegionalGapStatus.POTENTIAL_GAP_NOT_ESTABLISHED
                action = RegionalActionType.VERIFY
                coverage_status = "Partially Covered"
                
                if reg_items:
                    reason = (
                        f"{self.host_jurisdiction} evidence provides partial coverage of network security but does not explicitly verify the specific control. "
                        f"Regional comparative evidence identifies an explicit control in {reg_items[0].country}, demonstrating a comparative approach, "
                        f"but this does NOT establish a legal requirement in {self.host_jurisdiction}. The difference remains a potential policy/standards gap requiring verification."
                    )
                else:
                    reason = (
                        f"{self.host_jurisdiction} evidence partially addresses the requirement. "
                        "Proof of a complete regulatory gap is incomplete; potential gap requires verification."
                    )
                remediation = "Perform technical verification against national technical specifications and obtain clarification from regulatory authorities."
                impact = "Operational controls may have unverified edge-case coverage; requires engineering and regulatory verification."
                limitations = "Regional comparison provides contextual best practice only; host applicability remains subject to verification."
                human_review_required = True

            map_record = RegionalComparisonMapping(
                mapping_id=f"MAP-{comp_id}-01",
                international_requirement=intl_dict,
                host_provision=host_primary,
                regional_provision=reg_primary,
                coverage=coverage_status,
                missing_element="Explicit control specification" if gap_status in {RegionalGapStatus.PARTIALLY_COVERED, RegionalGapStatus.POTENTIAL_GAP_NOT_ESTABLISHED, RegionalGapStatus.ESTABLISHED_GAP} else None,
                gap_status=gap_status,
                action=action,
                reason=reason,
                impact=impact,
                remediation=remediation,
                counter_evidence=reg_items if counter_evidence_ids else [],
                limitations=limitations,
            )
            mappings.append(map_record)

        primary_mapping = mappings[0]
        final_gap_status = primary_mapping.gap_status
        final_action = primary_mapping.action
        final_coverage_status = primary_mapping.coverage
        final_reasoning = primary_mapping.reason
        final_impact = primary_mapping.impact
        final_remediation = primary_mapping.remediation
        final_limitations = primary_mapping.limitations

        if not reg_items and coverage_matrix.get("Regional") == "NOT ESTABLISHED":
            final_limitations = (
                final_limitations + (" | " if final_limitations else "") +
                "Regional comparison could not be established because sufficient evidence for the relevant neighbouring jurisdiction was not available in the current knowledge base."
            )

        counter_ev_summary_str = " ".join(counter_evidence_summaries) if counter_evidence_summaries else "No conflicting regional counter-evidence identified."

        return RegionalComparativeAnalysisResult(
            comparison_id=comp_id,
            host_jurisdiction=self.host_jurisdiction,
            regional_jurisdictions=regional_jurisdictions,
            regional_mode=self.regional_mode,
            international_requirements=[it.to_dict() for it in intl_items] or [intl_dict],
            host_requirements=[h.to_dict() for h in host_items],
            regional_requirements=[r.to_dict() for r in reg_items],
            mappings=[m.to_dict() for m in mappings],
            coverage_status=final_coverage_status,
            gap_status=final_gap_status,
            action=final_action,
            evidence_ids=[it.evidence_id for it in classified_items],
            counter_evidence_ids=counter_evidence_ids,
            applicability={
                "host_direct_legal": True,
                "international_technical_baseline": True,
                "regional_comparative_only": True,
                "rule": f"Regional evidence does NOT constitute {self.host_jurisdiction} law.",
            },
            comparative_relevance="HIGH" if reg_items else "NONE_AVAILABLE_IN_KB",
            reasoning=final_reasoning,
            impact=final_impact,
            remediation=final_remediation,
            counter_evidence_summary=counter_ev_summary_str,
            limitations=final_limitations,
            human_review_required=human_review_required,
            regional_coverage=coverage_matrix,
        )
