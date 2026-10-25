"""
NetraSetu Canonical Knowledge Base Retrieval Engine

Unified retrieval over the authoritative NetraSetu knowledge base
(14,143 chunks - BAAI/bge-m3, FAISS IndexFlatIP).
"""

from __future__ import annotations

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
import math
import re
from collections import Counter
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
    Unified multi-domain retriever for NetraSetu.
    """

    def __init__(self):
        print("=" * 70)
        print("NETRASETU MULTI-KB RETRIEVER INITIALIZING")
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

        try:
            from rag.dynamic_kb.generation_manager import GenerationManager
            self.gen_mgr = GenerationManager()
            self.active_generation_id = (
                self.gen_mgr.active_manifest.generation_id
                if self.gen_mgr.active_manifest
                else "GEN-0001"
            )
        except Exception:
            self.active_generation_id = "GEN-0001"

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

            # Tag KB provenance and generation cleanly
            meta["kb"] = kb_name
            meta["index_generation_id"] = getattr(self, "active_generation_id", "GEN-0001")

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

    def _search_bm25_single_kb(
        self,
        query: str,
        kb_name: str,
        k: int,
        allowed_jurisdictions: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find lexical clause-level candidates without an extra model/dependency."""
        terms = set(re.findall(r"\d+(?:\.\d+)+|[a-z0-9]+", query.casefold()))
        if not terms:
            return []
        chunks = self.chunks[kb_name]
        tokenized: List[Counter] = []
        lengths: List[int] = []
        doc_frequency = Counter()
        for chunk in chunks:
            tokens = re.findall(r"\d+(?:\.\d+)+|[a-z0-9]+", str(chunk.get("text") or chunk.get("content") or "").casefold())
            counts = Counter(tokens)
            tokenized.append(counts)
            lengths.append(len(tokens))
            doc_frequency.update(terms.intersection(counts))
        average_length = sum(lengths) / max(len(lengths), 1)
        total_docs = len(chunks)
        scored = []
        for index, counts in enumerate(tokenized):
            meta = chunks[index].get("metadata", {}) or {}
            if allowed_jurisdictions and meta.get("jurisdiction") and meta.get("jurisdiction") not in allowed_jurisdictions:
                continue
            score = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log(1 + (total_docs - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5))
                denominator = frequency + 1.2 * (0.25 + 0.75 * lengths[index] / max(average_length, 1))
                score += inverse_frequency * (frequency * 2.2) / denominator
            if score > 0:
                scored.append((score, index))
        scored.sort(reverse=True)
        results = []
        for rank, (score, vector_id) in enumerate(scored[:k], start=1):
            chunk = chunks[vector_id]
            metadata = dict(chunk.get("metadata", {}) or {})
            metadata["kb"] = kb_name
            metadata["index_generation_id"] = getattr(self, "active_generation_id", "GEN-0001")
            results.append({
                "kb": kb_name,
                "rank_in_kb": rank,
                "score": float(score),
                "distance": float(score),
                "text": chunk.get("text") or chunk.get("content", ""),
                "metadata": metadata,
                "vector_id": int(vector_id),
            })
        return results

    @staticmethod
    def _merge_hybrid_candidates(semantic: List[Dict[str, Any]], lexical: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Merge dense and BM25 ranks with reciprocal-rank fusion."""
        merged = {}
        for channel, items in (("semantic", semantic), ("lexical", lexical)):
            for rank, item in enumerate(items, start=1):
                key = (item["kb"], item["vector_id"])
                existing = merged.setdefault(key, dict(item))
                existing[channel + "_rank"] = rank
                existing[channel + "_score"] = item["score"]
                if channel == "semantic":
                    existing["semantic_distance"] = item.get("distance")
        for item in merged.values():
            semantic_rank = item.get("semantic_rank")
            lexical_rank = item.get("lexical_rank")
            reciprocal = (1 / (60 + semantic_rank) if semantic_rank else 0) + (1 / (60 + lexical_rank) if lexical_rank else 0)
            item["hybrid_score"] = reciprocal * 61 / 2
            item["score"] = item["hybrid_score"]
            item["distance"] = item.get("semantic_distance")
        return sorted(merged.values(), key=lambda item: item["hybrid_score"], reverse=True)[:limit]

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

        # NetraSetu searches exclusively over the authoritative MAIN knowledge base
        selected_kbs = ["MAIN"]

        query_vec = self._embed_query(query_str)
        allowed_jur = self._get_allowed_jurisdictions(jurisdiction)

        # Quota allocation
        # MAIN always gets a generous slice
        per_kb_fetch = max(k * 2, 15)
        candidates_by_kb: Dict[str, List[Dict[str, Any]]] = {}

        for kb in selected_kbs:
            semantic_candidates = self._search_single_kb(
                query_vec=query_vec,
                kb_name=kb,
                k=per_kb_fetch,
                allowed_jurisdictions=allowed_jur,
            )
            lexical_candidates = self._search_bm25_single_kb(
                query=query_str,
                kb_name=kb,
                k=max(k * 4, 20),
                allowed_jurisdictions=allowed_jur,
            )
            candidates_by_kb[kb] = self._merge_hybrid_candidates(
                semantic_candidates,
                lexical_candidates,
                limit=per_kb_fetch,
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

                remaining.sort(key=lambda x: x.get("hybrid_score", x["score"]), reverse=True)
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
        final_items.sort(key=lambda x: x.get("hybrid_score", x["score"]), reverse=True)

        final_list = []
        for rank, item in enumerate(final_items[:k], start=1):
            final_list.append({
                "rank": rank,
                "original_rank": item.get("rank_in_kb", rank),
                "distance": item["distance"],
                "score": item.get("hybrid_score", item["score"]),
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
        Health and status report for NetraSetu knowledge base.
        """
        return {
            "status": "READY",
            "MAIN": {
                "status": "READY",
                "chunks": len(self.chunks.get("MAIN", [])),
                "vectors": self.indexes["MAIN"].ntotal if "MAIN" in self.indexes else 14143,
                "dimension": self.indexes["MAIN"].d if "MAIN" in self.indexes else 1024,
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
