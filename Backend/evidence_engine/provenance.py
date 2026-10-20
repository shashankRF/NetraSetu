from __future__ import annotations

from typing import Any, Dict

from .models import EvidenceMetadata


def extract_metadata(
    result: Dict[str, Any],
    rank: int | None = None,
) -> EvidenceMetadata:
    """
    Preserve provenance from the existing RAG retrieval layer.

    This function does not invent metadata.
    Missing metadata remains empty/None.
    """

    metadata = result.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    return EvidenceMetadata(
        document=str(
            metadata.get("document")
            or metadata.get("source")
            or ""
        ),
        publisher=str(
            metadata.get("publisher")
            or ""
        ),
        source_type=str(
            metadata.get("source_type")
            or ""
        ),
        jurisdiction=str(
            metadata.get("jurisdiction")
            or ""
        ),
        page=metadata.get("page"),
        section=str(
            metadata.get("section")
            or ""
        ),
        clause=str(
            metadata.get("clause")
            or ""
        ),
        chunk_id=result.get("chunk_id"),
        retrieval_rank=(
            rank
            if rank is not None
            else result.get("rank")
        ),
        version=str(
            metadata.get("version")
            or ""
        ),
        publication_date=str(
            metadata.get("publication_date")
            or ""
        ),
        effective_date=str(
            metadata.get("effective_date")
            or ""
        ),
        expiry_date=str(
            metadata.get("expiry_date")
            or ""
        ),
    )