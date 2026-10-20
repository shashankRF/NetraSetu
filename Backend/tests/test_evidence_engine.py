from Backend.evidence_engine.models import (
    Applicability,
    ClaimAssessment,
    EvidenceItem,
    EvidenceMetadata,
    EvidenceRole,
    EvidenceStatus,
    EvidenceStrength,
    RequirementType,
)

from Backend.evidence_engine.engine import EvidenceEngine


def test_supporting_evidence():
    evidence = EvidenceItem(
        evidence_id="EV-001",
        claim_id="CL-001",
        claim_text="Example security requirement applies.",
        evidence_text="The authority requires the specified security control.",
        role=EvidenceRole.SUPPORTING,
        strength=EvidenceStrength.STRONG,
        applicability=Applicability.DIRECT,
        requirement_type=RequirementType.MANDATORY,
        metadata=EvidenceMetadata(
            document="Example Regulation",
            publisher="Example Authority",
            source_type="NATIONAL_REGULATION",
            jurisdiction="INDIA",
            page=10,
            clause="5.2",
            chunk_id=100,
            retrieval_rank=1,
        ),
        confidence=0.95,
    )

    claim = ClaimAssessment(
        claim_id="CL-001",
        claim_text="Example security requirement applies.",
        supporting=[evidence],
        status=EvidenceStatus.SUFFICIENT,
        applicability=Applicability.DIRECT,
        confidence=0.95,
    )

    result = EvidenceEngine().assess([claim])

    assert result.supporting_count == 1
    assert result.contradicting_count == 0
    assert result.overall_status == EvidenceStatus.SUFFICIENT
    assert result.overall_strength == EvidenceStrength.STRONG
    assert result.overall_confidence == 0.90


def test_conflicting_evidence():
    supporting = EvidenceItem(
        evidence_id="EV-002",
        claim_id="CL-002",
        claim_text="Requirement applies.",
        evidence_text="Source A supports the requirement.",
        role=EvidenceRole.SUPPORTING,
        strength=EvidenceStrength.STRONG,
        applicability=Applicability.DIRECT,
        requirement_type=RequirementType.MANDATORY,
        metadata=EvidenceMetadata(
            document="Source A",
            publisher="Authority A",
            source_type="NATIONAL_REGULATION",
            jurisdiction="INDIA",
            page=20,
            chunk_id=200,
            retrieval_rank=1,
        ),
        confidence=0.90,
    )

    contradicting = EvidenceItem(
        evidence_id="EV-003",
        claim_id="CL-002",
        claim_text="Requirement applies.",
        evidence_text="Source B limits or contradicts applicability.",
        role=EvidenceRole.CONTRADICTING,
        strength=EvidenceStrength.MODERATE,
        applicability=Applicability.PARTIAL,
        requirement_type=RequirementType.MANDATORY,
        metadata=EvidenceMetadata(
            document="Source B",
            publisher="Authority B",
            source_type="OFFICIAL_GUIDANCE",
            jurisdiction="INDIA",
            page=30,
            chunk_id=300,
            retrieval_rank=2,
        ),
        confidence=0.75,
    )

    claim = ClaimAssessment(
        claim_id="CL-002",
        claim_text="Requirement applies.",
        supporting=[supporting],
        contradicting=[contradicting],
        status=EvidenceStatus.CONFLICTING,
        applicability=Applicability.UNCERTAIN,
        confidence=0.60,
    )

    result = EvidenceEngine().assess([claim])

    assert result.supporting_count == 1
    assert result.contradicting_count == 1
    assert result.overall_status == EvidenceStatus.CONFLICTING
    assert (
        "Conflicting evidence requires resolution."
        in result.missing_evidence
    )


def test_insufficient_evidence():
    claim = ClaimAssessment(
        claim_id="CL-003",
        claim_text="Unverified requirement.",
        status=EvidenceStatus.INSUFFICIENT,
        applicability=Applicability.NOT_ESTABLISHED,
        confidence=0.20,
    )

    result = EvidenceEngine().assess([claim])

    assert result.supporting_count == 0
    assert result.contradicting_count == 0
    assert result.overall_status == EvidenceStatus.INSUFFICIENT
    assert result.overall_strength == EvidenceStrength.INSUFFICIENT
    assert result.overall_confidence == 0.20


def test_evidence_metadata_is_preserved():
    metadata = EvidenceMetadata(
        document="Principal Telecommunication Services Rules",
        publisher="Department of Telecommunications",
        source_type="NATIONAL_REGULATION",
        jurisdiction="INDIA",
        page=126,
        section="Traffic Segregation",
        clause="X",
        chunk_id=8421,
        retrieval_rank=2,
        version="2026",
    )

    assert metadata.document == (
        "Principal Telecommunication Services Rules"
    )
    assert metadata.publisher == (
        "Department of Telecommunications"
    )
    assert metadata.jurisdiction == "INDIA"
    assert metadata.page == 126
    assert metadata.chunk_id == 8421
    assert metadata.retrieval_rank == 2
    assert metadata.version == "2026"