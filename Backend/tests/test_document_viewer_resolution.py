from __future__ import annotations

import fitz
import pytest
from fastapi.testclient import TestClient

from Backend import verification_api
from Backend.evidence_engine import document_registry
from Backend.server import app


@pytest.fixture
def registered_test_pdf(monkeypatch, tmp_path):
    root = tmp_path.resolve()
    pdf_dir = root / "knowledge_base" / "Documents main" / "TRAI_Act"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "Regulation_14052026.pdf"
    pdf = fitz.open()
    first = pdf.new_page()
    first.insert_text((72, 72), "NetraSetu synthetic citation fixture cover")
    second = pdf.new_page()
    second.insert_text((72, 72), "Rule 3(1)(a) requires resilient emergency communications.")
    second.insert_text((72, 100), "Context line following the cited clause.")
    pdf.save(pdf_path)
    pdf.close()
    monkeypatch.setattr(document_registry, "PROJECT_ROOT", root)
    monkeypatch.setattr(verification_api, "PROJECT_ROOT", root)
    monkeypatch.setenv("NETRASETU_ENV", "development")
    monkeypatch.setenv("NETRASETU_TESTING", "1")
    monkeypatch.delenv("NETRASETU_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("NETRASETU_ADMIN_PASSWORD", raising=False)
    return root, pdf_path


def _login(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200, response.text


def test_basename_without_pdf_suffix_resolves_to_registered_storage(registered_test_pdf):
    root, expected = registered_test_pdf
    resolved = verification_api.resolve_document_file("Regulation_14052026")
    assert resolved == expected
    assert resolved.is_relative_to(root / "knowledge_base")


def test_canonical_viewer_url_serves_pdf_ranges_and_maps_physical_page(registered_test_pdf):
    _, expected = registered_test_pdf
    client = TestClient(app)
    _login(client)
    raw = client.get("/api/documents/raw/Regulation_14052026", headers={"Range": "bytes=0-7"})
    assert raw.status_code == 206, raw.text
    assert raw.headers["content-type"].startswith("application/pdf")
    assert raw.content == b"%PDF-1.7"
    assert raw.headers.get("content-range", "").startswith("bytes 0-7/")

    info = client.get("/api/documents/info", params={
        "doc_path": "Regulation_14052026", "page": 2,
        "quote": "Rule 3(1)(a) requires resilient emergency communications.",
    })
    assert info.status_code == 200, info.text
    payload = info.json()
    assert payload["viewer_page_number"] == 2
    assert payload["pdf_page_number"] == 2
    assert payload["zero_based_pdf_page_index"] == 1
    assert payload["source_page_label"] == 2
    assert payload["canonical_document_id"].startswith("KB-")
    assert payload["storage_key"].endswith("Regulation_14052026.pdf")
    assert len(payload["content_sha256"]) == 64
    assert payload["verification_status"] == "EXACT_MATCH_VERIFIED"
    assert payload["bounding_boxes"]
    assert "Context line following" in payload["surrounding_context"]
    assert expected.name == payload["document_name"]

    preview = client.get("/api/documents/preview", params={
        "doc_path": "Regulation_14052026", "page": 2,
        "quote": "Rule 3(1)(a) requires resilient emergency communications.",
    })
    assert preview.status_code == 200, preview.text
    assert preview.headers["content-type"].startswith("image/png")
    assert preview.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_unknown_document_and_path_traversal_fail_without_leaking_paths(registered_test_pdf):
    _root, _expected = registered_test_pdf
    client = TestClient(app)
    _login(client)
    for identifier in ("unknown-document", "..%2F..%2F.env"):
        response = client.get("/api/documents/raw/" + identifier)
        assert response.status_code == 404
        assert "C:\\" not in response.text and "knowledge_base" not in response.text


def test_missing_registered_source_returns_structured_unavailable_status(registered_test_pdf):
    root, pdf_path = registered_test_pdf
    pdf_path.unlink()
    assert document_registry.find_local_document_path("Regulation_14052026") == ""
    client = TestClient(app)
    _login(client)
    response = client.get("/api/documents/info", params={"doc_path": "Regulation_14052026", "page": 2})
    assert response.status_code == 404
    assert response.json()["detail"] == "Source document not found in knowledge base."
    assert str(root) not in response.text

