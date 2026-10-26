from Backend.evidence_engine.clause_verifier import (
    StructuredEvidenceRecord,
    VerificationStatus,
)


def _record(status, quote):
    return StructuredEvidenceRecord(
        claim_id="CLM-1",
        claim="Assess the emergency communications obligation.",
        source_doc_id="DOC-ITU-1",
        source_title="Emergency Telecommunications Recommendation",
        issuing_authority="ITU-T",
        document_identifier="ITU-T X.1234",
        version="2025 edition",
        publication_date="2025-01-01",
        effective_date="2025-01-01",
        jurisdiction="International",
        legal_status="INTERNATIONAL_RECOMMENDATION",
        clause="3(1)(a)",
        page=12,
        source_url="https://example.org/source.pdf",
        local_viewer_url="/api/documents/raw/ITU/source.pdf#page=12",
        supporting_text=quote,
        surrounding_context="Context from the verified page.",
        relationship="SUPPORTS",
        verification_status=status,
        verification_explanation="Compared with the source PDF passage.",
        rule_number="3",
        rule_title="Emergency communications",
        subrule_number="(1)",
        subclause_letter="(a)",
        full_clause_hierarchy="Rule 3(1)(a) — Emergency communications",
        viewer_page_number=12,
        exact_source_quote=quote,
        source_line_numbers=[18, 19],
        bounding_boxes=[{"x0": 10.0, "y0": 20.0, "x1": 100.0, "y1": 30.0}],
    )


def test_citation_contract_preserves_complete_verified_source_and_metadata():
    exact = "The complete first sentence. The complete second sentence; including its qualification."
    citation = _record(VerificationStatus.EXACT_MATCH_VERIFIED, exact).to_dict()["citation"]

    assert citation["document_name"] == "Emergency Telecommunications Recommendation"
    assert citation["document_id"] == "ITU-T X.1234"
    assert citation["clause"] == "Rule 3(1)(a) — Emergency communications"
    assert citation["rule_identifier"] == "3"
    assert citation["rule_title"] == "Emergency communications"
    assert citation["subclause"] == "(1)(a)"
    assert citation["page_number"] == 12
    assert citation["exact_statement"] == exact
    assert "..." not in citation["exact_statement"]
    assert citation["source_line_numbers"] == [18, 19]


def test_unverified_quote_is_not_exposed_as_an_exact_citation():
    citation = _record(
        VerificationStatus.QUOTE_NOT_VERIFIED,
        "A retrieved but unverified sentence.",
    ).to_dict()["citation"]

    assert citation["exact_statement"] == "Evidence not retrieved"
    assert citation["page_number"] == 12
    assert citation["verification_status"] == VerificationStatus.QUOTE_NOT_VERIFIED
