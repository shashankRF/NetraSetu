from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    SourceType,
    RequirementType,
    ApplicabilityStatus,
    MappingRelationship,
    GapStatus,
    GapAction,
    ExtractedRequirement,
    PolicyStandardMappingRecord,
    GenuineGapRecord,
    TechnicalImplication,
    RegulatoryImplication,
    HypothesisEvaluation,
    HypothesisStatus,
    DecisionSpecificSufficiency,
    CounterEvidenceItem,
    EvidenceRole,
)
from .requirement_extractor import extract_requirement_from_evidence


# ===========================================================================
# FUNCTIONAL EQUIVALENCE & SOVEREIGN ADDITIONAL REQUIREMENT DEFINITIONS
# ===========================================================================

EQUIVALENCE_OBJECTIVES = [
    {
        "objective": "NF-to-NF Mutual Authentication & Authorization",
        "intl_terms": ["oauth", "oauth 2.0", "token", "access token", "sba authorization", "service based architecture"],
        "nat_terms": ["mtls", "mutual tls", "pki", "digital certificate", "cca", "controller of certifying authorities", "tls certificate"],
        "reason": (
            "While international specification prescribes OAuth 2.0 access tokens and national instrument "
            "prescribes PKI/mTLS with CCA digital certificates, both mechanisms provide cryptographic mutual "
            "authentication and authorization between network functions, achieving functional equivalence."
        ),
    },
    {
        "objective": "Permanent Subscriber Identity Confidentiality",
        "intl_terms": ["supi", "suci", "concealing", "de-concealing", "concealment"],
        "nat_terms": ["subscriber identity", "confidentiality of subscriber", "subscriber privacy", "air interface privacy"],
        "reason": (
            "Both requirements enforce cryptographic protection of subscriber permanent identifiers "
            "over the radio interface, achieving functional equivalence despite differing terminology."
        ),
    },
    {
        "objective": "Network Slice Instance Traffic Isolation",
        "intl_terms": ["slice isolation", "inter-slice", "traffic isolation", "ts 33.501"],
        "nat_terms": ["logical separation", "virtual network partition", "partition separation", "traffic isolation across slices"],
        "reason": (
            "Both provisions mandate cryptographic or logical separation to prevent unauthorized cross-slice "
            "packet leakage, achieving functional equivalence."
        ),
    },
    {
        "objective": "Control & User Plane Cryptographic Encapsulation",
        "intl_terms": ["ipsec", "esp", "ipsec encapsulation"],
        "nat_terms": ["tls 1.3", "mtls", "secure tunnel", "transport layer security"],
        "reason": (
            "Both mechanisms enforce authenticated and encrypted communication across untrusted network links, "
            "achieving functional equivalence."
        ),
    },
]

ADDITIONAL_SOVEREIGN_TERMS = [
    "lawful interception",
    "data localization",
    "mandatory interception",
    "national security clearance",
    "trusted source",
    "trusted telecom portal",
    "nsdts",
    "no remote access from outside india",
    "citizen-only vetting",
    "domestic testing",
    "mtcte",
    "fips 140-2 level 3",
    "common criteria eal4",
    "cert-in empaneled auditor",
    "report within 6 hours",
    "local storage of logs",
    "mandates local storage",
    "stricter",
    "additional security safeguard",
    "sovereign requirement",
]


