from pathlib import Path

import pymupdf

from Backend.evidence_engine.document_registry import DOCUMENT_REGISTRY, find_local_document_path


def test_registry_titles_and_gazette_identifiers_follow_pdf_sources():
    cases = {
        "DOT-GMDSS-RULES-2024": ("G.S.R. 674(E)", "Global Maritime Distress and Safety System"),
        "DOT-MARITIME-FLIGHT-CONNECTIVITY-2022": ("G.S.R. 154(E)", "2022"),
        "DOT-CRITICAL-INFRA-2024": ("G.S.R. 723(E)", "Critical Telecommunication Infrastructure"),
        "DOT-MTCTE-2023": ("TEC 93009:2024", "Version 3.0"),
    }
    for doc_id, (identifier, title_fragment) in cases.items():
        entry = DOCUMENT_REGISTRY[doc_id]
        path = find_local_document_path(entry.local_path)
        assert path, f"Registered source is missing for {doc_id}"
        pdf = pymupdf.open(path)
        first_pages = " ".join(page.get_text() for page in list(pdf)[:4])
        assert title_fragment.casefold() in entry.title.casefold()
        assert identifier in entry.document_identifier
        if doc_id == "DOT-GMDSS-RULES-2024":
            assert entry.publication_date == "2024-10-29"
            assert "not retrieved" in entry.effective_date.casefold()
            assert entry.legal_status == "DRAFT_NOTIFICATION"
        if doc_id == "DOT-MARITIME-FLIGHT-CONNECTIVITY-2022":
            assert entry.publication_date == entry.effective_date == "2022-02-23"
        if doc_id == "DOT-CRITICAL-INFRA-2024":
            assert entry.publication_date == "2024-11-22"
            assert "not retrieved" in entry.effective_date.casefold()
            assert entry.legal_status == "DRAFT_NOTIFICATION"
        if doc_id != "DOT-MTCTE-2023":
            gazette_number = identifier.replace("G.S.R. ", "").split(",")[0].split("(")[0]
            assert gazette_number in first_pages


def test_registry_marks_missing_pdfs_as_unverified_instead_of_claiming_metadata():
    for doc_id in ("ITU-T-Y3172", "DGCA-DRONE-RULES-2021"):
        entry = DOCUMENT_REGISTRY[doc_id]
        assert not find_local_document_path(entry.local_path)
        assert "not found" in entry.title.casefold()
        assert "not retrieved" in entry.document_identifier.casefold()
        assert not entry.clauses, f"Unverified clause metadata must not be cited for {doc_id}"


def test_registry_does_not_expose_unverified_static_clause_assertions():
    # Source provisions must be obtained from and verified against the PDF at runtime.
    assert all(not entry.clauses for entry in DOCUMENT_REGISTRY.values())
