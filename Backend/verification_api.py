from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .evidence_engine.clause_verifier import (
    verify_claim_evidence,
    VerificationStatus,
)
from .evidence_engine.document_registry import (
    DOCUMENT_REGISTRY,
    resolve_document_metadata,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

router = APIRouter(
    tags=["Source-to-Clause Verification"],
)


class VerifyClaimRequest(BaseModel):
    claim: str
    clause: Optional[str] = None
    document: Optional[str] = None
    page: Optional[int] = None
    evidence_id: Optional[str] = None
    deliberate_clause_override: Optional[str] = None


def resolve_document_file(doc_path: str) -> Optional[Path]:
    """
    Safely resolve a local document path across knowledge_base, Documents main,
    canonical DOCUMENT_REGISTRY metadata, and all indexed folders.
    Supports resolving by:
    - Relative/absolute filesystem path (with or without knowledge_base prefix)
    - Document ID (e.g. CERTIN-DIR-2022, DOT-TELECOM-ACT-2023)
    - Document title or abbreviation (e.g. "Directions under Section 70B", "DPDP Act")
    - Raw filename (e.g. CERT-In_Directions_70B_28.04.2022.pdf)
    """
    import urllib.parse
    if not doc_path:
        return None

    # Strip query parameters or page hashes if accidentally passed
    clean_raw = str(doc_path).split("#")[0].split("?")[0].strip()
    clean_unquoted = urllib.parse.unquote(clean_raw).strip()

    # Normalize paths
    candidates_to_test = []
    for test_str in [clean_unquoted, clean_raw]:
        norm = os.path.normpath(test_str).replace("\\", "/").lstrip("/")
        if norm and norm not in candidates_to_test:
            candidates_to_test.append(norm)

    # 1. Check if the identifier matches a registered document in DOCUMENT_REGISTRY
    for test_key in [clean_unquoted, clean_raw]:
        meta = resolve_document_metadata(test_key)
        if meta and meta.local_path:
            meta_path = os.path.normpath(meta.local_path).replace("\\", "/").lstrip("/")
            if meta_path not in candidates_to_test:
                candidates_to_test.insert(0, meta_path)

    # 2. Test candidate paths against project root and knowledge base
    for cand_str in candidates_to_test:
        paths_to_check = [
            PROJECT_ROOT / cand_str,
            PROJECT_ROOT / "knowledge_base" / cand_str,
            PROJECT_ROOT / "knowledge_base" / "Documents main" / cand_str,
        ]
        if cand_str.startswith("knowledge_base/"):
            sub = cand_str[len("knowledge_base/"):]
            paths_to_check.append(PROJECT_ROOT / "knowledge_base" / "Documents main" / sub)

        # Space/underscore variations
        if "_" in cand_str:
            with_space = cand_str.replace("_", " ")
            paths_to_check.append(PROJECT_ROOT / with_space)
            paths_to_check.append(PROJECT_ROOT / "knowledge_base" / with_space)
            paths_to_check.append(PROJECT_ROOT / "knowledge_base" / "Documents main" / with_space)
        if " " in cand_str:
            with_underscore = cand_str.replace(" ", "_")
            paths_to_check.append(PROJECT_ROOT / with_underscore)
            paths_to_check.append(PROJECT_ROOT / "knowledge_base" / with_underscore)
            paths_to_check.append(PROJECT_ROOT / "knowledge_base" / "Documents main" / with_underscore)

        for p in paths_to_check:
            try:
                resolved = p.resolve()
                if str(resolved).startswith(str(PROJECT_ROOT.resolve())) and resolved.is_file():
                    return resolved
            except Exception:
                continue

    # 3. Fallback: Search by filename in knowledge_base directory
    for test_str in candidates_to_test:
        fname = Path(test_str).name
        if fname and fname.lower().endswith((".pdf", ".txt", ".json")):
            matches = list((PROJECT_ROOT / "knowledge_base").rglob(fname))
            if matches and matches[0].is_file():
                res = matches[0].resolve()
                if str(res).startswith(str(PROJECT_ROOT.resolve())):
                    return res
            # Also try space/underscore variations of filename
            if "_" in fname:
                matches_space = list((PROJECT_ROOT / "knowledge_base").rglob(fname.replace("_", " ")))
                if matches_space and matches_space[0].is_file():
                    return matches_space[0].resolve()
            if " " in fname:
                matches_under = list((PROJECT_ROOT / "knowledge_base").rglob(fname.replace(" ", "_")))
                if matches_under and matches_under[0].is_file():
                    return matches_under[0].resolve()

    return None


@router.get("/api/documents/info")
def get_document_file_info(
    doc_path: str,
    page: Optional[int] = None,
):
    """
    Check document availability and validate page navigation indices.
    """
    resolved = resolve_document_file(doc_path)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"Source document '{doc_path}' not found in knowledge base.",
        )

    total_pages = 1
    if resolved.suffix.lower() == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(resolved))
            total_pages = len(reader.pages)
        except Exception:
            total_pages = 1

    valid_page = True
    page_error = None
    if page is not None:
        if page < 1:
            valid_page = False
            page_error = f"Invalid page number {page}. Document pages are 1-based (minimum 1)."
        elif page > total_pages:
            valid_page = False
            page_error = f"Invalid page number {page}. Document has {total_pages} total pages."

    return {
        "status": "AVAILABLE",
        "document_name": resolved.name,
        "resolved_path": str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "total_pages": total_pages,
        "requested_page": page,
        "valid_page": valid_page,
        "page_error": page_error,
    }