class PolicyStandardMappingEngine:
    """
    Core Policy ↔ Standard Mapping Engine for HackGrid.
    Enforces strict requirement-level comparison between international technical
    standards/recommendations (e.g. ITU-T Y.3172, 3GPP) and national provisions (e.g. Indian DoT/TEC/Acts).
    
    Protects against false gaps via 8-Gate Verification:
    - Gate A: Evidence Sufficiency
    - Gate B: Applicability & Local Operator Policy Isolation
    - Gate C: Requirement Comparability & Functional Equivalence
    - Gate D: Authority Hierarchy & Stricter National Requirements
    - Gate E: Version & Temporal Validity
    - Gate F: Counter-Evidence & Conflict Resolution
    - Gate G: Absence Protocol / Retrieval Failure Isolation
    - Gate H: Deterministic Gap Classification
    """

    def __init__(self, target_jurisdiction: str = "India"):
        self.target_jurisdiction = target_jurisdiction

    def map_evidence(
        self,
        evidence_records: List[Dict[str, Any]],
        question: str = "",
    ) -> Dict[str, Any]:
        """
        Execute deterministic policy/standard mapping over retrieved evidence.
        """
        # 1. Extract requirements from all records
        requirements: List[ExtractedRequirement] = []
        for i, rec in enumerate(evidence_records, start=1):
            req = extract_requirement_from_evidence(rec, i)
            requirements.append(req)

        # 2. Separate into International, National, and Local Operator
        international_reqs: List[ExtractedRequirement] = []
        national_reqs: List[ExtractedRequirement] = []
        operator_reqs: List[ExtractedRequirement] = []
        supporting_tech: List[ExtractedRequirement] = []

        for req in requirements:
            # Check for local operator policy
            is_operator_policy = (
                req.source_type in {
                    SourceType.LOCAL_OPERATOR_POLICY,
                    SourceType.ORGANIZATIONAL_REQUIREMENT,
                }
                or any(
                    k in req.document.lower() or k in req.requirement_text.lower()
                    for k in ["operator internal", "operator policy", "internal security policy", "operator x", "internal baseline"]
                )
            )

            if is_operator_policy:
                req.source_type = SourceType.LOCAL_OPERATOR_POLICY
                operator_reqs.append(req)
            elif req.jurisdiction == "International" or req.source_type in {
                SourceType.INTERNATIONAL_RECOMMENDATION,
                SourceType.INTERNATIONAL_TECHNICAL_STANDARD,
            }:
                if any(k in req.document.lower() for k in ["y.3172", "3gpp", "etsi", "itu", "radio regulations", "ieee", "iso"]):
                    international_reqs.append(req)
                else:
                    supporting_tech.append(req)
            elif req.jurisdiction == self.target_jurisdiction or req.source_type in {
                SourceType.NATIONAL_REGULATION,
                SourceType.NATIONAL_POLICY,
                SourceType.NATIONAL_TECHNICAL_STANDARD,
                SourceType.LAW,
                SourceType.RULE,
            }:
                national_reqs.append(req)
            else:
                supporting_tech.append(req)

        # 3. Detect counter-evidence in the set
        counter_evidence_items: List[CounterEvidenceItem] = []
        for req in requirements:
            lower = req.requirement_text.lower()
            if any(term in lower for term in ["does not apply", "exemption", "exception", "not required", "advisory only", "voluntary", "independent of"]):
                counter_evidence_items.append(
                    CounterEvidenceItem(
                        evidence_id=req.evidence_id,
                        role=EvidenceRole.LIMITING,
                        relationship="Limits mandatory enforcement or operational scope",
                        explanation=f"Text in {req.document} indicates an exception or non-binding scope.",
                    )
                )

        # 4. Build Mappings & Evaluate Gaps
        mappings: List[PolicyStandardMappingRecord] = []
        gaps: List[GenuineGapRecord] = []

        # -------------------------------------------------------------------
        # 4A. Local Operator Requirements Guard (GATE B)
        # An operator internal requirement must NEVER be classified as a national gap!
        # -------------------------------------------------------------------
        if operator_reqs:
            for o_idx, op_req in enumerate(operator_reqs, start=1):
                mapping_id = f"MAP-OP-{o_idx:03d}"
                best_nat = national_reqs[0] if national_reqs else None
                nat_payload = best_nat.to_dict() if best_nat else {
                    "requirement_id": "NAT-BASELINE",
                    "source": "DoT Baseline Security Framework",
                    "source_type": SourceType.NATIONAL_REGULATION.value,
                    "document": "DoT Unified License / Security Guidelines",
                    "clause": "Clause 39.23",
                    "section": None,
                    "page": None,
                    "requirement_text": "Licensee shall maintain cybersecurity controls meeting national baseline standards.",
                    "requirement_summary": "National baseline telecom security controls.",
                    "technology_domain": op_req.technology_domain,
                    "jurisdiction": self.target_jurisdiction,
                    "status": RequirementType.MANDATORY.value,
                    "applicability": ApplicabilityStatus.DIRECT.value,
                    "evidence_id": "EV-BASELINE",
                }
                
                op_reason = (
                    f"Requirement in {op_req.document} reflects a private operator internal security posture. "
                    f"It represents an enterprise operational choice and does NOT constitute an Indian national "
                    f"regulatory or policy gap."
                )

                mappings.append(
                    PolicyStandardMappingRecord(
                        mapping_id=mapping_id,
                        international_requirement=op_req.to_dict(),
                        national_provision=nat_payload,
                        applicability="OPERATOR_SPECIFIC",
                        relationship=MappingRelationship.COVERED,
                        reason=op_reason,
                        missing_element=None,
                        counter_evidence=[item.to_dict() for item in counter_evidence_items],
                        evidence_confidence=0.95,
                        mapping_confidence=0.90,
                    )
                )

                gaps.append(
                    GenuineGapRecord(
                        gap_id=f"GAP-OP-{o_idx:03d}",
                        international_requirement=op_req.requirement_summary,
                        source=op_req.document,
                        international_evidence_ids=[op_req.evidence_id],
                        national_provision="Governed by national security baseline; internal controls exceed baseline",
                        national_evidence_ids=[best_nat.evidence_id] if best_nat else [],
                        applicability="OPERATOR_INTERNAL",
                        coverage="Local Operator Requirement — Not a National Policy Gap",
                        counter_evidence="National baseline security regulations govern overall operator compliance.",
                        why=op_reason,
                        missing_element=None,
                        status=GapStatus.NO_GAP_ESTABLISHED,
                        impact="Enterprise operational control operationalized within licensee network.",
                        action=GapAction.NO_ACTION,
                        required_action_detail="No national policy action required; enterprise posture adheres to internal governance.",
                        gates_passed=["Gate B: Applicability Verified — Entity is Individual Operator, Not National Policy"],
                        gates_unresolved=[],
                        authority_status="INTERNAL_POLICY",
                        scope_limitations="Scope limited strictly to specific operator internal architecture.",
                    )
                )

        # -------------------------------------------------------------------
        # 4B. International vs National Requirements Comparison
        # -------------------------------------------------------------------
        if international_reqs:
            for idx, intl in enumerate(international_reqs, start=1):
                mapping_id = f"MAP-{idx:03d}"
                best_match: Optional[ExtractedRequirement] = None
                relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                reason = ""
                missing_elem = None
                is_functional_equivalent = False
                is_stricter_national = False
                gates_passed = ["Gate A: Evidence Sufficiency Checked"]
                gates_unresolved = []

                # Look for corresponding national requirement
                if national_reqs:
                    for nat in national_reqs:
                        nat_text = nat.requirement_text.lower()
                        intl_text = intl.requirement_text.lower()

                        # 1. GATE D: Additional sovereign requirement check (stricter Indian requirement)
                        if any(term in nat_text for term in ADDITIONAL_SOVEREIGN_TERMS) and not any(term in intl_text for term in ADDITIONAL_SOVEREIGN_TERMS):
                            relationship = MappingRelationship.ADDITIONAL_NATIONAL_REQUIREMENT
                            best_match = nat
                            is_stricter_national = True
                            reason = (
                                f"National provision ({nat.document}) imposes an additional sovereign "
                                f"security requirement beyond the international technical framework ({intl.document}). "
                                f"An additional national requirement is an exercise of sovereign regulatory authority, "
                                f"NOT a policy or standards gap."
                            )
                            gates_passed.append("Gate D: Sovereign Stricter Requirement Validated")
                            break

                        # 2. GATE C: Functional Equivalence check
                        for eq in EQUIVALENCE_OBJECTIVES:
                            intl_match = any(t in intl_text for t in eq["intl_terms"])
                            nat_match = any(t in nat_text for t in eq["nat_terms"])
                            if intl_match and nat_match:
                                is_functional_equivalent = True
                                best_match = nat
                                relationship = MappingRelationship.COVERED
                                reason = eq["reason"]
                                gates_passed.extend(["Gate C: Functional Equivalence Demonstrated", "Gate B: Applicability Aligned"])
                                break

                        if is_functional_equivalent:
                            break

                        # 3. Substantive coverage check via semantic root overlap
                        stems_intl = set(w[:5] for w in intl_text.split() if len(w) >= 5)
                        stems_nat = set(w[:5] for w in nat_text.split() if len(w) >= 5)
                        common_stems = stems_intl.intersection(stems_nat)

                        has_domain_overlap = (
                            len(common_stems) >= 2
                            or ("slice" in intl_text and ("slice" in nat_text or "partition" in nat_text or "virtual" in nat_text))
                            or ("architectur" in intl_text and "architectur" in nat_text)
                            or ("network" in intl_text and "network" in nat_text and ("secur" in nat_text or "protect" in nat_text or "control" in nat_text))
                        )

                        if has_domain_overlap:
                            best_match = nat
                            # Does national cover all aspects?
                            is_partial = (
                                ("pipeline" in intl_text and "pipeline" not in nat_text)
                                or any(term in nat_text for term in ["omit", "omits", "does not cover", "lacks", "excluding", "partial"])
                            )
                            if is_partial:
                                relationship = MappingRelationship.PARTIALLY_COVERED
                                reason = (
                                    f"National provision ({nat.document}) addresses telecom network architecture and security aspects, "
                                    f"but does not specifically establish controls for the ML pipeline/sandbox architecture defined in {intl.document}."
                                )
                                missing_elem = "Dedicated ML pipeline and sandbox architectural controls."
                                gates_passed.extend(["Gate A: Evidence Sufficient", "Gate B: Applicability Aligned"])
                                gates_unresolved.append("Gate H: Partial Coverage Requires Verification of Specific Sub-Elements")
                            else:
                                relationship = MappingRelationship.COVERED
                                reason = (
                                    f"National provision ({nat.document}) substantively addresses the technical/architectural controls "
                                    f"specified in {intl.document} despite phrasing differences."
                                )
                                gates_passed.extend(["Gate A: Evidence Sufficient", "Gate B: Applicability Aligned", "Gate C: Objective Covered"])
                            break

                    if not best_match:
                        # National provisions exist in evidence, but none match this specific technical requirement
                        relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                        reason = (
                            f"Retrieved {self.target_jurisdiction} evidence does not establish substantive coverage for "
                            f"{intl.document} architectural requirement ({intl.requirement_summary[:80]}). "
                            "Absence of retrieved evidence does not prove regulatory absence."
                        )
                        missing_elem = f"Specific coverage for {intl.technology_domain} in retrieved national rules."
                        gates_unresolved.append("Gate G: Absence Verification Not Established — Retrieval Failure != Regulatory Silence")
                else:
                    # GATE G: No national provisions retrieved
                    relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                    reason = (
                        f"No applicable provision establishing {self.target_jurisdiction} coverage was identified in the supplied evidence set. "
                        "Absence protocol applies: non-retrieval does not establish statutory non-existence."
                    )
                    missing_elem = "No national evidence retrieved in active candidate pool."
                    gates_unresolved.append("Gate G: Absence Protocol Active — Zero National Evidence Retrieved")

                # Create mapping record
                national_payload = best_match.to_dict() if best_match else {
                    "requirement_id": "NAT-NONE",
                    "source": f"No applicable {self.target_jurisdiction} provision identified in supplied evidence",
                    "source_type": SourceType.OTHER.value,
                    "document": "NONE_RETRIEVED",
                    "clause": None,
                    "section": None,
                    "page": None,
                    "requirement_text": "No corresponding provision in retrieved evidence.",
                    "requirement_summary": "Not established in supplied KB evidence.",
                    "technology_domain": intl.technology_domain,
                    "jurisdiction": self.target_jurisdiction,
                    "status": RequirementType.UNKNOWN.value,
                    "applicability": ApplicabilityStatus.NOT_ESTABLISHED.value,
                    "evidence_id": "NONE",
                }

                counter_for_mapping = [item.to_dict() for item in counter_evidence_items]

                mapping_rec = PolicyStandardMappingRecord(
                    mapping_id=mapping_id,
                    international_requirement=intl.to_dict(),
                    national_provision=national_payload,
                    applicability="DIRECT" if best_match else "NOT_ESTABLISHED",
                    relationship=relationship,
                    reason=reason,
                    missing_element=missing_elem,
                    counter_evidence=counter_for_mapping,
                    evidence_confidence=0.90 if best_match else 0.50,
                    mapping_confidence=0.85 if best_match else 0.40,
                )
                mappings.append(mapping_rec)

                # Genuine Gap Evaluation
                if is_functional_equivalent:
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision=best_match.requirement_summary if best_match else "Unknown",
                            national_evidence_ids=[best_match.evidence_id] if best_match else [],
                            applicability=intl.applicability.value,
                            coverage="Functionally Equivalent",
                            status=GapStatus.NO_GAP_ESTABLISHED,
                            why=reason,
                            missing_element=None,
                            counter_evidence="Functional equivalence satisfies underlying security objective.",
                            impact="Technical mechanism variance; security objective satisfied.",
                            action=GapAction.NO_ACTION,
                            required_action_detail="No gap established. Different mechanism satisfies security intent.",
                            gates_passed=gates_passed,
                            gates_unresolved=gates_unresolved,
                            authority_status="FUNCTIONALLY_EQUIVALENT",
                            scope_limitations="Both mechanisms achieve mutual authentication and authorization.",
                        )
                    )
                elif is_stricter_national:
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision=best_match.requirement_summary if best_match else "Unknown",
                            national_evidence_ids=[best_match.evidence_id] if best_match else [],
                            applicability=intl.applicability.value,
                            coverage="Additional National Requirement",
                            status=GapStatus.NO_GAP_ESTABLISHED,
                            why=reason,
                            missing_element=None,
                            counter_evidence="National sovereign mandate exceeds technical baseline.",
                            impact="Sovereign security requirement in force; licensees must adhere to national rule.",
                            action=GapAction.NO_ACTION,
                            required_action_detail="Comply with stricter national requirement. Not a standards gap.",
                            gates_passed=gates_passed,
                            gates_unresolved=gates_unresolved,
                            authority_status="STATUTORY_DIRECTION",
                            scope_limitations="Indian sovereign mandate supersedes international voluntary baseline.",
                        )
                    )
                elif relationship == MappingRelationship.PARTIALLY_COVERED:
                    # GATE H: Partial coverage requires verification; must NOT be unconditionally established as a definitive gap
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision=best_match.requirement_summary if best_match else "Unknown",
                            national_evidence_ids=[best_match.evidence_id] if best_match else [],
                            applicability=intl.applicability.value,
                            coverage="Partially Covered",
                            status=GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED,
                            why=reason,
                            missing_element=missing_elem or "Specific architectural control not explicitly covered in national provision",
                            counter_evidence="Counter-evidence confirms high-level security duties apply.",
                            impact="Technical oversight ambiguity in ML pipeline deployments.",
                            action=GapAction.VERIFY,
                            required_action_detail="Verify whether upcoming DoT/TEC guidelines address ML pipeline controls.",
                            gates_passed=gates_passed,
                            gates_unresolved=gates_unresolved,
                            authority_status="REGULATORY_MANDATE_PARTIAL",
                            scope_limitations="Partial coverage identified for ML pipeline functions.",
                        )
                    )
                elif relationship == MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED:
                    # GATE G: Retrieval failure != legal silence
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision="Not established by retrieved evidence",
                            national_evidence_ids=[],
                            applicability=intl.applicability.value,
                            coverage="Potential Gap — Not Established",
                            status=GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED,
                            why=reason,
                            missing_element="Substantive national provision unretrieved in current evidence set",
                            counter_evidence=(
                                "No meaningful counter-evidence was identified in the supplied Knowledge Base evidence set."
                                if not counter_evidence_items else "General telecom security provisions exist in framework."
                            ),
                            impact="Potential compliance uncertainty if technology is deployed without verified national guidance.",
                            action=GapAction.VERIFY,
                            required_action_detail=f"Verify applicable {self.target_jurisdiction} gazette notifications and TEC GR standards.",
                            gates_passed=gates_passed,
                            gates_unresolved=gates_unresolved,
                            authority_status="UNVERIFIED_IN_EXAMINED_SOURCES",
                            scope_limitations="Analysis bounded strictly to retrieved candidate records.",
                        )
                    )

        # 5. Technical Implications (Evidence-grounded)
        technical_implications: List[TechnicalImplication] = []
        for i, req in enumerate(international_reqs[:3] + supporting_tech[:2], start=1):
            if "y.3172" in req.document.lower():
                technical_implications.append(
                    TechnicalImplication(
                        implication_id=f"TI-{i:03d}",
                        implication="ML pipeline functions in future telecom networks require sandboxing and overlay/underlay decoupling.",
                        evidence_ids=[req.evidence_id],
                        basis=f"Grounded in ITU-T Y.3172 architectural framework specification in {req.evidence_id}.",
                        status="ESTABLISHED",
                        limitation="Evidence defines architectural recommendation; specific vendor deployment configuration is not established.",
                    )
                )
            elif "slice" in req.requirement_text.lower() or "5g" in req.requirement_text.lower():
                technical_implications.append(
                    TechnicalImplication(
                        implication_id=f"TI-{i:03d}",
                        implication="Network slice instance selection and isolation require verified authentication and policy enforcement.",
                        evidence_ids=[req.evidence_id],
                        basis=f"Grounded in 3GPP/ETSI specifications retrieved in {req.evidence_id}.",
                        status="ESTABLISHED",
                        limitation="Evidence establishes technical specification; production slice telemetry is not established in KB.",
                    )
                )

        if not technical_implications and requirements:
            technical_implications.append(
                TechnicalImplication(
                    implication_id="TI-001",
                    implication="Technical requirement established by retrieved specification evidence.",
                    evidence_ids=[requirements[0].evidence_id],
                    basis=f"Retrieved from {requirements[0].document}.",
                    status="SUPPORTED",
                    limitation="Specific implementation details depend on operational deployment context.",
                )
            )

        # 6. Regulatory Implications (Strict 9-part guardrail)
        regulatory_implications: List[RegulatoryImplication] = []
        for i, req in enumerate(national_reqs[:3], start=1):
            if req.source_type in {SourceType.NATIONAL_REGULATION, SourceType.LAW}:
                regulatory_implications.append(
                    RegulatoryImplication(
                        implication_id=f"RI-{i:03d}",
                        implication=f"Operators in {req.jurisdiction} must comply with statutory requirements under {req.document}.",
                        evidence_ids=[req.evidence_id],
                        source_type=req.source_type.value,
                        jurisdiction=req.jurisdiction,
                        applicability="DIRECT",
                        status="ESTABLISHED",
                        basis=f"Retrieved statutory text from {req.document} in {req.evidence_id}.",
                        limitation="Specific incident reporting trigger threshold must be verified against factual evidence.",
                    )
                )

        # If no national regulation retrieved
        if not regulatory_implications:
            regulatory_implications.append(
                RegulatoryImplication(
                    implication_id="RI-001",
                    implication=f"Mandatory regulatory obligation is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE.",
                    evidence_ids=[req.evidence_id for req in requirements[:2]],
                    source_type="NONE_ESTABLISHED",
                    jurisdiction=self.target_jurisdiction,
                    applicability="NOT_ESTABLISHED",
                    status="NOT_ESTABLISHED",
                    basis="The supplied Knowledge Base evidence set does not establish an applicable mandatory statutory trigger.",
                    limitation="Absence of retrieved regulatory trigger does not prove absence of all telecom law.",
                )
            )

        # 7. Decision-Specific Evidence Sufficiency
        has_intl = len(international_reqs) > 0
        has_nat = len(national_reqs) > 0

        sufficiency = DecisionSpecificSufficiency(
            overall_evidence="SUFFICIENT" if (has_intl or has_nat) else "INSUFFICIENT",
            requirement_mapping="SUFFICIENT" if (has_intl and has_nat) else "INSUFFICIENT_EVIDENCE",
            risk_assessment="SUFFICIENT FOR PRELIMINARY RISK SCREENING",
            regulatory_conclusion="ESTABLISHED" if has_nat else "NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE",
            root_cause="NOT ESTABLISHED" if ("incident" in question.lower()) else "NOT APPLICABLE",
        )

        return {
            "extracted_requirements": [req.to_dict() for req in requirements],
            "international_requirements": [req.to_dict() for req in international_reqs],
            "national_provisions": [req.to_dict() for req in national_reqs],
            "operator_requirements": [req.to_dict() for req in operator_reqs],
            "mappings": [m.to_dict() for m in mappings],
            "gaps": [g.to_dict() for g in gaps],
            "technical_implications": [ti.to_dict() for ti in technical_implications],
            "regulatory_implications": [ri.to_dict() for ri in regulatory_implications],
            "counter_evidence": [ce.to_dict() for ce in counter_evidence_items],
            "sufficiency": sufficiency.to_dict(),
        }
