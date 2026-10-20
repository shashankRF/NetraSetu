import pytest
from Backend.regional_comparative_gap import (
    JurisdictionRole,
    RegionalRelationshipType,
    RegionalGapStatus,
    RegionalActionType,
    RegionalComparativeGapEngine,
    format_regional_comparative_markdown,
    validate_regional_claims,
    get_relevant_regional_jurisdictions,
    assess_regional_kb_coverage,
)


def test_01_india_host_international_covered_no_gap():
    """TEST 1: India host + international requirement + Indian provision covers it -> NO ESTABLISHED GAP"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-01",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501 Rel 18",
            "text": "Network slice authentication and authorization must adhere to strict cryptographic isolation.",
        },
        {
            "id": "EV-IND-01",
            "jurisdiction": "India",
            "document": "TEC GR of gNodeB",
            "text": "The gNodeB must adhere to mandatory isolation and authentication controls satisfying international slice specifications.",
        },
    ]
    res = engine.compare(evidence, question="Is 5G slice isolation covered in India?")
    assert res.gap_status == RegionalGapStatus.NO_ESTABLISHED_GAP
    assert res.action == RegionalActionType.NO_ACTION
    assert res.coverage_status == "Covered"


def test_02_india_host_international_partially_covered():
    """TEST 2: India host + international requirement + Indian provision partially covers it -> PARTIALLY COVERED"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-02",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501 Rel 18",
            "text": "Network slice isolation requires explicit inter-slice cryptographic boundaries and logging.",
        },
        {
            "id": "EV-IND-02",
            "jurisdiction": "India",
            "document": "DoT Rules 2024",
            "text": "Licensees shall maintain general security and baseline security controls across network interfaces.",
        },
        {
            "id": "EV-REG-01",
            "jurisdiction": "Bangladesh",
            "document": "BTRC Telecom Security Guideline",
            "text": "Explicit slice isolation must be verified through third-party audits.",
        },
    ]
    res = engine.compare(evidence, question="Verify slice isolation requirements")
    assert res.gap_status == RegionalGapStatus.PARTIALLY_COVERED
    assert res.action == RegionalActionType.VERIFY
    assert "Regional comparative evidence identifies an explicit control" in res.reasoning
    assert "does NOT establish a legal requirement in India" in res.reasoning


def test_03_regional_has_explicit_provision_indian_insufficient():
    """TEST 3: India host + international requirement + regional country has explicit provision but Indian evidence is insufficient"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-03",
            "jurisdiction": "International",
            "document": "ITU-T Y.3172",
            "text": "Machine learning overlay architectures in 5G must enforce sandbox isolation.",
        },
        {
            "id": "EV-IND-03",
            "jurisdiction": "India",
            "document": "General Guidance Notice",
            "text": "Guidance only: Operators may explore AI telemetry with general security awareness.",
        },
        {
            "id": "EV-REG-02",
            "jurisdiction": "Singapore",
            "document": "IMDA Model AI Governance Framework",
            "text": "Mandatory sandbox isolation must be enforced for all autonomous ML pipelines.",
        },
    ]
    res = engine.compare(evidence, question="Is ML sandbox isolation required in India?")
    assert res.gap_status in {RegionalGapStatus.PARTIALLY_COVERED, RegionalGapStatus.POTENTIAL_GAP_NOT_ESTABLISHED}
    assert res.action == RegionalActionType.VERIFY
    assert res.human_review_required is True


def test_04_authoritative_indian_evidence_establishes_gap():
    """TEST 4: India host + international requirement + authoritative Indian evidence demonstrates relevant control is not adequately addressed -> ESTABLISHED GAP"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-04",
            "jurisdiction": "International",
            "document": "ETSI 33.501 Rel 18",
            "text": "Mandatory cryptographic token verification between distinct network slice instances.",
        },
        {
            "id": "EV-IND-04",
            "jurisdiction": "India",
            "document": "TEC Standards Gap Report",
            "text": "Token verification between distinct network slices is unaddressed in indian requirements; gap established.",
        },
    ]
    res = engine.compare(evidence, question="Does India have a gap in slice token verification?")
    assert res.gap_status == RegionalGapStatus.ESTABLISHED_GAP
    assert res.action == RegionalActionType.FIX
    assert res.coverage_status == "Uncovered"


