"""
HackGrid Multi-KB Retrieval Engine

Unified multi-domain retrieval supporting:
    1. MAIN KB (14,143 chunks - BAAI/bge-m3, FAISS, always searched)
    2. DEFENCE KB (397 chunks - DRDO, Drone Rules, NATO UAS)
    3. MARITIME KB (273 chunks - IMO AIS, Maritime Safety, NOSDCP)

Core Invariants:
- MAIN KB is NEVER bypassed; it participates in every retrieval.
- Domain KBs are queried when the domain classifier indicates domain relevance.
- Shared BGE-M3 singleton prevents redundant memory/CPU usage.
- Strict source provenance ('kb': 'MAIN' | 'DEFENCE' | 'MARITIME') attached to every chunk.
"""

from __future__ import annotations

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAIN_DIR = BASE_DIR
DEFENCE_DIR = BASE_DIR / "DEFENCE CHUNKS"
MARITIME_DIR = BASE_DIR / "MARITIME CHUNKS"

INDEX_CONFIG = {
    "MAIN": {
        "index": MAIN_DIR / "faiss_new.index",
        "chunks": MAIN_DIR / "chunks_new.json",
        "embeddings": MAIN_DIR / "embeddings_new.npy",
    },
    "DEFENCE": {
        "index": DEFENCE_DIR / "defence_faiss.index",
        "chunks": DEFENCE_DIR / "defence_chunks.json",
        "embeddings": DEFENCE_DIR / "defence_embeddings.npy",
    },
    "MARITIME": {
        "index": MARITIME_DIR / "maritime_faiss.index",
        "chunks": MARITIME_DIR / "maritime_chunks.json",
        "embeddings": MARITIME_DIR / "maritime_embeddings.npy",
    },
}

MODEL_NAME = "BAAI/bge-m3"

JURISDICTION_PROFILES = {
    "India": {"India", "International"},
    "European Union": {"European Union", "International"},
}


# ============================================================
# MULTI-KB RETRIEVER CLASS
# ============================================================

