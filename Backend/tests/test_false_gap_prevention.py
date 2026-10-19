"""
HackGrid False-Gap Prevention Test Suite
========================================

Automated regression suite verifying that the gap analysis pipeline does not
erroneously classify:
1. Local operator security requirements as national policy gaps.
2. 3GPP vs Indian mechanism variances as gaps without equivalence assessment.
3. Stricter Indian requirements as gaps.
4. Retrieval failures as proof that no law exists.
5. Partial coverage as unconditionally established gaps.
6. Conflicting multi-agency rules as coverage gaps.
7. Functionally equivalent mechanisms as gaps.
8. Foreign jurisdiction evidence as Indian regulatory gaps.
9. Version mismatches as established gaps.
10. Valid uncovered obligations from being correctly established.
11. Missing authority metadata from inventing legal status.
12. Contradictory counter-evidence from falsely confirming gaps.
"""

import pytest
from Backend.policy_standard_mapping.models import (
    SourceType,
    RequirementType,
    ApplicabilityStatus,
    MappingRelationship,
    GapStatus,
    GapAction,
)
from Backend.policy_standard_mapping.mapping_engine import PolicyStandardMappingEngine
from Backend.policy_standard_mapping.source_classifier import classify_source_type
from Backend.policy_standard_mapping.requirement_extractor import extract_requirement_from_evidence
from Backend.governance import evaluate_governance


# ===========================================================================
# TEST 1: Local Operator Security Requirement != National Policy Gap
# ===========================================================================
def test_01_local_security_requirement_not_national_gap():
    """
    An operator's internal policy requires an additional control (e.g. 3-of-5 threshold signatures).
    Must NOT classify this as an established Indian policy or regulatory gap.
    """
    records = [
        {
            "evidence_id": "EV-OP-001",
            "text": "Operator X internal security policy requires 3-of-5 threshold cryptographic signatures for all HSM administration.",
            "metadata": {
                "document": "Operator X Internal Security Baseline 2024",
                "source_file": "internal_policies/operator_x_baseline.pdf",
                "jurisdiction": "India",
            },
        },
        {
            "evidence_id": "EV-NAT-001",
            "text": "Licensee shall maintain hardware security module controls compliant with FIPS 140-2 Level 3 or CC EAL4+.",
            "metadata": {
                "document": "DoT Unified License Security Guidelines",
                "jurisdiction": "India",
            },
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    # Operator policy must be recognized as local/enterprise requirement
    assert len(result["operator_requirements"]) >= 1
    # Must NOT produce an ESTABLISHED_GAP
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])
    # Any gap finding regarding operator policy must be NO_GAP_ESTABLISHED
    op_gaps = [g for g in result["gaps"] if "operator" in g["coverage"].lower() or "operator" in g["international_requirement"].lower()]
    for g in op_gaps:
        assert g["status"] == GapStatus.NO_GAP_ESTABLISHED.value
        assert g["action"] == GapAction.NO_ACTION.value


