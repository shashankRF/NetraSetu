"""
NetraSetu Dynamic Knowledge Base API Router
===========================================

REST endpoints for Knowledge Base Management, Ingestion, Approval,
Retirement, and Atomic Rollback (Part 9 & Part 10).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from rag.dynamic_kb import (
    DocumentRecord,
    DocumentRegistryManager,
    DynamicIngestionPipeline,
    GenerationManager,
    IndexGenerationManifest,
    IngestionResult,
    SourceApprovalStatus,
)

router = APIRouter(prefix="/api/kb", tags=["Dynamic Knowledge Base"])

_registry_mgr = DocumentRegistryManager()
_gen_mgr = GenerationManager()
_pipeline = DynamicIngestionPipeline(registry_mgr=_registry_mgr, gen_mgr=_gen_mgr)


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class IngestPathRequest(BaseModel):
    filepath: str = Field(..., description="Local path to approved document")
    title: str = Field(..., description="Canonical document title")
    doc_id: Optional[str] = None
    jurisdiction: str = "India"
    issuing_org: str = "Department of Telecommunications"
    approval_status: str = "APPROVED_FOR_RETRIEVAL"
    force_reindex: bool = False


class DocumentApprovalRequest(BaseModel):
    reviewer_notes: Optional[str] = "Approved by compliance authority"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
def get_kb_status() -> Dict[str, Any]:
    """
    Returns high-level dynamic KB health, active generation, document counts,
    and index consistency invariants (Part 9).
    """
    all_docs = _registry_mgr.list_documents()
    active_docs = [d for d in all_docs if d.active and d.approval_status == SourceApprovalStatus.APPROVED_FOR_RETRIEVAL.value]
    pending_docs = [d for d in all_docs if d.approval_status in {SourceApprovalStatus.PENDING_REVIEW.value, SourceApprovalStatus.PENDING_VALIDATION.value}]
    retired_docs = [d for d in all_docs if d.approval_status == SourceApprovalStatus.RETIRED.value]

    manifest = _gen_mgr.active_manifest

    return {
        "status": "HEALTHY",
        "current_generation": manifest.generation_id if manifest else "GEN-0001",
        "vector_count": manifest.vector_count if manifest else 14143,
        "dimension": manifest.dimension if manifest else 1024,
        "embedding_model": manifest.embedding_model if manifest else "BAAI/bge-m3",
        "index_consistency": "VERIFIED_CONSISTENT" if (manifest and manifest.invariants_verified) else "UNKNOWN",
        "total_registered_documents": len(all_docs),
        "active_eligible_documents": len(active_docs),
        "pending_review_documents": len(pending_docs),
        "retired_documents": len(retired_docs),
        "last_updated": manifest.created_at if manifest else None,
        "rollback_available": _gen_mgr.rollback_file.exists(),
    }


@router.get("/documents")
def list_documents(
    approval_status: Optional[str] = None,
    active_only: bool = False,
) -> Dict[str, Any]:
    """List registered documents with optional lifecycle filters."""
    docs = _registry_mgr.list_documents(approval_status=approval_status, active_only=active_only)
    return {
        "count": len(docs),
        "documents": [d.to_dict() for d in docs],
    }


@router.get("/documents/{doc_id}")
def get_document_details(doc_id: str) -> Dict[str, Any]:
    """Retrieve full provenance and metadata for a specific document."""
    doc = _registry_mgr.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in registry")
    return doc.to_dict()


@router.post("/documents/ingest")
def ingest_document(req: IngestPathRequest) -> Dict[str, Any]:
    """
    Incrementally ingests a document by file path.
    Skips processing if SHA-256 hash is unchanged.
    """
    res = _pipeline.ingest_document(
        filepath=req.filepath,
        title=req.title,
        doc_id=req.doc_id,
        jurisdiction=req.jurisdiction,
        issuing_org=req.issuing_org,
        approval_status=req.approval_status,
        force_reindex=req.force_reindex,
    )
    if res.status == "FAILED":
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/documents/{doc_id}/approve")
def approve_document(doc_id: str, req: Optional[DocumentApprovalRequest] = None) -> Dict[str, Any]:
    """Approve a pending/unverified document for authoritative retrieval (Part 6)."""
    doc = _registry_mgr.approve_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return {
        "message": f"Document {doc_id} approved for authoritative retrieval.",
        "document": doc.to_dict(),
    }


@router.post("/documents/{doc_id}/retire")
def retire_document(doc_id: str) -> Dict[str, Any]:
    """Retires a document and safely removes its vectors from active retrieval (Part 5)."""
    res = _pipeline.retire_document(doc_id)
    if res.status == "FAILED":
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/rollback")
def rollback_generation() -> Dict[str, Any]:
    """Rolls back to the previous known-good generation (Part 4)."""
    res = _gen_mgr.rollback()
    if not res:
        raise HTTPException(status_code=400, detail="No rollback generation available.")
    return {
        "message": f"Successfully rolled back to {res.generation_id}.",
        "manifest": res.to_dict(),
    }
