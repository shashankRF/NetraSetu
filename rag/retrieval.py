import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

RAG_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = RAG_DIR / "chunks_new.json"
FAISS_FILE = RAG_DIR / "faiss_new.index"

MODEL_NAME = "BAAI/bge-m3"


# ============================================================
# JURISDICTION PROFILES
# ============================================================

JURISDICTION_PROFILES = {
    "India": {
        "India",
        "International",
    },
    "European Union": {
        "European Union",
        "International",
    },
}


# ============================================================
# UNIFIED RETRIEVER DELEGATION (SINGLETON)
# ============================================================

_retriever = None

def _get_unified():
    global _retriever
    if _retriever is None:
        from rag.multi_kb_retriever import get_unified_retriever
        _retriever = get_unified_retriever()
    return _retriever

class _LazyChunks:
    def __len__(self):
        return len(_get_unified().chunks.get("MAIN", []))
    def __getitem__(self, idx):
        return _get_unified().chunks.get("MAIN", [])[idx]
    def __iter__(self):
        return iter(_get_unified().chunks.get("MAIN", []))

class _LazyIndex:
    @property
    def ntotal(self):
        return _get_unified().indexes["MAIN"].ntotal
    @property
    def d(self):
        return _get_unified().indexes["MAIN"].d
    def search(self, *args, **kwargs):
        return _get_unified().indexes["MAIN"].search(*args, **kwargs)

class _LazyModel:
    def encode(self, *args, **kwargs):
        return _get_unified().model.encode(*args, **kwargs)

chunks = _LazyChunks()
index = _LazyIndex()
embedding_model = _LazyModel()


# ============================================================
# HELPERS
# ============================================================

def _get_jurisdiction(metadata):
    """
    Safely extract jurisdiction from chunk metadata.
    """

    if not isinstance(metadata, dict):
        return None

    value = metadata.get("jurisdiction")

    if value is None:
        return None

    return str(value).strip()


def _validate_jurisdiction(jurisdiction):
    """
    Validate the requested jurisdiction profile.
    """

    if jurisdiction not in JURISDICTION_PROFILES:
        supported = ", ".join(
            JURISDICTION_PROFILES.keys()
        )

        raise ValueError(
                f"Unsupported jurisdiction profile '{jurisdiction}'. "
                f"Supported jurisdiction profiles: {supported}"
        )


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve(
    query,
    k=8,
    jurisdiction=None,
    domains=None,
):
    """
    Jurisdiction-aware multi-KB evidence retrieval.

    Parameters
    ----------
    query : str
        User query.

    k : int
        Number of final evidence records.

    jurisdiction : str | None
        If "India": Only India + International evidence.
        If "European Union": Only European Union + International evidence.

    domains : list | str | None
        Domain hints for specialized KB activation (DEFENCE, MARITIME).
        MAIN KB is always searched regardless of domains.
    """
    from rag.multi_kb_retriever import get_unified_retriever

    query_str = str(query).strip()
    if not query_str:
        return []

    if jurisdiction is not None:
        _validate_jurisdiction(jurisdiction)

    retriever = get_unified_retriever()
    return retriever.retrieve_unified(
        query=query_str,
        k=k,
        jurisdiction=jurisdiction,
        domains=domains,
    )


# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("HACKGRID JURISDICTION-AWARE RETRIEVAL TEST")
    print("=" * 80)

    query = (
        "5G network slicing security requirements"
    )

    for jurisdiction in [
        "India",
        "European Union",
    ]:

        print(
            f"\n--- {jurisdiction} ---"
        )

        results = retrieve(
            query,
            k=8,
            jurisdiction=jurisdiction,
        )

        print(
            f"Returned {len(results)} evidence records."
        )

        jurisdictions = sorted(
            {
                _get_jurisdiction(
                    item.get("metadata", {})
                )
                for item in results
            }
        )

        print(
            "Jurisdictions:",
            jurisdictions,
        )

        for item in results[:3]:

            metadata = item.get(
                "metadata",
                {},
            )

            print(
                f"{item['rank']}. "
                f"{metadata.get('document', 'Unknown')} | "
                f"{metadata.get('jurisdiction', 'Unknown')}"
            )