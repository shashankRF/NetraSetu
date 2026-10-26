"""
NetraSetu Controlled Document Registry Manager
=============================================

Authoritative manager for registered documents, source provenance,
and lifecycle states (Part 2 & Part 6).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rag.dynamic_kb.models import (
    DocumentRecord,
    SourceApprovalStatus,
    ExtractionStatus,
    IndexingStatus,
)


def _compute_sha256(filepath: Path | str) -> str:
    """Calculate SHA-256 content hash of a physical file."""
    p = Path(filepath)
    if not p.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class DocumentRegistryManager:
    """
    Manages the authoritative document registry (registry_data.json).
    Ensures safe, idempotent access to document metadata and status.
    """

    def __init__(self, registry_file: Optional[Path] = None):
        self.base_dir = Path(__file__).resolve().parent
        self.rag_dir = self.base_dir.parent
        self.repo_root = self.rag_dir.parent
        self.registry_file = registry_file or (self.base_dir / "registry_data.json")
        self.documents: Dict[str, DocumentRecord] = {}
        self._load_or_bootstrap()

    def _load_or_bootstrap(self):
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.documents = {
                    k: DocumentRecord.from_dict(v)
                    for k, v in data.get("documents", {}).items()
                }
                print(f"[REGISTRY] Loaded {len(self.documents)} registered documents from disk.")
                return
            except Exception as exc:
                print(f"[REGISTRY WARN] Error reading registry: {exc}. Rebuilding bootstrap.")

        self._bootstrap_from_corpus()

    def _bootstrap_from_corpus(self):
        """Bootstrap the document registry from the existing 14,143 chunk corpus."""
        print("[REGISTRY] Bootstrapping document registry from corpus...")
        chunks_path = self.rag_dir / "chunks_new.json"
        if not chunks_path.exists():
            return

        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Import authoritative catalog if available
        auth_registry = {}
        try:
            from Backend.evidence_engine.document_registry import DOCUMENT_REGISTRY
            auth_registry = DOCUMENT_REGISTRY
        except Exception as e:
            print(f"[REGISTRY WARN] Could not import DOCUMENT_REGISTRY: {e}")

        # Group chunks by document
        doc_chunks: Dict[str, List[Dict[str, Any]]] = {}
        for idx, c in enumerate(chunks):
            m = c.get("metadata", {}) or {}
            d_name = m.get("document") or m.get("source_file") or f"doc_{idx}"
            if d_name not in doc_chunks:
                doc_chunks[d_name] = []
            doc_chunks[d_name].append(c)

        for doc_name, c_list in doc_chunks.items():
            first_meta = c_list[0].get("metadata", {}) or {}
            source_file = first_meta.get("source_file") or f"{doc_name}.pdf"
            jurisdiction = first_meta.get("jurisdiction") or "India"

            # Stable doc_id slug
            doc_id_slug = re.sub(r"[^A-Za-z0-9_-]", "_", doc_name).strip("_").upper()
            if not doc_id_slug:
                doc_id_slug = f"DOC_{abs(hash(doc_name))}"

            # Search for local physical file
            local_path = ""
            for candidate in [
                self.repo_root / "knowledge_base" / "Documents main" / source_file,
                self.repo_root / "knowledge_base" / source_file,
                self.repo_root / "knowledge_base" / Path(source_file).name,
            ]:
                if candidate.is_file():
                    local_path = str(candidate.relative_to(self.repo_root)).replace("\\", "/")
                    break

            content_hash = ""
            if local_path:
                content_hash = _compute_sha256(self.repo_root / local_path)
            else:
                content_hash = hashlib.sha256(f"{doc_name}:{len(c_list)}".encode("utf-8")).hexdigest()

            # Cross-reference with authoritative registry
            issuing_org = "Government of India / Telecom Standards Org"
            legal_status = "BINDING_STATUTORY"
            approval = SourceApprovalStatus.APPROVED_FOR_RETRIEVAL.value

            for auth_id, auth_meta in auth_registry.items():
                if auth_meta.title.lower() in doc_name.lower() or doc_name.lower() in auth_meta.title.lower():
                    issuing_org = auth_meta.issuing_authority
                    legal_status = auth_meta.legal_status
                    doc_id_slug = auth_id
                    break

            chunk_ids = [
                c.get("metadata", {}).get("chunk_id") or f"c_{i}"
                for i, c in enumerate(c_list)
            ]

            record = DocumentRecord(
                doc_id=doc_id_slug,
                filename=Path(source_file).name,
                title=doc_name,
                local_path=local_path,
                issuing_org=issuing_org,
                jurisdiction=jurisdiction,
                version="1.0",
                ingestion_timestamp=datetime.utcnow().isoformat() + "Z",
                content_hash=content_hash,
                extraction_status=ExtractionStatus.TEXT_EXTRACTED.value,
                indexing_status=IndexingStatus.ACTIVE.value,
                verification_status="VERIFIED",
                approval_status=approval,
                legal_status=legal_status,
                active=True,
                chunk_count=len(c_list),
                chunk_ids=chunk_ids,
                index_generation_id="GEN-0001",
            )
            self.documents[record.doc_id] = record

        self.save()
        print(f"[REGISTRY] Bootstrapped {len(self.documents)} documents into registry_data.json.")

    def save(self):
        """Persist registry to disk atomically."""
        data = {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "document_count": len(self.documents),
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
        }
        temp_file = self.registry_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.registry_file)

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        return self.documents.get(doc_id)

    def get_document_by_hash(self, content_hash: str) -> Optional[DocumentRecord]:
        if not content_hash:
            return None
        for doc in self.documents.values():
            if doc.content_hash == content_hash:
                return doc
        return None

    def list_documents(
        self,
        approval_status: Optional[str] = None,
        active_only: bool = False,
    ) -> List[DocumentRecord]:
        docs = list(self.documents.values())
        if active_only:
            docs = [d for d in docs if d.active]
        if approval_status:
            docs = [d for d in docs if d.approval_status == approval_status]
        return docs

    def register_or_update(self, record: DocumentRecord) -> DocumentRecord:
        record.ingestion_timestamp = datetime.utcnow().isoformat() + "Z"
        self.documents[record.doc_id] = record
        self.save()
        return record

    def approve_document(self, doc_id: str) -> Optional[DocumentRecord]:
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        doc.approval_status = SourceApprovalStatus.APPROVED_FOR_RETRIEVAL.value
        doc.active = True
        self.save()
        return doc

    def retire_document(self, doc_id: str) -> Optional[DocumentRecord]:
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        doc.approval_status = SourceApprovalStatus.RETIRED.value
        doc.active = False
        doc.indexing_status = IndexingStatus.RETIRED.value
        self.save()
        return doc
