from __future__ import annotations
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from .evidence_engine.clause_verifier import (
    verify_claim_evidence,
    VerificationStatus,
    PDFSourceMatcher,
    LegalClauseParser,
)
from .evidence_engine.document_registry import (
    DOCUMENT_REGISTRY,
    find_local_document_path,
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
    root = PROJECT_ROOT.resolve()
    approved_root = (root / "knowledge_base").resolve()

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
                if resolved.is_relative_to(approved_root) and resolved.is_file():
                    return resolved
            except Exception:
                continue

    # Canonical KB resolver handles indexed document basenames with a missing
    # .pdf suffix, while remaining restricted to a unique file in KB storage.
    resolved_path = find_local_document_path(clean_unquoted)
    if resolved_path:
        candidate = (root / resolved_path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file() and candidate.suffix.lower() == ".pdf":
            return candidate

    # 3. Fallback: Search by filename in knowledge_base directory
    for test_str in candidates_to_test:
        fname = Path(test_str).name
        if fname and fname.lower().endswith((".pdf", ".txt", ".json")):
            matches = list((PROJECT_ROOT / "knowledge_base").rglob(fname))
            if matches and matches[0].is_file():
                res = matches[0].resolve()
                if res.is_relative_to(approved_root):
                    return res
            # Also try space/underscore variations of filename
            if "_" in fname:
                matches_space = list((PROJECT_ROOT / "knowledge_base").rglob(fname.replace("_", " ")))
                if matches_space and matches_space[0].is_file():
                    resolved = matches_space[0].resolve()
                    if resolved.is_relative_to(approved_root):
                        return resolved
            if " " in fname:
                matches_under = list((PROJECT_ROOT / "knowledge_base").rglob(fname.replace(" ", "_")))
                if matches_under and matches_under[0].is_file():
                    resolved = matches_under[0].resolve()
                    if resolved.is_relative_to(approved_root):
                        return resolved

    return None


@router.get("/api/documents/info")
def get_document_file_info(
    doc_path: str,
    page: Optional[int] = None,
    quote: Optional[str] = None,
    q: Optional[str] = None,
):
    """
    Check document availability, validate page navigation indices,
    and resolve verbatim text matching, clause hierarchy, and bounding boxes.
    """
    resolved = resolve_document_file(doc_path)
    if not resolved:
        raise HTTPException(status_code=404, detail="Source document not found in knowledge base.")

    total_pages = 1
    is_pdf = resolved.suffix.lower() == ".pdf"
    if is_pdf:
        try:
            import fitz
            doc = fitz.open(str(resolved))
            total_pages = len(doc)
        except Exception:
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

    target_quote = quote or q or ""
    viewer_page = page or 1
    zero_page = max(0, viewer_page - 1)
    printed_page = viewer_page
    bounding_boxes = []
    clause_hierarchy = {
        "rule_number": None,
        "rule_title": None,
        "subrule_number": None,
        "clause_number": None,
        "subclause_letter": None,
        "full_clause_hierarchy": "General Provision",
    }


    match_status = "SUPPORTED" if not target_quote else "QUOTE_NOT_VERIFIED"
    exact_source_quote = ""

    if is_pdf and (target_quote or page is not None):
        try:
            import fitz
            doc = fitz.open(str(resolved))
            if target_quote:
                match_res = PDFSourceMatcher.match_quote_in_pdf(resolved, target_quote, preferred_page=page)
                if match_res["matched"]:
                    viewer_page = match_res["viewer_page_number"]
                    zero_page = match_res["zero_based_pdf_page_index"]
                    printed_page = match_res["printed_page_number"]
                    bounding_boxes = match_res["bounding_boxes"]
                    clause_hierarchy = match_res["clause_hierarchy"]
                    match_status = match_res["match_type"]
                    exact_source_quote = match_res["exact_source_quote"]
            elif 0 <= zero_page < len(doc):
                p_text = doc[zero_page].get_text()
                printed_page = LegalClauseParser.extract_printed_page(p_text, viewer_page)
                clause_hierarchy = LegalClauseParser.parse_clause_hierarchy(doc, zero_page)
        except Exception as e:
            import traceback
            traceback.print_exc()

    page_text = ""
    if is_pdf and 0 <= zero_page < total_pages:
        try:
            import fitz
            with fitz.open(str(resolved)) as context_doc:
                page_text = context_doc[zero_page].get_text("text").strip()
        except Exception:
            page_text = ""

    context = page_text
    if target_quote and page_text:
        idx = page_text.casefold().find(target_quote.casefold())
        if idx >= 0:
            context = page_text[max(0, idx - 500):min(len(page_text), idx + len(target_quote) + 500)]

    try:
        digest = hashlib.sha256()
        with resolved.open("rb") as source_file:
            for block in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(block)
        content_hash = digest.hexdigest()
    except OSError:
        content_hash = None
    relative_key = str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")
    registered_meta = resolve_document_metadata(doc_path) or resolve_document_metadata(resolved.name)
    stable_doc_id = registered_meta.doc_id if registered_meta else f"KB-{hashlib.sha256(relative_key.casefold().encode('utf-8')).hexdigest()[:16].upper()}"

    return {
        "status": "AVAILABLE" if valid_page else "PAGE_UNAVAILABLE",
        "canonical_document_id": stable_doc_id,
        "original_official_source_url": registered_meta.official_url if registered_meta else None,
        "storage_key": relative_key,
        "file_available": True,
        "availability_verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_sha256": content_hash,
        "document_name": resolved.name,
        "resolved_path": relative_key,
        "total_pages": total_pages,
        "requested_page": page,
        "valid_page": valid_page,
        "page_error": page_error,
        "viewer_page_number": viewer_page,
        "zero_based_pdf_page_index": zero_page,
        "pdf_page_number": viewer_page,
        "page_numbering_convention": "pdf_page_number is 1-based physical PDF page; zero_based_pdf_page_index is 0-based physical PDF page index; source_page_label is printed page label when extracted",
        "source_page_label": printed_page,
        "printed_page_number": printed_page,
        "exact_source_quote": exact_source_quote,
        "bounding_boxes": bounding_boxes,
        "source_line_numbers": match_res.get("source_line_numbers", []) if target_quote and "match_res" in locals() else [],
        "clause_hierarchy": clause_hierarchy,
        "verification_status": match_status,
        "surrounding_context": context,
        "source_context_status": "AVAILABLE" if context else "NOT_RETRIEVED",
    }


@router.get("/api/documents/preview")
def get_document_page_preview(
    doc_path: str,
    page: int = 1,
    quote: Optional[str] = None,
):
    """Render one PDF page and highlight an exact, source-matched passage."""
    resolved = resolve_document_file(doc_path)
    if not resolved or resolved.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF source was not retrieved.")
    try:
        import fitz
        doc = fitz.open(str(resolved))
        if page < 1 or page > len(doc):
            raise HTTPException(status_code=404, detail="Requested PDF page is unavailable.")
        pdf_page = doc[page - 1]
        if quote:
            match = PDFSourceMatcher.match_quote_in_pdf(resolved, quote, preferred_page=page)
            if match.get("matched") and match.get("viewer_page_number") == page:
                shape = pdf_page.new_shape()
                for rect in match.get("bounding_boxes", []):
                    shape.draw_rect(fitz.Rect(rect["x0"], rect["y0"], rect["x1"], rect["y1"]))
                shape.finish(color=(0.95, 0.18, 0.22), fill=(1.0, 0.25, 0.28), fill_opacity=0.22, width=1.8)
                shape.commit(overlay=True)
        pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(1.55, 1.55), alpha=False)
        return Response(
            content=pixmap.tobytes("png"),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not render source PDF page: {exc}")

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