def test_05_different_wording_same_substantive_control_not_a_gap():
    """TEST 5: Different wording but same substantive control -> NOT A GAP"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-05",
            "jurisdiction": "International",
            "document": "3GPP TS 23.501",
            "text": "Core network slice isolation requirement.",
        },
        {
            "id": "EV-IND-05",
            "jurisdiction": "India",
            "document": "TEC Technical Regulations",
            "text": "Telecommunication operators shall enforce access control partitioning and logical separation across subscriber domains.",
        },
    ]
    res = engine.compare(evidence, question="Is slice isolation missing in India?")
    assert res.gap_status == RegionalGapStatus.NOT_A_GAP
    assert res.action == RegionalActionType.NO_ACTION
    assert "Terminology Difference" in res.coverage_status


def test_06_regional_stricter_requirement_india_has_coverage():
    """TEST 6: Regional country has stricter requirement but India has adequate technical coverage -> NO ESTABLISHED GAP"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-06",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501",
            "text": "Baseline security mutual authentication between network functions.",
        },
        {
            "id": "EV-IND-06",
            "jurisdiction": "India",
            "document": "Critical Telecommunication Infrastructure Rules 2024",
            "text": "Mutual authentication is mandatory and strictly complied with for all network functions.",
        },
        {
            "id": "EV-REG-03",
            "jurisdiction": "Sri Lanka",
            "document": "TRCSL Stricter Cybersecurity Directive",
            "text": "Stricter mandatory isolation with 256-bit quantum-safe key exchange across all interfaces.",
        },
    ]
    res = engine.compare(evidence, question="Does India have a gap because Sri Lanka has stricter requirements?")
    assert res.gap_status == RegionalGapStatus.NO_ESTABLISHED_GAP
    assert res.action == RegionalActionType.NO_ACTION
    assert "additional regional control" in res.reasoning


def test_07_no_indian_evidence_retrieved_absence_not_established():
    """TEST 7: No Indian evidence retrieved -> ABSENCE NOT ESTABLISHED (NOT 'No Indian regulation exists.')"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-07",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501",
            "text": "User plane security ciphering integrity protection.",
        },
        {
            "id": "EV-REG-04",
            "jurisdiction": "Pakistan",
            "document": "PTA Telecommunication Security Framework",
            "text": "Mandatory user plane encryption.",
        },
    ]
    res = engine.compare(evidence, question="Does Indian law require user plane encryption?")
    assert res.gap_status == RegionalGapStatus.ABSENCE_NOT_ESTABLISHED
    assert res.action == RegionalActionType.INVESTIGATE
    assert "An applicable host-country provision was not established in the evidence examined" in res.reasoning
    assert "No Indian regulation exists" not in res.reasoning


def test_08_regional_evidence_conflicts_with_another_regional_source():
    """TEST 8: Regional evidence conflicts with another regional source -> CONFLICT / HUMAN REVIEW as appropriate"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-08",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501",
            "text": "Roaming interconnect security requirements.",
        },
        {
            "id": "EV-IND-08",
            "jurisdiction": "India",
            "document": "DoT License Conditions",
            "text": "General security safeguards shall be applied to international interconnects.",
        },
        {
            "id": "EV-REG-05A",
            "jurisdiction": "Nepal",
            "document": "NTA Telecom Directive",
            "text": "Interconnect encryption is mandatory and operators must strictly require IPsec tunnels.",
        },
        {
            "id": "EV-REG-05B",
            "jurisdiction": "Bhutan",
            "document": "BICMA Telecom Rule",
            "text": "Interconnect encryption is optional and alternative transport-level protections are permitted.",
        },
    ]
    res = engine.compare(evidence, question="Compare regional interconnect requirements")
    assert res.human_review_required is True
    assert len(res.counter_evidence_ids) >= 2
    assert "Regional evidence exhibits divergent implementations" in res.counter_evidence_summary