@router.get("/api/documents/raw/{doc_path:path}")
def get_raw_document(
    doc_path: str,
    page: Optional[int] = None,
):
    """
    Safely stream local knowledge base document (PDF or text)
    with inline disposition to support browser document viewer.
    Validates page numbers and returns appropriate headers.
    """
    resolved = resolve_document_file(doc_path)

    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"Document file '{doc_path}' not found in knowledge base.",
        )

    total_pages = 1
    media_type = (
        "application/pdf"
        if str(resolved).lower().endswith(".pdf")
        else "text/plain; charset=utf-8"
    )

    if media_type == "application/pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(resolved))
            total_pages = len(reader.pages)
        except Exception:
            total_pages = 1

    headers = {
        "Content-Disposition": "inline",
        "Cache-Control": "public, max-age=3600",
        "X-Total-Pages": str(total_pages),
    }

    if page is not None:
        if page < 1 or page > total_pages:
            headers["X-Page-Warning"] = f"Requested page {page} out of bounds (1-{total_pages})"
        else:
            headers["X-Current-Page"] = str(page)

    return FileResponse(
        path=str(resolved),
        media_type=media_type,
        headers=headers,
    )


@router.get("/api/document_metadata")
def get_document_metadata_endpoint(
    doc_id: Optional[str] = None,
    query: Optional[str] = None,
):
    """
    Query official document registry metadata.
    """
    if doc_id:
        doc = DOCUMENT_REGISTRY.get(doc_id.upper())
        if doc:
            return doc.to_dict()

    if query:
        doc = resolve_document_metadata(query)
        if doc:
            return doc.to_dict()

    return {
        "count": len(DOCUMENT_REGISTRY),
        "documents": [d.to_dict() for d in DOCUMENT_REGISTRY.values()],
    }


@router.post("/api/verify_claim")
def verify_claim_endpoint(
    request: VerifyClaimRequest,
):
    """
    On-demand deterministic claim-to-clause verification.
    """
    mock_ev = []
    if request.document or request.evidence_id:
        mock_ev.append(
            {
                "title": request.document or "Source Document",
                "evidence_id": request.evidence_id or "EV-001",
                "text": request.claim,
                "provenance": {
                    "document": request.document,
                    "clause": request.clause,
                    "page": request.page,
                },
            }
        )

    record = verify_claim_evidence(
        claim=request.claim,
        evidence_records=mock_ev,
        deliberate_clause_override=(
            request.deliberate_clause_override or request.clause
        ),
    )

    return record.to_dict()
