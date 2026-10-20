from __future__ import annotations

from typing import Any, Dict, List

from .models import EvidenceMetadata
from .document_registry import resolve_document_from_evidence


def build_evidence_metadata(
    result: Dict[str, Any],
    rank: int | None = None,
) -> EvidenceMetadata:
    """
    Convert an existing RAG retrieval result into the
    normalized EvidenceMetadata structure.

    Original provenance is preserved.
    """

    metadata = result.get("metadata", {}) or {}

    retrieval_rank = (
        rank
        if rank is not None
        else result.get("rank")
    )

    return EvidenceMetadata(
        document=metadata.get("document"),
        publisher=metadata.get("publisher"),
        source_type=(
            metadata.get("source_type")
            or metadata.get("document_type")
        ),
        jurisdiction=metadata.get("jurisdiction"),
        page=metadata.get("page"),
        section=metadata.get("section"),
        clause=metadata.get("clause"),
        chunk_id=metadata.get(
            "chunk_id",
            result.get("chunk_id"),
        ),
        retrieval_rank=retrieval_rank,
        version=metadata.get("version"),
        publication_date=metadata.get(
            "publication_date"
        ),
        effective_date=metadata.get(
            "effective_date"
        ),
        expiry_date=metadata.get(
            "expiry_date"
        ),
    )


def build_evidence_record(
    result: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """
    Convert one real RAG retrieval result into an
    audit-ready evidence record with clickable official
    source metadata and local document viewer support.
    """

    metadata = result.get("metadata", {}) or {}

    evidence_id = f"EV-{index:03d}"
    kb_name = result.get("kb") or metadata.get("kb") or "MAIN"
    title_str = metadata.get("document") or metadata.get("source_file") or result.get("title") or f"Record {index}"

    # Resolve official document metadata and links
    doc_meta = resolve_document_from_evidence(result)
    page_num = metadata.get("page")
    clause_str = metadata.get("clause") or ""

    local_viewer_url = ""
    if doc_meta.local_path:
        page_anchor = f"#page={page_num}" if page_num else "#page=1"
        local_viewer_url = f"/api/documents/raw/{doc_meta.local_path}{page_anchor}"

    return {
        "evidence_id": evidence_id,
        "kb": kb_name,
        "title": title_str,

        "source_doc_id": doc_meta.doc_id,
        "official_title": doc_meta.title,
        "issuing_authority": doc_meta.issuing_authority,
        "document_identifier": doc_meta.document_identifier,
        "version": doc_meta.version,
        "publication_date": doc_meta.publication_date,
        "effective_date": doc_meta.effective_date,
        "legal_status": doc_meta.legal_status,
        "source_url": doc_meta.official_url,
        "local_viewer_url": local_viewer_url,
        "faq_url": doc_meta.faq_url,

        "retrieval": {
            "rank": result.get("rank", index),
            "distance": result.get("distance"),
        },

        "provenance": {
            "kb": kb_name,
            "document": metadata.get("document"),
            "source_file": metadata.get("source_file"),
            "folder": metadata.get("folder"),
            "jurisdiction": metadata.get("jurisdiction") or doc_meta.jurisdiction,
            "document_type": metadata.get("document_type") or doc_meta.document_type,
            "legal_status": doc_meta.legal_status,
            "page": page_num,
            "section": metadata.get("section"),
            "clause": clause_str,
            "chunk_id": metadata.get(
                "chunk_id",
                result.get("chunk_id"),
            ),
            "language": metadata.get("language"),
            "text_hash": metadata.get("text_hash"),
            "official_url": doc_meta.official_url,
            "local_viewer_url": local_viewer_url,
        },

        "text": result.get("text", ""),

        "normalized_metadata": {
            "document": metadata.get("document"),
            "official_title": doc_meta.title,
            "publisher": doc_meta.issuing_authority or metadata.get("publisher"),
            "source_type": (
                metadata.get("source_type")
                or metadata.get("document_type")
                or doc_meta.document_type
            ),
            "jurisdiction": metadata.get("jurisdiction") or doc_meta.jurisdiction,
            "legal_status": doc_meta.legal_status,
            "page": page_num,
            "section": metadata.get("section"),
            "clause": clause_str,
            "source_url": doc_meta.official_url,
            "local_viewer_url": local_viewer_url,
            "chunk_id": metadata.get(
                "chunk_id",
                result.get("chunk_id"),
            ),
            "retrieval_rank": result.get(
                "rank",
                index,
            ),
            "version": metadata.get("version") or doc_meta.version,
            "publication_date": metadata.get(
                "publication_date"
            ) or doc_meta.publication_date,
            "effective_date": metadata.get(
                "effective_date"
            ) or doc_meta.effective_date,
            "expiry_date": metadata.get(
                "expiry_date"
            ),
        },
    }


def adapt_retrieval_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert the complete RAG retrieval result set
    into Evidence Engine records.
    """

    evidence_records = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        evidence_records.append(
            build_evidence_record(
                result=result,
                index=index,
            )
        )

    return evidence_records
