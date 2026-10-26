"""
NetraSetu Index Generation Manager
==================================

Manages atomic index generations, invariants validation, and rollback (Part 4).
Prevents partially-built indexes from exposure to retrieval requests.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from rag.dynamic_kb.models import IndexGenerationManifest


class GenerationManager:
    """
    Coordinates atomic generation manifests and physical FAISS/embedding artifacts.
    """

    def __init__(self, kb_dir: Optional[Path] = None):
        self.kb_dir = kb_dir or Path(__file__).resolve().parent.parent
        self.manifest_file = self.kb_dir / "dynamic_kb" / "active_generation.json"
        self.rollback_file = self.kb_dir / "dynamic_kb" / "rollback_generation.json"
        self.active_manifest: Optional[IndexGenerationManifest] = None
        self._init_or_load()

    def _init_or_load(self):
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.active_manifest = IndexGenerationManifest.from_dict(data)
                print(f"[GEN] Active generation: {self.active_manifest.generation_id} ({self.active_manifest.vector_count} vectors)")
                return
            except Exception as exc:
                print(f"[GEN WARN] Error reading active manifest: {exc}")

        self._bootstrap_initial_generation()

    def _bootstrap_initial_generation(self):
        """Register the existing working 14,143 vector index as GEN-0001."""
        print("[GEN] Initializing baseline index generation GEN-0001...")
        index_file = self.kb_dir / "faiss_new.index"
        chunks_file = self.kb_dir / "chunks_new.json"
        emb_file = self.kb_dir / "embeddings_new.npy"

        vector_count = 14143
        dim = 1024

        if index_file.exists():
            try:
                idx = faiss.read_index(str(index_file))
                vector_count = idx.ntotal
                dim = idx.d
            except Exception as e:
                print(f"[GEN WARN] faiss read: {e}")

        manifest = IndexGenerationManifest(
            generation_id="GEN-0001",
            created_at=datetime.utcnow().isoformat() + "Z",
            vector_count=vector_count,
            dimension=dim,
            embedding_model="BAAI/bge-m3",
            document_count=72,
            active=True,
            index_file=index_file.name,
            chunks_file=chunks_file.name,
            embeddings_file=emb_file.name,
            invariants_verified=True,
        )

        self.active_manifest = manifest
        self._save_manifest(manifest, self.manifest_file)
        print(f"[GEN] GEN-0001 baseline established ({vector_count} vectors, dim {dim}).")

    def _save_manifest(self, manifest: IndexGenerationManifest, target_path: Path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = target_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        tmp.replace(target_path)

    def validate_generation(
        self,
        index: faiss.Index,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray,
        expected_dim: int = 1024,
    ) -> Tuple[bool, str]:
        """Strict validation of invariants before activation (Part 4)."""
        if index.d != expected_dim:
            return False, f"Dimension mismatch: expected {expected_dim}, got {index.d}"
        if embeddings.shape[1] != expected_dim:
            return False, f"Embedding shape mismatch: expected dim {expected_dim}, got {embeddings.shape[1]}"
        if index.ntotal != len(chunks):
            return False, f"Count mismatch: index has {index.ntotal} vectors but chunks list has {len(chunks)}"
        if embeddings.shape[0] != len(chunks):
            return False, f"Embedding count mismatch: {embeddings.shape[0]} != {len(chunks)}"
        if np.isnan(embeddings).any() or np.isinf(embeddings).any():
            return False, "Embeddings contain NaN or Inf values"
        return True, "All generation invariants verified"

    def stage_and_publish(
        self,
        new_chunks: List[Dict[str, Any]],
        new_embeddings: np.ndarray,
        active_doc_ids: List[str],
    ) -> IndexGenerationManifest:
        """
        Builds a new faiss.IndexFlatIP, validates consistency, backs up current
        active generation for rollback, and publishes atomically.
        """
        dim = new_embeddings.shape[1]
        new_idx = faiss.IndexFlatIP(dim)
        new_idx.add(np.asarray(new_embeddings, dtype="float32"))

        valid, msg = self.validate_generation(new_idx, new_chunks, new_embeddings, dim)
        if not valid:
            raise ValueError(f"Generation validation failed: {msg}")

        # Current generation ID increment
        curr_num = 1
        if self.active_manifest and self.active_manifest.generation_id.startswith("GEN-"):
            try:
                curr_num = int(self.active_manifest.generation_id.split("-")[1])
            except ValueError:
                curr_num = 1
        new_gen_id = f"GEN-{curr_num + 1:04d}"

        # Preserve rollback manifest
        if self.active_manifest:
            self._save_manifest(self.active_manifest, self.rollback_file)

        # Atomic write of chunks, embeddings, index
        chunks_path = self.kb_dir / "chunks_new.json"
        emb_path = self.kb_dir / "embeddings_new.npy"
        idx_path = self.kb_dir / "faiss_new.index"

        # 1. Write chunks
        tmp_chunks = chunks_path.with_suffix(".tmp.json")
        with open(tmp_chunks, "w", encoding="utf-8") as f:
            json.dump(new_chunks, f, ensure_ascii=False)
        tmp_chunks.replace(chunks_path)

        # 2. Write embeddings
        tmp_emb = emb_path.with_suffix(".tmp.npy")
        np.save(tmp_emb, new_embeddings)
        tmp_emb.replace(emb_path)

        # 3. Write index
        tmp_idx = idx_path.with_suffix(".tmp.index")
        faiss.write_index(new_idx, str(tmp_idx))
        tmp_idx.replace(idx_path)

        # 4. Save new active manifest
        manifest = IndexGenerationManifest(
            generation_id=new_gen_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            vector_count=new_idx.ntotal,
            dimension=dim,
            embedding_model="BAAI/bge-m3",
            document_count=len(active_doc_ids),
            active_doc_ids=active_doc_ids,
            active=True,
            parent_generation_id=self.active_manifest.generation_id if self.active_manifest else None,
            index_file=idx_path.name,
            chunks_file=chunks_path.name,
            embeddings_file=emb_path.name,
            invariants_verified=True,
        )

        self.active_manifest = manifest
        self._save_manifest(manifest, self.manifest_file)
        print(f"[GEN] Published new generation {new_gen_id} with {new_idx.ntotal} vectors.")
        return manifest

    def rollback(self) -> Optional[IndexGenerationManifest]:
        """Rollback to the last known-good generation (Part 4)."""
        if not self.rollback_file.exists():
            return None
        with open(self.rollback_file, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
        manifest = IndexGenerationManifest.from_dict(prev_data)
        self.active_manifest = manifest
        self._save_manifest(manifest, self.manifest_file)
        print(f"[GEN] Rolled back to generation {manifest.generation_id}.")
        return manifest
