import fitz

from Backend.evidence_engine.clause_verifier import LegalClauseParser, PDFSourceMatcher, VerificationStatus


def test_partial_prefix_match_does_not_verify_an_unmatched_passage(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Authority requires prompt incident reporting within six hours.")
    document.save(pdf_path)
    document.close()

    result = PDFSourceMatcher.match_quote_in_pdf(
        pdf_path,
        "Authority requires prompt incident reporting within six hours. It also imposes a network-slice isolation rule.",
    )

    assert result["matched"] is False
    assert result["match_type"] == VerificationStatus.QUOTE_NOT_VERIFIED
    assert result["exact_source_quote"] == ""


def test_complete_verbatim_passage_remains_verified(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    expected = "Authority requires prompt incident reporting within six hours."
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), expected)
    document.save(pdf_path)
    document.close()

    result = PDFSourceMatcher.match_quote_in_pdf(pdf_path, expected)

    assert result["matched"] is True
    assert result["match_type"] == VerificationStatus.EXACT_MATCH_VERIFIED
    assert expected in result["exact_source_quote"]
    assert result["source_line_numbers"]


def test_page_level_quote_does_not_inherit_previous_pages_rule():
    document = fitz.open()
    first = document.new_page()
    first.insert_text((72, 72), "10. An unrelated procedure step")
    second = document.new_page()
    second.insert_text((72, 72), "Continuation text without a clause heading.")

    hierarchy = LegalClauseParser.parse_clause_hierarchy(
        document,
        1,
        "Continuation text without a clause heading.",
    )

    assert hierarchy["rule_number"] is None
    assert hierarchy["rule_title"] is None
    assert hierarchy["full_clause_hierarchy"] == "General Provision"
    document.close()


def test_technical_decimal_clause_and_title_are_extracted_from_source():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "5.15.1 Network slice security requirements\nThe network slice shall use the required security controls.")

    hierarchy = LegalClauseParser.parse_clause_hierarchy(
        document,
        0,
        "The network slice shall use the required security controls.",
    )

    assert hierarchy["rule_number"] == "Clause 5.15.1"
    assert hierarchy["rule_title"] == "Network slice security requirements"
    assert hierarchy["full_clause_hierarchy"] == "Clause 5.15.1 - Network slice security requirements"
    document.close()