def test_09_foreign_requirement_not_treated_as_host_law_claim_gate():
    """TEST 9: Foreign requirement is mistakenly treated as Indian requirement -> GUARDRAIL REJECTS / SANITIZES"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    regional_res = engine.compare(
        evidence_records=[
            {
                "id": "EV-REG-09",
                "jurisdiction": "Bangladesh",
                "document": "BTRC Guideline",
                "text": "Explicit rule on logging.",
            }
        ],
        question="What does law require?",
    )

    bad_synthesis = {
        "claims": [
            "Bangladesh regulation is binding on India.",
            "India has no applicable laws regarding this topic.",
        ],
        "assessment": "No India regulation exists for this requirement.",
    }

    validated = validate_regional_claims(bad_synthesis, regional_analysis=regional_res.to_dict())

    # Verify both violations were neutralized
    assert "binding on India" not in validated["claims"][0]
    assert "NOT established by the supplied evidence" in validated["claims"][0]
    assert "No India regulation exists" not in validated["assessment"]
    assert "an applicable host-country provision was not established" in validated["assessment"]


def test_10_regional_evidence_comparative_only_invariant():
    """TEST 10: Regional evidence improves understanding but does not prove host gap -> COMPARATIVE EVIDENCE ONLY"""
    engine = RegionalComparativeGapEngine(host_jurisdiction="India")
    evidence = [
        {
            "id": "EV-INTL-10",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501",
            "text": "Slice isolation verification requirements.",
        },
        {
            "id": "EV-IND-10",
            "jurisdiction": "India",
            "document": "ITSAR 111102209",
            "text": "Network security general testing parameters.",
        },
        {
            "id": "EV-REG-10",
            "jurisdiction": "Sri Lanka",
            "document": "TRCSL Telecom Rule",
            "text": "Mandatory isolation testing.",
        },
    ]
    res = engine.compare(evidence)
    assert res.applicability["regional_comparative_only"] is True
    assert res.applicability["rule"] == "Regional evidence does NOT constitute India law."


def test_11_realistic_5g_network_slicing_comprehensive():
    """TEST 11 (Realistic 5G Test): Comprehensive evaluation matching Section 38 of task prompt."""
    question = (
        "A 5G operator in India is implementing network slicing for a critical service. "
        "International technical standards define security and isolation requirements. "
        "The compliance assessment indicates that some controls may not be explicitly addressed in Indian requirements. "
        "Examine India together with relevant regional jurisdictions and international standards. "
        "Determine which controls are covered, partially covered, additional, conflicting, or genuinely missing. "
        "Do not treat regional requirements as Indian law."
    )

    engine = RegionalComparativeGapEngine(host_jurisdiction="India", regional_mode="COMPARATIVE")
    evidence = [
        {
            "id": "EV-001",
            "jurisdiction": "International",
            "document": "3GPP TS 33.501 Rel 18",
            "text": "5G network slice isolation requires distinct cryptographic contexts, tenant separation, and mutual authentication.",
        },
        {
            "id": "EV-002",
            "jurisdiction": "India",
            "document": "Critical Telecommunication Infrastructure Rules 2024",
            "text": "Critical telecom networks must maintain baseline security controls and logical segmentation; specific slice cryptographic boundary controls are partially addressed.",
        },
        {
            "id": "EV-003",
            "jurisdiction": "Bangladesh",
            "document": "BTRC Telecom Security Regulation",
            "text": "Licensed 5G operators must implement explicit cryptographic slice isolation validated quarterly.",
        },
    ]

    res = engine.compare(evidence, question=question, domain="telecom")

    assert res.host_jurisdiction == "India"
    assert "Bangladesh" in res.regional_jurisdictions
    assert res.gap_status == RegionalGapStatus.PARTIALLY_COVERED
    assert res.action == RegionalActionType.VERIFY
    assert res.human_review_required is True

    # Check markdown formatting conforms to Sections 16 & 39
    md = format_regional_comparative_markdown(res)
    assert "### Regional Comparative Gap Analysis" in md
    assert "HOST:" in md
    assert "REGIONAL COMPARISON:" in md
    assert "INTERNATIONAL REQUIREMENT:" in md
    assert "HOST-COUNTRY COVERAGE:" in md
    assert "GAP STATUS:" in md
    assert "EVIDENCE:" in md
    assert "WHY:" in md
    assert "IMPACT:" in md
    assert "REMEDIATION:" in md
    assert "COUNTER-EVIDENCE:" in md
    assert "LIMITATION:" in md