class MultiKBRetriever:
    """
    Unified multi-domain retriever for HackGrid.
    """

    def __init__(self):
        print("=" * 70)
        print("HACKGRID MULTI-KB RETRIEVER INITIALIZING")
        print("=" * 70)

        print(f"Loading shared {MODEL_NAME} model on CPU...")
        self.model = SentenceTransformer(
            MODEL_NAME,
            device="cpu",
        )
        print("BGE-M3 loaded.")

        self.indexes: Dict[str, Any] = {}
        self.chunks: Dict[str, List[Dict[str, Any]]] = {}
        self.embeddings: Dict[str, Any] = {}

        self._load_all_kbs()

    def _load_all_kbs(self):
        for kb_name, cfg in INDEX_CONFIG.items():
            index_path = cfg["index"]
            chunks_path = cfg["chunks"]
            emb_path = cfg["embeddings"]

            if not chunks_path.exists():
                raise FileNotFoundError(f"{kb_name} chunks missing: {chunks_path}")

            with open(chunks_path, "r", encoding="utf-8") as f:
                chunk_list = json.load(f)

            if not emb_path.exists():
                raise FileNotFoundError(f"{kb_name} embeddings missing: {emb_path}")

            emb = np.load(emb_path, mmap_mode="r")

            # Check or auto-build FAISS index
            if not index_path.exists() or index_path.stat().st_size == 0:
                print(f"[REPAIR] Building FAISS IndexFlatIP for {kb_name} from embeddings...")
                idx = faiss.IndexFlatIP(emb.shape[1])
                idx.add(np.asarray(emb, dtype="float32"))
                faiss.write_index(idx, str(index_path))
            else:
                try:
                    idx = faiss.read_index(str(index_path))
                except Exception as exc:
                    print(f"[REPAIR] Re-reading FAISS failed for {kb_name}: {exc}. Rebuilding...")
                    idx = faiss.IndexFlatIP(emb.shape[1])
                    idx.add(np.asarray(emb, dtype="float32"))
                    faiss.write_index(idx, str(index_path))

            if idx.ntotal != len(chunk_list):
                raise ValueError(
                    f"{kb_name}: FAISS count ({idx.ntotal}) != chunks ({len(chunk_list)})"
                )

            self.indexes[kb_name] = idx
            self.chunks[kb_name] = chunk_list
            self.embeddings[kb_name] = emb

            print(f"  [{kb_name}] Chunks: {len(chunk_list)} | Vectors: {idx.ntotal} | Dim: {idx.d} -> READY")

        print("=" * 70)
        print("ALL KNOWLEDGE BASES OPERATIONAL")
        print("=" * 70)

    def _embed_query(self, query: str) -> np.ndarray:
        vec = self.model.encode([query], normalize_embeddings=True)
        return np.asarray(vec, dtype="float32")

    def _get_allowed_jurisdictions(self, jurisdiction: Optional[str]) -> Optional[Set[str]]:
        if not jurisdiction:
            return None
        return JURISDICTION_PROFILES.get(jurisdiction, {jurisdiction, "International"})

    def _search_single_kb(
        self,
        query_vec: np.ndarray,
        kb_name: str,
        k: int,
        allowed_jurisdictions: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        idx = self.indexes[kb_name]
        chunk_list = self.chunks[kb_name]

        # Fetch extra if filtering by jurisdiction
        fetch_k = min(len(chunk_list), k * 5 if allowed_jurisdictions else k)
        distances, ids = idx.search(query_vec, max(fetch_k, 1))

        results = []
        for rank, (score, v_id) in enumerate(zip(distances[0], ids[0]), start=1):
            if v_id < 0 or v_id >= len(chunk_list):
                continue

            chunk = chunk_list[v_id]
            meta = chunk.get("metadata", {}) or {}

            c_jur = meta.get("jurisdiction")
            if allowed_jurisdictions and c_jur and c_jur not in allowed_jurisdictions:
                continue

            # Tag KB provenance cleanly
            meta["kb"] = kb_name

            results.append({
                "kb": kb_name,
                "rank_in_kb": rank,
                "score": float(score),
                "distance": float(score),
                "text": chunk.get("text") or chunk.get("content", ""),
                "metadata": meta,
                "vector_id": int(v_id),
            })

            if len(results) >= k:
                break

        return results

    def retrieve_unified(
        self,
        query: str,
        k: int = 8,
        jurisdiction: Optional[str] = None,
        domains: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Multi-domain retrieval adhering to candidate pooling quotas.
        MAIN KB is ALWAYS included.
        """
        query_str = (query or "").strip()
        if not query_str:
            return []

        # Determine target KBs
        selected_kbs = ["MAIN"]
        if domains:
            if isinstance(domains, str):
                domains = [domains]
            for d in domains:
                d_clean = str(d).upper().strip()
                if "DEFENCE" in d_clean or "DRONE" in d_clean:
                    if "DEFENCE" not in selected_kbs:
                        selected_kbs.append("DEFENCE")
                if "MARITIME" in d_clean or "PORT" in d_clean or "VESSEL" in d_clean or "SEA" in d_clean or "OIL" in d_clean:
                    if "MARITIME" not in selected_kbs:
                        selected_kbs.append("MARITIME")

        query_vec = self._embed_query(query_str)
        allowed_jur = self._get_allowed_jurisdictions(jurisdiction)

        # Quota allocation
        # MAIN always gets a generous slice
        per_kb_fetch = max(k * 2, 15)
        candidates_by_kb: Dict[str, List[Dict[str, Any]]] = {}

        for kb in selected_kbs:
            candidates_by_kb[kb] = self._search_single_kb(
                query_vec=query_vec,
                kb_name=kb,
                k=per_kb_fetch,
                allowed_jurisdictions=allowed_jur,
            )

        # Quota-based pooling guaranteeing representation for all participating KBs
        final_items: List[Dict[str, Any]] = []
        seen_keys: Set[Any] = set()

        if len(selected_kbs) == 1:
            for item in candidates_by_kb.get("MAIN", []):
                meta = item.get("metadata", {})
                dedupe_key = (
                    item["kb"],
                    meta.get("chunk_id") or meta.get("document") or item["text"][:100],
                )
                if dedupe_key not in seen_keys:
                    seen_keys.add(dedupe_key)
                    final_items.append(item)
                if len(final_items) >= k:
                    break
        else:
            # Multi-KB: calculate quota per KB
            # MAIN is guaranteed >= 40-50% of k
            main_quota = max(k // 2, 3)
            # Domain KBs share the rest, each guaranteed >= 2 items
            domain_quota = max((k - main_quota) // (len(selected_kbs) - 1), 2)

            quota_picks: List[Dict[str, Any]] = []

            # 1. Guaranteed MAIN picks
            for item in candidates_by_kb.get("MAIN", [])[:main_quota]:
                quota_picks.append(item)

            # 2. Guaranteed Domain picks
            for kb in selected_kbs:
                if kb != "MAIN":
                    for item in candidates_by_kb.get(kb, [])[:domain_quota]:
                        quota_picks.append(item)

            # 3. Add quota picks to final_items with deduplication
            for item in quota_picks:
                meta = item.get("metadata", {})
                dedupe_key = (
                    item["kb"],
                    meta.get("chunk_id") or meta.get("document") or item["text"][:100],
                )
                if dedupe_key not in seen_keys:
                    seen_keys.add(dedupe_key)
                    final_items.append(item)

            # 4. Fill any remainder up to k from best remaining across all pools
            if len(final_items) < k:
                remaining: List[Dict[str, Any]] = []
                for kb in selected_kbs:
                    for item in candidates_by_kb.get(kb, []):
                        meta = item.get("metadata", {})
                        dedupe_key = (
                            item["kb"],
                            meta.get("chunk_id") or meta.get("document") or item["text"][:100],
                        )
                        if dedupe_key not in seen_keys:
                            remaining.append(item)

                remaining.sort(key=lambda x: x["score"], reverse=True)
                for item in remaining:
                    meta = item.get("metadata", {})
                    dedupe_key = (
                        item["kb"],
                        meta.get("chunk_id") or meta.get("document") or item["text"][:100],
                    )
                    if dedupe_key not in seen_keys:
                        seen_keys.add(dedupe_key)
                        final_items.append(item)
                    if len(final_items) >= k:
                        break

        # Re-sort final_items by score so downstream ranking receives them in semantic order
        final_items.sort(key=lambda x: x["score"], reverse=True)

        final_list = []
        for rank, item in enumerate(final_items[:k], start=1):
            final_list.append({
                "rank": rank,
                "original_rank": item.get("rank_in_kb", rank),
                "distance": item["distance"],
                "score": item["score"],
                "text": item["text"],
                "metadata": item["metadata"],
                "kb": item["kb"],
            })

        return final_list

    def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        candidates_per_kb: int = 15,
        final_k: int = 10,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        High-level search API returning structured results and metadata.
        """
        results = self.retrieve_unified(
            query=query,
            k=final_k,
            jurisdiction=jurisdiction,
            domains=domains,
        )

        selected_kbs = ["MAIN"]
        if domains:
            for d in domains:
                d_u = str(d).upper()
                if "DEFENCE" in d_u and "DEFENCE" not in selected_kbs:
                    selected_kbs.append("DEFENCE")
                if "MARITIME" in d_u and "MARITIME" not in selected_kbs:
                    selected_kbs.append("MARITIME")

        return {
            "query": query,
            "searched_kbs": selected_kbs,
            "candidate_count": len(results),
            "final_count": len(results),
            "results": results,
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Health and status report for all knowledge bases.
        """
        return {
            "status": "READY",
            "MAIN": {
                "status": "READY",
                "chunks": len(self.chunks.get("MAIN", [])),
                "vectors": self.indexes["MAIN"].ntotal if "MAIN" in self.indexes else 0,
                "dimension": self.indexes["MAIN"].d if "MAIN" in self.indexes else 0,
            },
            "DEFENCE": {
                "status": "READY",
                "chunks": len(self.chunks.get("DEFENCE", [])),
                "vectors": self.indexes["DEFENCE"].ntotal if "DEFENCE" in self.indexes else 0,
                "dimension": self.indexes["DEFENCE"].d if "DEFENCE" in self.indexes else 0,
            },
            "MARITIME": {
                "status": "READY",
                "chunks": len(self.chunks.get("MARITIME", [])),
                "vectors": self.indexes["MARITIME"].ntotal if "MARITIME" in self.indexes else 0,
                "dimension": self.indexes["MARITIME"].d if "MARITIME" in self.indexes else 0,
            },
            "unified_retriever": "READY",
        }


# ============================================================
# SINGLETON ACCESSOR
# ============================================================

_unified_retriever_instance: Optional[MultiKBRetriever] = None

def get_unified_retriever() -> MultiKBRetriever:
    global _unified_retriever_instance
    if _unified_retriever_instance is None:
        _unified_retriever_instance = MultiKBRetriever()
    return _unified_retriever_instance