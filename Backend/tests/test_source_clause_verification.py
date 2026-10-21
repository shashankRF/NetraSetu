from __future__ import annotations
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["NETRASETU_TESTING"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import pytest

from Backend.evidence_engine.clause_verifier import (
    verify_claim_evidence,
    VerificationStatus,
    extract_clause_and_page,
)
from Backend.evidence_engine.document_registry import (
    resolve_document_metadata,
    resolve_document_from_evidence,
    DOCUMENT_REGISTRY,
)
from Backend.demo_scenarios.library import get_scenario
from Backend.verification_api import (
    get_raw_document,
    get_document_metadata_endpoint,
    verify_claim_endpoint,
    VerifyClaimRequest,
)


def test_certin_valid_6hour_reporting():
    """
    Test Section 7 requirement: Test the six-hour reporting requirement under
    CERT-In Directions dated 28 April 2022, Para 2(ii).
    """
    claim = "Entities must mandatorily report cybersecurity incidents to CERT-In within 6 hours of noticing such incidents under Paragraph (ii) of the Directions dated 28 April 2022."

    mock_ev = [{
        "title": "Directions under section 70B(6) CERT-In",
        "evidence_id": "EV-001",
        "text": "report cyber incidents as mentioned in Annexure I to CERT-In within 6 (six) hours of noticing such incidents",
        "provenance": {
            "document": "CERT-In Directions 28 April 2022",
            "clause": "Paragraph (ii)",
            "page": 2,
            "jurisdiction": "India"
        }
    }]

    record = verify_claim_evidence(claim=claim, evidence_records=mock_ev, claim_id="CLM-CERT-01")

    # 1. Verification status
    # The source text is verbatim in the PDF; verification is specifically
    # reported as an exact citation match rather than a semantic assertion.
    assert record.verification_status == VerificationStatus.EXACT_MATCH_VERIFIED

    # 2. Document authority and metadata
    assert "CERT-In" in record.issuing_authority
    assert "20(3)/2022-CERT-In" in record.document_identifier
    assert record.jurisdiction == "India"
    assert record.legal_status == "BINDING_DIRECTION"

    # 3. Clause & Page
    assert record.clause.startswith("Paragraph (ii)")
    assert record.page == 2

    # 4. Official clickable URL & local viewer URL
    assert record.source_url == "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf"
    assert "page=2" in record.local_viewer_url

    # 5. Exact official wording preserved
    assert "within 6 (six) hours" in record.supporting_text

    # The FAQ PDF is not part of the retrieved evidence record, so its
    # clarification must not be added from registry notes alone.
    assert record.faq_clarification is None


def test_certin_clause_mismatch_deliberate_test():
    """
    Test deliberate test with an incorrect clause citation (Clause 12).
    NetraSetu must detect the mismatch rather than accept it merely because
    the document exists.
    """
    claim = "Under Clause 12 of the CERT-In Directions dated 28 April 2022, entities are required to report incidents within 6 hours."

    mock_ev = [{
        "title": "CERT-In Directions 2022",
        "evidence_id": "EV-002",
        "text": "Cyber incident reporting within 6 hours",
        "provenance": {
            "document": "CERT-In Directions 28 April 2022",
            "clause": "Clause 12",
            "page": 2
        }
    }]

    record = verify_claim_evidence(
        claim=claim,
        evidence_records=mock_ev,
        claim_id="CLM-MISMATCH-01",
        deliberate_clause_override="Clause 12"
    )

    # NetraSetu must detect the mismatch and reject
    assert record.verification_status == VerificationStatus.UNSUPPORTED
    assert record.relationship == "INCORRECT_CLAUSE_ATTRIBUTION"
    assert "CITATION MISMATCH DETECTED" in record.verification_explanation
    assert "Paragraph (ii)" in record.verification_explanation
    assert record.confidence == 0.0


def test_legal_vs_technical_source_distinction():
    """
    Test Section 5: Separate binding Indian legal requirements from technical
    standards. Do not present an ITU-T recommendation as an Indian statutory obligation.
    """
    claim = "Deployment of ML pipelines in telecom networks is a mandatory statutory obligation in India under ITU-T Recommendation Y.3172."

    mock_ev = [{
        "title": "ITU-T Recommendation Y.3172",
        "evidence_id": "EV-003",
        "text": "The machine learning pipeline in future networks comprises data collection and preprocessing.",
        "provenance": {
            "document": "ITU-T Y.3172",
            "clause": "Section 6",
            "page": 9,
            "jurisdiction": "International"
        }
    }]

    record = verify_claim_evidence(claim=claim, evidence_records=mock_ev)

    # Must flag legal status distinction
    assert record.verification_status == VerificationStatus.PARTIALLY_SUPPORTED
    assert record.legal_status == "INTERNATIONAL_RECOMMENDATION"
    assert record.relationship == "NON_BINDING_STANDARD_MISCLASSIFIED_AS_STATUTORY"
    assert "LEGAL STATUS DISTINCTION" in record.verification_explanation


def test_inaccessible_unindexed_source():
    """
    Test Section 6: If a source is inaccessible/unindexed, mark UNVERIFIED.
    Never pretend a clause was opened or verified.
    """
    claim = "The Global Satellite Code of 2099 mandates quantum encryption under Section 5."

    record = verify_claim_evidence(claim=claim, evidence_records=[])

    assert record.verification_status == VerificationStatus.UNVERIFIED
    assert record.source_doc_id == "UNKNOWN-DOC"
    assert record.confidence == 0.0
    assert "cannot be verified" in record.verification_explanation


def test_unsupported_claim():
    """
    Test Section 3 & 6: If cited passage does not establish claim, mark UNSUPPORTED.
    """
    claim = "All 5G base stations must contain quantum cryptographic chips manufactured exclusively in Bengaluru."

    mock_ev = [{
        "title": "3GPP TS 33.501 Security Architecture",
        "evidence_id": "EV-004",
        "text": "Network access security provides users with secure access to 5G services protecting against radio interface attacks.",
        "provenance": {
            "document": "3GPP TS 33.501",
            "clause": "Section 5",
            "page": 15
        }
    }]

    record = verify_claim_evidence(claim=claim, evidence_records=mock_ev)

    # The candidate passage cannot be verified verbatim in the cited PDF.
    # Under the no-guessing contract this remains unverified, not a fabricated
    # unsupported finding about a passage that was never established.
    assert record.verification_status == VerificationStatus.QUOTE_NOT_VERIFIED
    assert "could not be matched" in record.verification_explanation


def test_raw_document_serving_endpoint():
    """
    Test Section 1 & 2: Local document viewer endpoint streams official PDF with inline disposition.
    """
    resp = get_raw_document("knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf")
    assert resp.status_code == 200
    assert resp.media_type == "application/pdf"
    assert "inline" in resp.headers.get("Content-Disposition", "")
    assert Path(resp.path).is_file()


def test_document_metadata_endpoint():
    """
    Test API endpoint for querying document registry metadata.
    """
    data = get_document_metadata_endpoint(doc_id="CERTIN-DIR-2022")
    assert data["doc_id"] == "CERTIN-DIR-2022"
    assert "CERT-In" in data["issuing_authority"]
    assert "para_2_ii" in data["clauses"]


def test_verify_claim_endpoint():
    """
    Test API endpoint for on-demand claim-to-clause verification.
    """
    # 1. Valid test
    req_payload = VerifyClaimRequest(
        claim="Mandatory incident reporting to CERT-In within 6 hours",
        clause="Paragraph (ii)",
        document="CERT-In Directions 28 April 2022",
        page=2,
    )
    data = verify_claim_endpoint(req_payload)
    # A claim supplied as a request is not itself source evidence.
    assert data["verification_status"] == VerificationStatus.QUOTE_NOT_VERIFIED
    assert data["source_doc_id"] == "CERTIN-DIR-2022"

    # 2. Deliberate mismatch test
    mismatch_payload = VerifyClaimRequest(
        claim="Mandatory incident reporting to CERT-In within 6 hours under Clause 12",
        clause="Clause 12",
        document="CERT-In Directions 28 April 2022",
        page=2,
        deliberate_clause_override="Clause 12",
    )
    m_data = verify_claim_endpoint(mismatch_payload)
    # The request carries a claim and a citation but no independently retrieved
    # passage. The verifier must not treat the claim text as source evidence.
    assert m_data["verification_status"] == VerificationStatus.QUOTE_NOT_VERIFIED


def test_certin_demo_scenario_registered():
    """
    Test Section 7: Demonstration scenario registered and contains Steps C1 and C2.
    """
    scenario = get_scenario("HG-CERTIN-008")
    assert scenario is not None
    assert scenario["scenario_id"] == "HG-CERTIN-008"
    assert len(scenario["steps"]) == 2
    step_ids = [s["step_id"] for s in scenario["steps"]]
    assert "C1" in step_ids
    assert "C2" in step_ids




def test_it_act_rules_2000_0_resolution_and_content():
    """
    CRITICAL ACCEPTANCE CRITERIA:
    Verify the fix using the actual IT-Act-Rules_2000_0 evidence record.
    Confirm that the real source document opens on the cited page (p. 1)
    and that the displayed passage matches the source PDF.
    """
    from Backend.evidence_engine.document_registry import resolve_document_metadata, DOCUMENT_REGISTRY
    from Backend.verification_api import get_raw_document, get_document_file_info
    import pypdf

    # 1. Resolve metadata
    doc = resolve_document_metadata("IT-Act-Rules_2000_0")
    assert doc is not None
    assert doc.doc_id == "MEITY-IT-ACT-RULES-2000"
    assert "IT-Act-Rules_2000_0.pdf" in doc.local_path

    # 2. Check file info endpoint
    info = get_document_file_info("Indian_Acts/IT-Act-Rules_2000_0.pdf", page=1)
    assert info["status"] == "AVAILABLE"
    assert info["total_pages"] == 105
    assert info["requested_page"] == 1
    assert info["valid_page"] is True
    assert info["page_error"] is None

    # 3. Verify actual physical PDF file content on page 1
    pdf_path = PROJECT_ROOT / info["resolved_path"]
    assert pdf_path.is_file()
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 105
    page1_text = reader.pages[0].extract_text()
    assert "G.S.R 788 (E)" in page1_text or "G.S.R 789 (E)" in page1_text
    assert "Information Technology Act, 2000" in page1_text
    assert "October, 2000" in page1_text
    assert "Certifying Authorities" in page1_text

    # 4. Stream endpoint returns 200 with inline PDF disposition
    resp = get_raw_document("Indian_Acts/IT-Act-Rules_2000_0.pdf", page=1)
    assert resp.status_code == 200
    assert resp.media_type == "application/pdf"
    assert "inline" in resp.headers.get("Content-Disposition", "")
    assert resp.headers.get("X-Total-Pages") == "105"
    assert resp.headers.get("X-Current-Page") == "1"


def test_it_act_2000_updated_section_70b_page_mapping():
    """
    Verify page mapping for Information Technology Act, 2000 (as amended).
    Physical page 28 contains Section 70B (CERT-In incident response).
    """
    from Backend.verification_api import get_raw_document, get_document_file_info
    import pypdf

    info = get_document_file_info("Indian_Acts/it_act_2000_updated.pdf", page=28)
    assert info["status"] == "AVAILABLE"
    assert info["total_pages"] == 36
    assert info["valid_page"] is True

    pdf_path = PROJECT_ROOT / info["resolved_path"]
    reader = pypdf.PdfReader(str(pdf_path))
    page28_text = reader.pages[27].extract_text()  # 0-indexed page 27 is 1-indexed page 28
    assert "70B." in page28_text
    assert "Indian Computer Emergency Response Team" in page28_text

    resp = get_raw_document("Indian_Acts/it_act_2000_updated.pdf", page=28)
    assert resp.status_code == 200
    assert resp.headers.get("X-Current-Page") == "28"


def test_invalid_page_navigation():
    """
    Verify that out-of-bounds or invalid page numbers are detected visibly.
    """
    from Backend.verification_api import get_document_file_info, get_raw_document

    # Test page beyond total pages
    info_out_of_bounds = get_document_file_info("Indian_Acts/it_act_2000_updated.pdf", page=999)
    assert info_out_of_bounds["valid_page"] is False
    assert "Invalid page number 999" in info_out_of_bounds["page_error"]
    assert "Document has 36 total pages" in info_out_of_bounds["page_error"]

    # Test zero page number (pages are 1-based)
    info_zero = get_document_file_info("Indian_Acts/it_act_2000_updated.pdf", page=0)
    assert info_zero["valid_page"] is False
    assert "1-based" in info_zero["page_error"]

    # Stream headers reflect warning
    resp = get_raw_document("Indian_Acts/it_act_2000_updated.pdf", page=999)
    assert "X-Page-Warning" in resp.headers


def test_missing_source_file_produces_explicit_404():
    """
    Verify that requesting a missing source file produces an explicit HTTP 404,
    never returning a blank viewer or fabricated placeholder.
    """
    from fastapi import HTTPException
    import pytest
    from Backend.verification_api import get_raw_document, get_document_file_info

    with pytest.raises(HTTPException) as exc_info:
        get_raw_document("NonExistent_Regulatory_Document_999.pdf")
    assert exc_info.value.status_code == 404
    assert "not found in knowledge base" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info_info:
        get_document_file_info("NonExistent_Regulatory_Document_999.pdf")
    assert exc_info_info.value.status_code == 404
    assert "not found in knowledge base" in exc_info_info.value.detail



def test_certin_directions_70b_resolution_and_content():
    """
    ACCEPTANCE TEST: Trace and verify the exact document cited:
    - Title: Directions under Section 70B of IT Act 2000
    - Issuer: CERT-In, MeitY, Government of India
    - Citation: Annexure I, Page 1 (and 6-hour reporting mandate on Page 2)
    - Doc ID: CERTIN-DIR-2022
    Ensures that resolving by doc ID, title, or relative path succeeds with HTTP 200 application/pdf.
    """
    from Backend.evidence_engine.document_registry import resolve_document_metadata, DOCUMENT_REGISTRY
    from Backend.verification_api import get_raw_document, get_document_file_info
    import pypdf

    # 1. Resolve metadata by doc ID and by title
    doc_by_id = resolve_document_metadata("CERTIN-DIR-2022")
    assert doc_by_id is not None
    assert doc_by_id.doc_id == "CERTIN-DIR-2022"
    assert "CERT-In_Directions_70B_28.04.2022.pdf" in doc_by_id.local_path

    doc_by_title = resolve_document_metadata("Directions under Section 70B of IT Act 2000")
    assert doc_by_title is not None
    assert doc_by_title.doc_id == "CERTIN-DIR-2022"

    # 2. Query file info endpoint by doc_id
    info = get_document_file_info("CERTIN-DIR-2022", page=1)
    assert info["status"] == "AVAILABLE"
    assert info["total_pages"] == 3
    assert info["requested_page"] == 1
    assert info["valid_page"] is True
    assert info["page_error"] is None

    # 3. Stream raw PDF endpoint by doc_id
    resp = get_raw_document("CERTIN-DIR-2022", page=1)
    assert resp.status_code == 200
    assert resp.media_type == "application/pdf"
    assert "inline" in resp.headers.get("Content-Disposition", "")
    assert resp.headers.get("X-Total-Pages") == "3"
    assert resp.headers.get("X-Current-Page") == "1"

    # 4. Verify physical contents of PDF pages
    pdf_path = Path(resp.path)
    assert pdf_path.is_file()
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 3

    # Page 1: Subject / Section 70B directions
    p1_text = reader.pages[0].extract_text()
    assert "70B" in p1_text
    assert "CERT-In" in p1_text or "Indian Computer Emergency Response Team" in p1_text

    # Page 2: Mandatory 6-hour incident reporting mandate
    p2_text = reader.pages[1].extract_text()
    assert "6 hours" in p2_text.lower() or "six hours" in p2_text.lower()
    assert "incident" in p2_text.lower()

    # Page 3: Annexure I list of reportable incidents
    p3_text = reader.pages[2].extract_text()
    assert "Annexure" in p3_text or "ANNEXURE" in p3_text


def test_multi_document_source_resolution():
    """
    ACCEPTANCE TEST: Multiple indexed documents resolve to their own distinct source files.
    No document ID collision or fallback substitution is permitted.
    """
    from Backend.verification_api import get_raw_document, get_document_file_info

    docs_to_test = [
        ("CERTIN-DIR-2022", "CERT-In_Directions_70B_28.04.2022.pdf"),
        ("MEITY-DPDP-2023", "DPDP Act_2023.pdf"),
        ("DOT-TELECOM-ACT-2023", "new-telecom-Act-2023.pdf"),
        ("3GPP-TS-33501", "ETSI 33.501 Rel 18.pdf"),
        ("DOT-MTCTE-2023", "Testing and Certification MTCTE.pdf"),
    ]

    resolved_paths = set()
    for doc_id, expected_filename in docs_to_test:
        resp = get_raw_document(doc_id, page=1)
        assert resp.status_code == 200
        assert resp.media_type == "application/pdf"
        assert expected_filename in resp.path
        resolved_paths.add(resp.path)

    # All resolved paths must be distinct (no accidental aliasing)
    assert len(resolved_paths) == len(docs_to_test)


def test_invalid_doc_id_strict_404_no_fabrication():
    """
    ACCEPTANCE TEST: Invalid or fabricated document IDs return an explicit 404 error
    and never return a fallback or fabricated PDF.
    """
    from fastapi import HTTPException
    import pytest
    from Backend.verification_api import get_raw_document, get_document_file_info

    bogus_ids = [
        "NON-EXISTENT-REG-ID",
        "BOGUS_DOC_9999",
        "FAKE-DIRECTIVE-2099",
        "unknown/path/to/nothing.pdf",
    ]

    for bogus in bogus_ids:
        with pytest.raises(HTTPException) as exc_info:
            get_raw_document(bogus)
        assert exc_info.value.status_code == 404
        assert "not found in knowledge base" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info_info:
            get_document_file_info(bogus)
        assert exc_info_info.value.status_code == 404
        assert "not found in knowledge base" in exc_info_info.value.detail


if __name__ == "__main__":
    print("Running Source-to-Clause Verification Test Suite...")
    test_certin_valid_6hour_reporting()
    print("PASS: test_certin_valid_6hour_reporting")
    test_certin_clause_mismatch_deliberate_test()
    print("PASS: test_certin_clause_mismatch_deliberate_test")
    test_legal_vs_technical_source_distinction()
    print("PASS: test_legal_vs_technical_source_distinction")
    test_inaccessible_unindexed_source()
    print("PASS: test_inaccessible_unindexed_source")
    test_unsupported_claim()
    print("PASS: test_unsupported_claim")
    test_raw_document_serving_endpoint()
    print("PASS: test_raw_document_serving_endpoint")
    test_document_metadata_endpoint()
    print("PASS: test_document_metadata_endpoint")
    test_verify_claim_endpoint()
    print("PASS: test_verify_claim_endpoint")
    test_certin_demo_scenario_registered()
    print("PASS: test_certin_demo_scenario_registered")
    print("\nALL 9 SOURCE-TO-CLAUSE VERIFICATION TESTS PASSED SUCCESSFULLY!")