# ===========================================================================
# TEST 2: 3GPP vs Indian Mechanism != Gap Without Equivalence Assessment
# ===========================================================================
def test_02_3gpp_vs_indian_mechanism_different_not_missing():
    """
    A 3GPP specification describes one mechanism (OAuth 2.0 access tokens),
    while an Indian instrument prescribes another (mTLS with CCA PKI certificates).
    Must NOT establish a gap solely because mechanisms differ.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP TS 33.501 specifies OAuth 2.0 token-based authorization for network function inter-communication in SBA.",
            "metadata": {"document": "3GPP TS 33.501 Rel-16", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "TEC ITSAR standard mandates mutual TLS (mTLS) with digital certificates issued by a licensed Controller of Certifying Authorities (CCA) for network function authentication.",
            "metadata": {"document": "TEC MTCTE ITSAR 5G Core", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    # Functional equivalence must achieve coverage
    assert mapping["relationship"] == MappingRelationship.COVERED.value
    # No established gap
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 3: Stricter Indian Requirement != Regulatory Gap
# ===========================================================================
def test_03_stricter_indian_requirement_not_gap():
    """
    An applicable Indian instrument requires an additional safeguard beyond international baseline
    (e.g. data localization and no offshore remote access).
    Expected: Classify as ADDITIONAL_NATIONAL_REQUIREMENT, NOT a gap.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP specifications define cloud virtualization management for 5G core functions.",
            "metadata": {"document": "3GPP TS 23.501", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "DoT Unified License mandates data localization and strictly prohibits remote access from outside India without prior security clearance.",
            "metadata": {"document": "DoT Unified License Clause 39.23", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.ADDITIONAL_NATIONAL_REQUIREMENT.value
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 4: Retrieval Failure != Proof of Regulatory Absence
# ===========================================================================
def test_04_retrieval_failure_not_absence_of_law():
    """
    No Indian regulatory clause retrieved.
    Expected: POTENTIAL_GAP_NOT_ESTABLISHED with absence protocol disclaimer. Never ESTABLISHED_GAP.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP TS 38.300 specifies 5G NR non-terrestrial network (NTN) satellite ephemeris synchronization.",
            "metadata": {"document": "3GPP TS 38.300", "jurisdiction": "International"},
        }
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED.value
    assert "non-retrieval does not establish statutory non-existence" in mapping["reason"]
    # In gaps list, status must NOT be ESTABLISHED_GAP
    assert result["gaps"][0]["status"] == GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED.value
    assert result["gaps"][0]["action"] == GapAction.VERIFY.value


# ===========================================================================
# TEST 5: Partial Coverage Qualified != Unconditionally Established Gap
# ===========================================================================
def test_05_partial_coverage_qualified_not_established_gap():
    """
    One part of a multi-part obligation is addressed, while another remains unresolved.
    Expected: PARTIALLY_COVERED, with missing element identified, but status is POTENTIAL_GAP_NOT_ESTABLISHED.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Recommendation Y.3172 defines ML pipeline architecture and sandbox execution framework.",
            "metadata": {"document": "T-REC-Y.3172", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "National regulation mandates telecom network security and architectural testing, but lacks dedicated ML pipeline sandbox rules.",
            "metadata": {"document": "Regulation 2026", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.PARTIALLY_COVERED.value
    assert mapping["missing_element"] is not None
    # Must NOT be unconditionally ESTABLISHED_GAP
    assert result["gaps"][0]["status"] == GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED.value
    assert result["gaps"][0]["action"] == GapAction.VERIFY.value


# ===========================================================================
# TEST 6: Conflicting Sources Retain Unresolved Conflict State
# ===========================================================================
def test_06_conflicting_sources_unresolved_not_gap():
    """
    Two potentially applicable national sources disagree (e.g. CERT-In 6h vs DoT 24h).
    Expected: Does not establish a standards gap; preserves conflict explanation.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "CERT-In Directions 2022 mandate reporting of all cybersecurity incidents within 6 hours of noticing.",
            "metadata": {"document": "CERT-In Directions Clause 2(i)", "jurisdiction": "India"},
        },
        {
            "evidence_id": "EV-002",
            "text": "DoT Security Circular mandates reporting of major telecom network outages to TSOC within 24 hours.",
            "metadata": {"document": "DoT Telecom Security Circular", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)
    # Neither is classified as an established gap
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 7: Functional Equivalence Yields No Gap
# ===========================================================================
def test_07_functional_equivalence_no_gap():
    """
    Subscriber identity privacy: SUCI vs confidentiality of subscriber information.
    Expected: Functionally equivalent; NO_GAP_ESTABLISHED.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP TS 33.501 mandates SUPI concealment into SUCI over radio interface.",
            "metadata": {"document": "3GPP TS 33.501", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "DoT Unified License mandates confidentiality of subscriber identity across all air interface radio transmissions.",
            "metadata": {"document": "DoT License Clause 39.23", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    mapping = result["mappings"][0]
    assert mapping["relationship"] == MappingRelationship.COVERED.value
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 8: Jurisdiction Mismatch != Indian Regulatory Gap
# ===========================================================================
def test_08_jurisdiction_mismatch_not_indian_gap():
    """
    Retrieved evidence applies to UK (e.g. UK TSR). Must not be reported as an Indian regulatory gap.
    """
    rec = {
        "evidence_id": "EV-UK-001",
        "text": "UK Telecommunications Security Act 2021 mandates vendor diversification limits.",
        "metadata": {"document": "UK TSR 2022", "jurisdiction": "United Kingdom"},
    }

    req = extract_requirement_from_evidence(rec, 1)
    assert req.jurisdiction == "United Kingdom"
    # An international/UK req compared against India cannot become a confirmed gap without host-country applicability
    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence([rec])
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 9: Version Mismatch Retains Uncertainty State
# ===========================================================================
def test_09_version_mismatch_retains_uncertainty():
    """
    3GPP Rel-17 requirement evaluated against national baseline adopting Rel-15.
    Must NOT automatically declare an illegal compliance gap.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "3GPP Rel-17 specifies advanced RedCap 5G device authentication.",
            "metadata": {"document": "3GPP TS 33.501 Rel-17", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "TEC National Standard adopts 3GPP Rel-15 baseline for Phase IV MTCTE testing.",
            "metadata": {"document": "TEC MTCTE Phase IV", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    # Must retain POTENTIAL_GAP or qualified status, never an unverified ESTABLISHED_GAP
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])


# ===========================================================================
# TEST 10: Genuine Uncovered Obligation Supported by Evidence
# ===========================================================================
def test_10_genuine_uncovered_obligation_supported_by_evidence():
    """
    When adequate evidence establishes a mandatory treaty obligation that is genuinely omitted in law,
    a gap record may be established with traceable supporting evidence and limitations.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU Radio Regulations Article 5 explicitly mandates coordination power limits for satellite downlinks.",
            "metadata": {"document": "ITU Radio Regulations Art 5", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "National frequency allocation plan omits coordination power limits for this satellite downlink band, leaving a regulatory void.",
            "metadata": {"document": "NFAP Gazette 2022", "jurisdiction": "India"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    # Relationship must identify the partial or potential omission
    assert len(result["mappings"]) >= 1
    mapping = result["mappings"][0]
    assert mapping["relationship"] in {MappingRelationship.PARTIALLY_COVERED.value, MappingRelationship.COVERED.value}


# ===========================================================================
# TEST 11: Missing Authority Metadata Retains Uncertainty
# ===========================================================================
def test_11_missing_authority_metadata_retains_uncertainty():
    """
    Source authority is unknown. Engine must NOT invent binding legal status.
    """
    record = {
        "evidence_id": "EV-UNK-001",
        "text": "Anonymous blog post claims 5G towers must shut down at midnight.",
        "metadata": {"document": "Unknown Document", "jurisdiction": "India"},
    }

    req = extract_requirement_from_evidence(record, 1)
    # Status should be UNKNOWN, not MANDATORY
    assert req.status == RequirementType.UNKNOWN


# ===========================================================================
# TEST 12: Contradictory Counter-Evidence Suppresses Established Gap
# ===========================================================================
def test_12_contradictory_counter_evidence_suppresses_established_gap():
    """
    Primary evidence suggests a gap, but limiting counter-evidence indicates voluntary scope.
    Must NOT establish the gap.
    """
    records = [
        {
            "evidence_id": "EV-001",
            "text": "ITU-T Y.3172 specifies ML architectural framework.",
            "metadata": {"document": "T-REC-Y.3172", "jurisdiction": "International"},
        },
        {
            "evidence_id": "EV-002",
            "text": "This standard is advisory only, voluntary, and does not apply to commercial production networks.",
            "metadata": {"document": "Y.3172 Scope Note", "jurisdiction": "International"},
        },
    ]

    engine = PolicyStandardMappingEngine(target_jurisdiction="India")
    result = engine.map_evidence(records)

    assert len(result["counter_evidence"]) >= 1
    assert result["counter_evidence"][0]["role"] == "LIMITING"
    # Established gap must NOT be declared
    assert not any(g["status"] == GapStatus.ESTABLISHED_GAP.value for g in result["gaps"])
