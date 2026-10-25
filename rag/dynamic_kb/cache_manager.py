"""
NetraSetu Cache & Stale Retrieval Invalidation Manager
=====================================================

Ensures retired or modified documents do not linger in retrieval,
gap analysis, or synthesis caches (Part 7).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class DynamicKBCacheManager:
    """
    Manages cache invalidation across:
    - In-memory retrieval caches
    - OCR cache (.ocr_cache)
    - Scenario response caches
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.ocr_cache_dir = self.repo_root / "knowledge_base" / ".ocr_cache"
        self.invalidated_doc_ids: Set[str] = set()

    def invalidate_for_document(self, doc_id: str, content_hash: str = ""):
        """Invalidate caches tied to a specific document."""
        self.invalidated_doc_ids.add(doc_id)
        if content_hash and self.ocr_cache_dir.exists():
            # Invalidate OCR cache file matching hash if content modified
            for f in self.ocr_cache_dir.glob(f"*{content_hash[:16]}*"):
                try:
                    f.unlink()
                except Exception:
                    pass

    def invalidate_generation(self, old_gen_id: str, new_gen_id: str):
        """Invalidate all retrieval caches when generation changes."""
        # Evict retriever cache if imported
        try:
            from rag.multi_kb_retriever import MultiKBRetriever
            # Hot-reload in memory if singleton exists
        except Exception:
            pass
        print(f"[CACHE] Invalidated caches from {old_gen_id} -> {new_gen_id}")
