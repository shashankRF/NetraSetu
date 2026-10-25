"""
NetraSetu Idempotent Dynamic Ingestion Pipeline
==============================================

Implements incremental, provenance-aware updates (Part 3 & Part 11).
Re-embeds ONLY genuinely new/modified chunks, bounding CPU execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from rag.dynamic_kb.models import (
    DocumentRecord,
    IndexGenerationManifest,
    IngestionResult,
    SourceApprovalStatus,
    ExtractionStatus,
    IndexingStatus,
)
from rag.dynamic_kb.registry import DocumentRegistryManager, _compute_sha256
from rag.dynamic_kb.generation_manager import GenerationManager
from rag.dynamic_kb.cache_manager import DynamicKBCacheManager
from rag.dynamic_kb.chunker import chunk_document


class DynamicIngestionPipeline:
    """
    Coordinates incremental document addition, modification detection,
    document replacement, and retirement without full-corpus re-embedding.
    """

    _lock = threading.Lock()

    def __init__(
        self,
        registry_mgr: Optional[DocumentRegistryManager] = None,
        gen_mgr: Optional[GenerationManager] = None,
        cache_mgr: Optional[DynamicKBCacheManager] = None,
    ):
        self.base_dir = Path(__file__).resolve().parent
        self.rag_dir = self.base_dir.parent
        self.repo_root = self.rag_dir.parent
        self.registry_mgr = registry_mgr or DocumentRegistryManager()
        self.gen_mgr = gen_mgr or GenerationManager()
        self.cache_mgr = cache_mgr or DynamicKBCacheManager(self.repo_root)

    def ingest_document(
        self,
        filepath: Path | str,
        title: str,
        doc_id: Optional[str] = None,
        jurisdiction: str = "India",
        issuing_org: str = "Government / Standards Body",
        approval_status: str = SourceApprovalStatus.APPROVED_FOR_RETRIEVAL.value,
        force_reindex: bool = False,
    ) -> IngestionResult:
        """
        Idempotent document ingestion:
        1. Validate source file & compute SHA-256 hash.
        2. If hash matches existing registered doc and no forced reindex -> SKIPPED (unchanged).
        3. If only metadata changed -> METADATA_UPDATED.
        4. If content modified or new document -> extract, chunk, embed ONLY new chunks,
           re-assemble FAISS index generation, publish atomically, and invalidate caches.
        """
        start_time = time.time()
        p = Path(filepath)
        if not p.is_file():
            return IngestionResult(
                doc_id=doc_id or "UNKNOWN",
                operation="FAILED",
                status="FAILED",
                generation_id=self.gen_mgr.active_manifest.generation_id if self.gen_mgr.active_manifest else "NONE",
                message=f"File not found: {filepath}",
                error="FileNotFoundError",
            )

        content_hash = _compute_sha256(p)
        stable_id = doc_id or p.stem.upper().replace(" ", "_")

        with self._lock:
            existing = self.registry_mgr.get_document(stable_id)
            if not existing:
                existing = self.registry_mgr.get_document_by_hash(content_hash)

            # Check for unchanged document
            if existing and existing.content_hash == content_hash and not force_reindex:
                if (
                    existing.title == title
                    and existing.jurisdiction == jurisdiction
                    and existing.approval_status == approval_status
                ):
                    duration = time.time() - start_time
                    print(f"[INGEST] Document {stable_id} is UNCHANGED (hash match). Skipping in {duration:.3f}s.")
                    return IngestionResult(
                        doc_id=existing.doc_id,
                        operation="UNCHANGED",
                        status="SKIPPED",
                        generation_id=self.gen_mgr.active_manifest.generation_id,
                        total_vectors=self.gen_mgr.active_manifest.vector_count,
                        total_duration_seconds=duration,
                        message="Content and metadata identical; processing skipped.",
                    )
                else:
                    # Metadata-only update
                    existing.title = title
                    existing.jurisdiction = jurisdiction
                    existing.issuing_org = issuing_org
                    existing.approval_status = approval_status
                    self.registry_mgr.register_or_update(existing)
                    self.cache_mgr.invalidate_for_document(existing.doc_id, content_hash)
                    duration = time.time() - start_time
                    print(f"[INGEST] Updated metadata for {stable_id} without re-embedding.")
                    return IngestionResult(
                        doc_id=existing.doc_id,
                        operation="METADATA_UPDATED",
                        status="SUCCESS",
                        generation_id=self.gen_mgr.active_manifest.generation_id,
                        total_vectors=self.gen_mgr.active_manifest.vector_count,
                        total_duration_seconds=duration,
                        message="Metadata updated successfully; vector embeddings preserved.",
                    )

            # -------------------------------------------------------------
            # Content changed or new document: Extract & Chunk
            # -------------------------------------------------------------
            t_ext = time.time()
            new_chunks = chunk_document(
                filepath=p,
                doc_id=stable_id,
                doc_name=title,
                jurisdiction=jurisdiction,
            )
            extraction_duration = time.time() - t_ext

            if not new_chunks:
                return IngestionResult(
                    doc_id=stable_id,
                    operation="FAILED",
                    status="FAILED",
                    generation_id=self.gen_mgr.active_manifest.generation_id,
                    message="Document extraction yielded 0 chunks.",
                    error="ExtractionEmptyError",
                )

            # -------------------------------------------------------------
            # Generate Embeddings ONLY for new chunks
            # -------------------------------------------------------------
            t_emb = time.time()
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("BAAI/bge-m3", device="cpu")
            texts = [c["text"] for c in new_chunks]
            new_vectors = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
            new_vectors = np.asarray(new_vectors, dtype="float32")
            embedding_duration = time.time() - t_emb

            # -------------------------------------------------------------
            # Merge with existing corpus
            # -------------------------------------------------------------
            t_idx = time.time()
            chunks_path = self.rag_dir / "chunks_new.json"
            emb_path = self.rag_dir / "embeddings_new.npy"

            with open(chunks_path, "r", encoding="utf-8") as f:
                existing_chunks = json.load(f)
            existing_embeddings = np.load(emb_path)

            # If replacing an existing document, filter out old chunks
            keep_indices = []
            for i, c in enumerate(existing_chunks):
                m = c.get("metadata", {}) or {}
                if m.get("doc_id") != stable_id and m.get("document") != title:
                    keep_indices.append(i)

            merged_chunks = [existing_chunks[i] for i in keep_indices] + new_chunks
            merged_embeddings = np.vstack([existing_embeddings[keep_indices], new_vectors])

            # -------------------------------------------------------------
            # Atomic Generation Staging & Activation
            # -------------------------------------------------------------
            active_docs = [
                d.doc_id for d in self.registry_mgr.list_documents(active_only=True)
            ]
            if stable_id not in active_docs:
                active_docs.append(stable_id)

            old_gen = self.gen_mgr.active_manifest.generation_id if self.gen_mgr.active_manifest else "GEN-0001"
            manifest = self.gen_mgr.stage_and_publish(
                new_chunks=merged_chunks,
                new_embeddings=merged_embeddings,
                active_doc_ids=active_docs,
            )
            indexing_duration = time.time() - t_idx

            # Update Registry Record
            chunk_ids = [c["metadata"]["chunk_id"] for c in new_chunks]
            doc_rec = DocumentRecord(
                doc_id=stable_id,
                filename=p.name,
                title=title,
                local_path=str(p.relative_to(self.repo_root) if p.is_relative_to(self.repo_root) else p).replace("\\", "/"),
                issuing_org=issuing_org,
                jurisdiction=jurisdiction,
                version="1.1" if existing else "1.0",
                ingestion_timestamp=datetime.utcnow().isoformat() + "Z",
                content_hash=content_hash,
                extraction_status=ExtractionStatus.TEXT_EXTRACTED.value,
                indexing_status=IndexingStatus.ACTIVE.value,
                verification_status="VERIFIED",
                approval_status=approval_status,
                active=True,
                chunk_count=len(new_chunks),
                chunk_ids=chunk_ids,
                index_generation_id=manifest.generation_id,
            )
            self.registry_mgr.register_or_update(doc_rec)

            # Cache Invalidation
            self.cache_mgr.invalidate_for_document(stable_id, content_hash)
            self.cache_mgr.invalidate_generation(old_gen, manifest.generation_id)

            total_duration = time.time() - start_time
            print(f"[INGEST] Successfully published {stable_id} into {manifest.generation_id} in {total_duration:.2f}s.")

            return IngestionResult(
                doc_id=stable_id,
                operation="VERSION_REPLACED" if existing else "NEW_INGESTED",
                status="SUCCESS",
                generation_id=manifest.generation_id,
                chunks_added=len(new_chunks),
                chunks_removed=len(existing_chunks) - len(keep_indices),
                total_vectors=manifest.vector_count,
                extraction_duration_seconds=extraction_duration,
                embedding_duration_seconds=embedding_duration,
                indexing_duration_seconds=indexing_duration,
                total_duration_seconds=total_duration,
                message=f"Ingested {len(new_chunks)} chunks into {manifest.generation_id}.",
            )

    def retire_document(self, doc_id: str) -> IngestionResult:
        """Retires a document and removes its vectors from the active generation (Part 5)."""
        start_time = time.time()
        with self._lock:
            doc = self.registry_mgr.get_document(doc_id)
            if not doc:
                return IngestionResult(
                    doc_id=doc_id,
                    operation="RETIRED",
                    status="FAILED",
                    generation_id=self.gen_mgr.active_manifest.generation_id,
                    message="Document ID not found in registry.",
                    error="DocumentNotFound",
                )

            # Update registry status
            self.registry_mgr.retire_document(doc_id)

            # Filter out chunks from active generation
            chunks_path = self.rag_dir / "chunks_new.json"
            emb_path = self.rag_dir / "embeddings_new.npy"

            with open(chunks_path, "r", encoding="utf-8") as f:
                existing_chunks = json.load(f)
            existing_embeddings = np.load(emb_path)

            keep_indices = [
                i for i, c in enumerate(existing_chunks)
                if c.get("metadata", {}).get("doc_id") != doc_id
                and c.get("metadata", {}).get("document") != doc.title
            ]

            retained_chunks = [existing_chunks[i] for i in keep_indices]
            retained_embeddings = existing_embeddings[keep_indices]

            active_docs = [
                d.doc_id for d in self.registry_mgr.list_documents(active_only=True)
            ]

            manifest = self.gen_mgr.stage_and_publish(
                new_chunks=retained_chunks,
                new_embeddings=retained_embeddings,
                active_doc_ids=active_docs,
            )

            self.cache_mgr.invalidate_for_document(doc_id, doc.content_hash)
            duration = time.time() - start_time

            return IngestionResult(
                doc_id=doc_id,
                operation="RETIRED",
                status="SUCCESS",
                generation_id=manifest.generation_id,
                chunks_removed=len(existing_chunks) - len(keep_indices),
                total_vectors=manifest.vector_count,
                total_duration_seconds=duration,
                message=f"Document {doc_id} retired. Chunks removed from active retrieval.",
            )
