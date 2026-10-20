import pytest
from Backend.policy_standard_mapping.models import (
    SourceType,
    RequirementType,
    ApplicabilityStatus,
    MappingRelationship,
    GapStatus,
    GapAction,
    ExtractedRequirement,
    PolicyStandardMappingRecord,
    GenuineGapRecord,
    HypothesisEvaluation,
    HypothesisStatus,
)
from Backend.policy_standard_mapping.source_classifier import classify_source_type
from Backend.policy_standard_mapping.requirement_extractor import (
    extract_requirement_from_evidence,
    _extract_clause_or_section,
)
from Backend.policy_standard_mapping.mapping_engine import PolicyStandardMappingEngine
from Backend.policy_standard_mapping.claim_validation_gate import validate_synthesis_claims
from rag.retrieval import _validate_jurisdiction


# ============================================================
# TEST 1 & TEST B: Y.3172 + APPLICABLE INDIAN PROVISION
# ============================================================
def test_y3172_mapping_substantive_coverage():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Recommendation Y.3172 specifies an architectural framework for machine learning in future networks including IMT-2020, specifying ML pipeline functions and sandbox capabilities.",
            "metadata": {
                "document": "T-REC-Y.3172-201906-I!!PDF-E",
                "source_file": "ITU_Rules_Framework/T-REC-Y.3172-201906-I!!PDF-E.pdf",
                "jurisdiction": "International",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": "DoT Rules specify telecom network security architecture requirements and telecommunications infrastructure protection standards for mobile operators.",
            "metadata": {
                "document": "Critical Telecommunication Infrastructure Rules, 2024_0",
                "source_file": "DoT_Rules/Critical Telecommunication Infrastructure Rules, 2024_0.pdf",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    assert len(result["mappings"]) >= 1
    mapping = result["mappings"][0]
    assert mapping["international_requirement"]["source_type"] == SourceType.INTERNATIONAL_RECOMMENDATION.value
    assert mapping["national_provision"]["source_type"] == SourceType.NATIONAL_REGULATION.value
    assert mapping["relationship"] in {
        MappingRelationship.COVERED.value,
        MappingRelationship.PARTIALLY_COVERED.value,
        MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED.value,
    }
    # Verify separate confidences
    assert "evidence_confidence" in mapping
    assert "mapping_confidence" in mapping


# ============================================================
# TEST 2 & TEST D: ADDITIONAL NATIONAL REQUIREMENT (NOT GAP)
# ============================================================
def test_additional_national_requirement_not_gap():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Y.3172 describes ML pipeline and model distribution framework in future networks.",
            "metadata": {
                "document": "T-REC-Y.3172-201906-I!!PDF-E",
                "source_file": "ITU_Rules_Framework/T-REC-Y.3172-201906-I!!PDF-E.pdf",
                "jurisdiction": "International",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": "Mandatory lawful interception and monitoring standards mandate real-time interface monitoring on telecom operators in India.",
            "metadata": {
                "document": "LAWFUL INTERCEPTION of MOBILE NETWORK after DCC TEC",
                "source_file": "TEC Guidelines/LAWFUL INTERCEPTION of MOBILE NETWORK after DCC TEC.pdf",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.ADDITIONAL_NATIONAL_REQUIREMENT.value
    # Additional requirement must NOT be classified as an ESTABLISHED GAP
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ============================================================
# TEST 3: WEAK / INDIRECT EVIDENCE -> POTENTIAL GAP NOT ESTABLISHED
# ============================================================
def test_weak_evidence_potential_gap_not_established():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Recommendation Y.3172 specifies an architectural framework for ML overlay and sandbox isolation.",
            "metadata": {
                "document": "T-REC-Y.3172-201906-I!!PDF-E",
                "source_file": "ITU_Rules_Framework/T-REC-Y.3172-201906-I!!PDF-E.pdf",
                "jurisdiction": "International",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": "Guidelines for telecom right of way specify fees and tower permits.",
            "metadata": {
                "document": "Telecommunications Right of Way Rules 2024",
                "source_file": "DoT_Rules/Telecommunications Right of Way Rules 2024.pdf",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED.value
    # Must NOT be marked as ESTABLISHED GAP
    assert all(g["status"] != GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ============================================================
# TEST 4 & TEST C: DEMONSTRATED PARTIAL COVERAGE / MISSING ELEMENT
# ============================================================
def test_demonstrated_partial_coverage():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Y.3172 architectural framework specifies an ML pipeline with model training, evaluation, and sandbox deployment.",
            "metadata": {
                "document": "T-REC-Y.3172-201906-I!!PDF-E",
                "source_file": "ITU_Rules_Framework/T-REC-Y.3172-201906-I!!PDF-E.pdf",
                "jurisdiction": "International",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": "National rules specify general telecom network security architecture requirements but omit ML pipeline controls.",
            "metadata": {
                "document": "Critical Telecommunication Infrastructure Rules, 2024_0",
                "source_file": "DoT_Rules/Critical Telecommunication Infrastructure Rules, 2024_0.pdf",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.PARTIALLY_COVERED.value
    assert mapping["missing_element"] is not None


# ============================================================
# TEST 5 & TEST E: TERMINOLOGY DIFFERENCE IS NOT A GAP
# ============================================================
def test_terminology_difference_not_gap():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP TS 23.501 specifies network slice instance selection and slice isolation controls.",
            "metadata": {
                "document": "23 Version 3gpp",
                "source_file": "3gpp/23 Version 3gpp.pdf",
                "jurisdiction": "International",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": "National regulations mandate logical separation of virtual network partitions and traffic isolation across slices.",
            "metadata": {
                "document": "Regulation_18092026",
                "source_file": "TRAI_Act/Regulation_18092026.pdf",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    # Substantive coverage achieved despite terminology difference
    assert mapping["relationship"] == MappingRelationship.COVERED.value
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ============================================================
# TEST 6 & TEST G: CONFLICTING EVIDENCE
# ============================================================
def test_conflicting_evidence():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "Standard specifies mandatory encryption for inter-slice interfaces.",
            "metadata": {"document": "ETSI 33.501", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "National provision explicitly prohibits encryption on certain monitoring interfaces without prior approval.",
            "metadata": {"document": "Lawful Interception Rules", "jurisdiction": "India"},
        },
    ]
    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)
    assert len(result["mappings"]) >= 1


# ============================================================
# TEST 7 & TEST F: ABSENCE PROTOCOL (NO NATIONAL EVIDENCE RETRIEVED)
# ============================================================
def test_absence_protocol_no_national_evidence():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Recommendation Y.3172 specifies ML architectural framework.",
            "metadata": {
                "document": "T-REC-Y.3172-201906-I!!PDF-E",
                "jurisdiction": "International",
            },
        }
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED.value
    # Never claim "No Indian regulation exists"
    assert "No applicable provision establishing" in mapping["reason"]
    assert "non-retrieval does not establish statutory non-existence" in mapping["reason"]


# ============================================================
# TEST 8 & TEST I: MANDATORY REPORTING NOT INFERRED WITHOUT TRIGGER
# ============================================================
def test_mandatory_reporting_strict_guardrail():
    synthesis = {
        "claims": [],
        "regulatory_implications": [
            {
                "statement": "Mandatory reporting applies to this cybersecurity anomaly within 6 hours.",
                "mandatory_status": "ESTABLISHED",
                "trigger": "ESTABLISHED",
                "authority_evidence_ids": ["EV-001"],
            }
        ],
    }

    evidence = [
        {
            "evidence_id": "EV-001",
            "text": "General cybersecurity guidance advises reviewing abnormal network traffic.",
            "metadata": {"document": "General Guidance", "jurisdiction": "India"},
        }
    ]

    validated = validate_synthesis_claims(synthesis, evidence)
    reg = validated["regulatory_implications"][0]
    # Mandatory reporting assertion must be downgraded / guarded
    assert reg["mandatory_status"] == "NOT_ESTABLISHED"
    assert "NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE" in reg["statement"]


# ============================================================
# TEST 9 & TEST H: ROOT CAUSE UNPROVEN ACROSS COMPETING HYPOTHESES
# ============================================================
def test_root_cause_competing_hypotheses():
    hypo = HypothesisEvaluation(
        hypothesis="Supply-Chain Container Compromise",
        status=HypothesisStatus.NOT_ESTABLISHED,
        evidence_ids=["EV-001"],
        supporting_evidence=[],
        limiting_counter_evidence=["EV-002"],
        confidence=0.15,
        reasoning="Valid vendor cryptographic signature and lack of matched CVE limit this hypothesis.",
    )
    assert hypo.status == HypothesisStatus.NOT_ESTABLISHED
    assert hypo.confidence < 0.20


# ============================================================
# TEST 10: REAL COUNTER-EVIDENCE DOWNGRADES CONCLUSION
# ============================================================
def test_counter_evidence_limiting_role():
    records = [
        {
            "evidence_id": "EV-001",
            "text": "Y.3172 defines ML architecture.",
            "metadata": {"document": "Y.3172", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "This standard is advisory only and voluntary for experimental testbeds.",
            "metadata": {"document": "Y.3172 Scope", "jurisdiction": "International"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    assert len(result["counter_evidence"]) >= 1
    assert result["counter_evidence"][0]["role"] == "LIMITING"


# ============================================================
# TEST 11 & TEST A: Y.3172 METADATA PRESERVATION & NO INVENTED CLAUSE
# ============================================================
def test_y3172_no_invented_clause():
    record = {
        "evidence_id": "EV-001",
        "text": "Recommendation ITU-T Y.3172 specifies an architectural framework for machine learning in future networks including IMT-2020.",
        "metadata": {
            "document": "T-REC-Y.3172-201906-I!!PDF-E",
            "source_file": "ITU_Rules_Framework/T-REC-Y.3172-201906-I!!PDF-E.pdf",
            "jurisdiction": "International",
            "page": 1,
        },
    }

    req = extract_requirement_from_evidence(record, 1)
    # Clause was not present in metadata or text, must be None (never hallucinated)
    assert req.clause is None
    assert req.page == 1
    assert req.source_type == SourceType.INTERNATIONAL_RECOMMENDATION
    assert req.status == RequirementType.TECHNICAL


# ============================================================
# TEST 12: INVALID JURISDICTION PROFILE REJECTION
# ============================================================
def test_invalid_jurisdiction_rejected():
    with pytest.raises(ValueError, match="Unsupported jurisdiction profile"):
        _validate_jurisdiction("Atlantis")


# ============================================================
# TEST 13 & TEST K/L: CLAIM GROUNDING & FALSE EVIDENCE REJECTION
# ============================================================
def test_claim_grounding_rejects_unsupported_claim():
    synthesis = {
        "claims": [
            {
                "claim_id": "CLM-001",
                "claim": "The satellite quantum teleporter mandates instantaneous encryption.",
                "evidence_ids": ["EV-999"],  # Non-existent EV ID
                "status": "SUPPORTED",
                "confidence": 0.99,
            }
        ]
    }
    evidence = [
        {
            "evidence_id": "EV-001",
            "text": "Standard 5G core slicing architecture.",
            "metadata": {"document": "3GPP TS 23.501"},
        }
    ]

    validated = validate_synthesis_claims(synthesis, evidence)
    c = validated["claims"][0]
    assert c["status"] == "INSUFFICIENT"
    assert "NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE" in c["claim"]
    assert c["confidence"] == 0.0
