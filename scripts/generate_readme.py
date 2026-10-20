# Script to update and regenerate README.md with latest multi-domain KB counts
import os
import re

README_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")

def update_readme():
    with open(README_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. At a Glance
    text = text.replace(
        "| **Validated Knowledge Base** | 14,143 indexed regulatory and technical chunks | `rag/chunks_new.json` (72 verified source documents) |",
        "| **Validated Knowledge Base** | 14,813 total indexed chunks across 3 active KBs (Main: 14,143, Defence: 397, Maritime: 273) | `rag/chunks_new.json`, `rag/DEFENCE CHUNKS/`, `rag/MARITIME CHUNKS/` |"
    )

    # 2. Mechanism in Section 4.1
    old_mech = "* **Mechanism**: In `rag/retrieval.py`, candidate retrieval expands candidate depth ($10 \\times K$, minimum 100 candidates) against the 14,143-chunk FAISS index, then deterministically prunes records whose metadata does not match the active `JurisdictionProfile`."
    new_mech = "* **Mechanism**: In `rag/multi_kb_retriever.py` and `rag/retrieval.py`, candidate retrieval queries the 14,143-chunk Main FAISS index alongside active domain indices (Defence: 397 chunks, Maritime: 273 chunks), expanding candidate depth ($10 \\times K$, minimum 100 candidates per active index) before applying deterministic jurisdiction profile pruning."
    if old_mech in text:
        text = text.replace(old_mech, new_mech)

    # 3. Section 8 Technical Specification
    old_spec = """### Technical Specification
* **Model**: `BAAI/bge-m3` loaded via `sentence-transformers` on CPU/device.
* **Embeddings File**: `rag/embeddings_new.npy` (57.9 MB, 14,143 vectors $\\times$ 1,024 float32).
* **Index File**: `rag/faiss_new.index` (57.9 MB, `IndexFlatIP` inner product on L2-normalized vectors).
* **Dynamic Candidate Expansion**: To prevent false negatives during geographic filtering, FAISS retrieves $\\max(K \\times 10, 100)$ candidates before pruning."""

    new_spec = """### Technical Specification
* **Model**: `BAAI/bge-m3` loaded via `sentence-transformers` on CPU/device (shared singleton across all knowledge bases).
* **Embeddings Files**:
  * Main: `rag/embeddings_new.npy` (57.9 MB, 14,143 vectors $\\times$ 1,024 float32).
  * Defence: `rag/DEFENCE CHUNKS/defence_embeddings.npy` (1.6 MB, 397 vectors $\\times$ 1,024 float32).
  * Maritime: `rag/MARITIME CHUNKS/maritime_embeddings.npy` (1.1 MB, 273 vectors $\\times$ 1,024 float32).
* **Index Files**: Compiled FAISS `IndexFlatIP` indices on L2-normalized dense vectors:
  * Main: `rag/faiss_new.index` (14,143 vectors)
  * Defence: `rag/DEFENCE CHUNKS/defence_faiss.index` (397 vectors)
  * Maritime: `rag/MARITIME CHUNKS/maritime_faiss.index` (273 vectors)
* **Total Indexed Corpus**: 14,813 verified dense vectors across 3 operational indices.
* **Dynamic Candidate Expansion & Quota Pooling**: Retrieves $\\max(K \\times 10, 100)$ candidates per active KB, enforces proportional quota pooling (Main $\\ge 40-50\\%$, domain KBs $\\ge 2-4$ candidates), and annotates source provenance (`kb`: `"MAIN"` | `"DEFENCE"` | `"MARITIME"`)."""
    if old_spec in text:
        text = text.replace(old_spec, new_spec)

    # 4. Section 9 Knowledge Base Architecture Diagram & Inventory
    old_kb_sec = """```mermaid
flowchart TD
    subgraph Knowledge_Bases [HackGrid Knowledge Bases]
        MainKB[Main Production KB<br/>14,143 Chunks<br/>Status: ACTIVE LIVE]
        MaritimeKB[Maritime KB<br/>Directory: rag/MARITIME CHUNKS<br/>Status: In Repo / Fallback to Main]
        DefenceKB[Defence KB<br/>Directory: rag/DEFENCE CHUNKS<br/>Status: In Repo / Fallback to Main]
    end

    MainKB --> UnifiedRetriever[Multi-KB Retriever Engine]
    MaritimeKB -.->|When populated| UnifiedRetriever
    DefenceKB -.->|When populated| UnifiedRetriever
    UnifiedRetriever --> Pipeline[HackGrid Production Pipeline]
```

### Knowledge Base Inventory

| Knowledge Base | Chunks | FAISS Index | Chunk File | Live Pipeline Status |
|---|---|---|---|---|
| **Main KB** | **14,143** | `rag/faiss_new.index` | `rag/chunks_new.json` | **ACTIVE (Canonical Production Knowledge Base)** |
| **Maritime KB** | 0 | `rag/MARITIME CHUNKS/` | `maritime_chunks.json` | *Available in repository; falls back to Main KB in live retrieval* |
| **Defence KB** | 0 | `rag/DEFENCE CHUNKS/` | `defence_chunks.json` | *Available in repository; falls back to Main KB in live retrieval* |

> [!NOTE]
> `rag/multi_kb_retriever.py` provides multi-index federation logic. If domain indices are empty or unbuilt, the system deterministically executes retrieval against the Main KB (which already contains extensive maritime, defence, telecom, and statutory documents)."""

    new_kb_sec = """```mermaid
flowchart TD
    subgraph Knowledge_Bases [HackGrid Multi-Domain Knowledge Bases]
        MainKB[Main Production KB<br/>14,143 Chunks<br/>Status: ACTIVE LIVE]
        MaritimeKB[Maritime Domain KB<br/>273 Chunks<br/>Status: ACTIVE LIVE]
        DefenceKB[Defence Domain KB<br/>397 Chunks<br/>Status: ACTIVE LIVE]
    end

    MainKB --> UnifiedRetriever[Unified Multi-KB Retriever Engine]
    MaritimeKB -->|Domain Routing + Quota Pooling| UnifiedRetriever
    DefenceKB -->|Domain Routing + Quota Pooling| UnifiedRetriever
    UnifiedRetriever --> Pipeline[HackGrid Production Pipeline]
```

### Knowledge Base Inventory

| Knowledge Base | Chunks | Vectors | Dimension | FAISS Index | Chunk File | Live Pipeline Status |
|---|---|---|---|---|---|---|
| **Main KB** | **14,143** | 14,143 | 1,024 | `rag/faiss_new.index` | `rag/chunks_new.json` | **ACTIVE (Canonical Production KB — Always Searched)** |
| **Defence KB** | **397** | 397 | 1,024 | `rag/DEFENCE CHUNKS/defence_faiss.index` | `defence_chunks.json` | **ACTIVE (Domain-Routed: DRDO, Drone Rules, NATO UAS)** |
| **Maritime KB** | **273** | 273 | 1,024 | `rag/MARITIME CHUNKS/maritime_faiss.index` | `maritime_chunks.json` | **ACTIVE (Domain-Routed: IMO MSC, NOSDCP, AIS Protocols)** |
| **Total Corpus** | **14,813** | **14,813** | **1,024** | **3 Active FAISS Indices** | **3 Correlated Corpora** | **UNIFIED MULTI-DOMAIN RETRIEVAL** |

> [!NOTE]
> `rag/multi_kb_retriever.py` provides multi-index federation logic, quota-based candidate pooling (MAIN guaranteed $\\ge 40-50\\%$, domain KBs guaranteed $\\ge 2-4$ candidates), and source provenance tracking (`kb`: `"MAIN"` | `"DEFENCE"` | `"MARITIME"`). Domain queries seamlessly aggregate candidates across relevant indices with strict attribution."""
    if old_kb_sec in text:
        text = text.replace(old_kb_sec, new_kb_sec)

    # 5. Section 10 Chunk Corpus Breakdown
    old_breakdown = """### Chunk Corpus Breakdown (14,143 Chunks Total)

* **By Regulatory Category**:
  * `3gpp` (Technical Specifications): 6,032 chunks
  * `DoT_Rules` (Indian Department of Telecommunications): 2,561 chunks
  * `EU Rules` (European Union Directives & Regulations): 1,364 chunks
  * `TRAI_Act` (Telecom Regulatory Authority of India): 1,222 chunks
  * `General` (Foundational Technical Papers & RFCs): 915 chunks
  * `TEC Guidelines` (Telecommunication Engineering Centre): 650 chunks
  * `Indian_Acts` (Information Technology & Telecommunications Acts): 498 chunks
  * `MTCTE Regulations` (Mandatory Testing & Certification): 452 chunks
  * `ITU_Rules_Framework` (International Telecommunication Union): 322 chunks
  * `DPDP Acts` (Digital Personal Data Protection Act): 127 chunks"""

    new_breakdown = """### Chunk Corpus Breakdown (14,813 Chunks Total)

* **Main Knowledge Base (14,143 Chunks)**:
  * `3gpp` (Technical Specifications): 6,032 chunks
  * `DoT_Rules` (Indian Department of Telecommunications): 2,561 chunks
  * `EU Rules` (European Union Directives & Regulations): 1,364 chunks
  * `TRAI_Act` (Telecom Regulatory Authority of India): 1,222 chunks
  * `General` (Foundational Technical Papers & RFCs): 915 chunks
  * `TEC Guidelines` (Telecommunication Engineering Centre): 650 chunks
  * `Indian_Acts` (Information Technology & Telecommunications Acts): 498 chunks
  * `MTCTE Regulations` (Mandatory Testing & Certification): 452 chunks
  * `ITU_Rules_Framework` (International Telecommunication Union): 322 chunks
  * `DPDP Acts` (Digital Personal Data Protection Act): 127 chunks

* **Defence Knowledge Base (397 Chunks)**:
  * `DRDO_ToT_Policy2025.pdf`: 245 chunks (Transfer of Technology, licensing, defence R&D)
  * `Drone Rules 2021.pdf`: 84 chunks (Indian UAS zoning, classification, certification)
  * `UAS_CONEMP NATO.pdf`: 68 chunks (NATO Concept of Employment for Unmanned Aircraft Systems)

* **Maritime Knowledge Base (273 Chunks)**:
  * `NOSDCP Circular 01 - 2025 INDIA.pdf`: 121 chunks (National Oil Spill Disaster Contingency Plan)
  * `MSC.570(109) IMO.pdf`: 62 chunks (IMO Maritime Safety Committee resolutions)
  * `MSC.74(69).pdf`: 48 chunks (IMO performance standards for navigational equipment & AIS)
  * `A.1106(29) 2015.pdf`: 42 chunks (Revised guidelines for shipborne automatic identification)"""
    if old_breakdown in text:
        text = text.replace(old_breakdown, new_breakdown)

    # 6. Section 15 Dependency Table
    text = text.replace(
        "| **Vector Database** | `faiss-cpu` | 1.15.1 | In-memory similarity search over 14,143 vectors |",
        "| **Vector Database** | `faiss-cpu` | 1.15.1 | In-memory similarity search over 14,813 vectors across 3 KBs |"
    )

    # 7. Section 27 Directory Tree
    old_tree = """├── rag/                                  # RAG vector retrieval & specialist agents
│   ├── chunks_new.json                   # 14,143 chunk knowledge base (18.1 MB)
│   ├── embeddings_new.npy                # 14,143 dense 1024-dim BGE-M3 vectors (57.9 MB)
│   ├── faiss_new.index                   # Compiled FAISS IndexFlatIP index (57.9 MB)
│   ├── retrieval.py                      # Core BGE-M3 + FAISS retrieval with jurisdiction profiles
│   ├── gptoss_backend.py                 # Groq client integration for GPT-OSS 120B
│   ├── orchestrator.py                   # Concurrent specialist multi-agent orchestrator
│   ├── network_agent.py                  # 5G Network architecture analysis specialist
│   ├── compliance_agent.py               # Regulatory compliance specialist
│   ├── policy_agent.py                   # Policy & standards landscape specialist
│   ├── gap_analysis_agent.py             # Specialist gap analysis synthesizer
│   ├── multi_kb_retriever.py             # Multi-index retrieval federation logic
│   ├── DEFENCE CHUNKS/                   # Dedicated Defence KB index (in-repo structure)
│   └── MARITIME CHUNKS/                  # Dedicated Maritime KB index (in-repo structure)"""

    new_tree = """├── rag/                                  # RAG vector retrieval & specialist agents
│   ├── chunks_new.json                   # Main KB: 14,143 chunks (18.1 MB)
│   ├── embeddings_new.npy                # Main KB: 14,143 dense 1024-dim BGE-M3 vectors (57.9 MB)
│   ├── faiss_new.index                   # Main KB: Compiled FAISS IndexFlatIP index (57.9 MB)
│   ├── retrieval.py                      # Retrieval facade & compatibility layer
│   ├── multi_kb_retriever.py             # UnifiedMultiKBRetriever singleton & quota candidate pooling
│   ├── gptoss_backend.py                 # Groq client integration for GPT-OSS 120B
│   ├── orchestrator.py                   # Concurrent specialist multi-agent orchestrator
│   ├── network_agent.py                  # 5G Network architecture analysis specialist
│   ├── compliance_agent.py               # Regulatory compliance specialist
│   ├── policy_agent.py                   # Policy & standards landscape specialist
│   ├── gap_analysis_agent.py             # Specialist gap analysis synthesizer
│   ├── DEFENCE CHUNKS/                   # Dedicated Defence KB index (397 chunks, 1024-d, IndexFlatIP)
│   └── MARITIME CHUNKS/                  # Dedicated Maritime KB index (273 chunks, 1024-d, IndexFlatIP)"""
    if old_tree in text:
        text = text.replace(old_tree, new_tree)

    # 8. Section 32 Why HackGrid is Different
    text = text.replace(
        "| **Primary Grounding** | Unranked text chunks | Model conversational context | **Verified 14,143-chunk statutory/standards KB** |",
        "| **Primary Grounding** | Unranked text chunks | Model conversational context | **Verified 14,813-chunk statutory/standards corpus across 3 KBs** |"
    )

    # 9. Section 36 Limitations
    old_lim = """* **Corpus Boundedness**: HackGrid's factual horizon is bounded by its 14,143 indexed chunks. Novel circulars issued after indexing require manual ingestion.
* **Probabilistic Synthesis**: While grounded in evidence, language-model synthesis can exhibit phrasing variance across identical contexts.
* **Domain KB Integration**: The dedicated Defence and Maritime chunk indices exist physically as repository scaffolds but currently fall back to the Main KB in unified live querying.
* **Non-Legal Finality**: HackGrid provides technical and regulatory **decision support**. It does not substitute for qualified legal counsel or statutory government gazettes."""

    new_lim = """* **Corpus Boundedness**: HackGrid's factual horizon is bounded by its 14,813 indexed chunks across the Main, Defence, and Maritime repositories. Novel circulars issued after indexing require manual ingestion.
* **Probabilistic Synthesis**: While grounded in evidence, language-model synthesis can exhibit phrasing variance across identical contexts.
* **Non-Legal Finality**: HackGrid provides technical and regulatory **decision support**. It does not substitute for qualified legal counsel or statutory government gazettes."""
    if old_lim in text:
        text = text.replace(old_lim, new_lim)

    # 10. Section 37 Future Roadmap
    old_roadmap = """CURRENT (v1.0 Baseline)
  ├── 14,143-chunk Main Knowledge Base active
  ├── 10-stage production orchestrator with GPT-OSS 120B
  ├── Deterministic Risk Engine & Governance Layer
  └── Interactive Web Console & Forensic Audit Trail

NEAR TERM (v1.1)
  ├── Live compilation and active routing for dedicated Maritime & Defence KB indices
  ├── Hybrid sparse/dense retrieval (BM25 + BGE-M3 reciprocal rank fusion)
  └── Multi-reviewer append-only audit recording on audit entries"""

    new_roadmap = """CURRENT (v1.1 Multi-Domain Operational)
  ├── 14,813 total chunks across 3 active Knowledge Bases (Main: 14,143, Defence: 397, Maritime: 273)
  ├── Unified multi-KB retrieval with quota candidate pooling & source provenance
  ├── 10-stage production orchestrator with GPT-OSS 120B
  ├── Deterministic Risk Engine & Governance Layer
  └── Interactive Web Console & Forensic Audit Trail

NEAR TERM (v1.2)
  ├── Hybrid sparse/dense retrieval (BM25 + BGE-M3 reciprocal rank fusion)
  └── Multi-reviewer append-only audit recording on audit entries"""
    if old_roadmap in text:
        text = text.replace(old_roadmap, new_roadmap)

    # 11. Section 42 Reproducibility
    old_repro = """1. Ensure the canonical 14,143-chunk index artifacts are present in `rag/`:
   * `chunks_new.json` (SHA256 verified)
   * `embeddings_new.npy` (Dense 1,024-dim BGE-M3 matrix)
   * `faiss_new.index` (Inner product index)"""

    new_repro = """1. Ensure the active knowledge base index artifacts are present in `rag/`:
   * Main KB: `chunks_new.json` (14,143 chunks), `embeddings_new.npy`, `faiss_new.index`
   * Defence KB: `rag/DEFENCE CHUNKS/` (397 chunks, `defence_faiss.index`)
   * Maritime KB: `rag/MARITIME CHUNKS/` (273 chunks, `maritime_faiss.index`)"""
    if old_repro in text:
        text = text.replace(old_repro, new_repro)

    # 12. Section 44 Current Implementation Status
    text = text.replace(
        "| **Dedicated Maritime KB Index** | 🟡 **Experimental** | Physical directory scaffold present; falls back to Main KB |",
        "| **Dedicated Maritime KB Index** | ✅ **Implemented** | 273 chunks in FAISS (`maritime_faiss.index`), live domain routing & quota pooling |"
    )
    text = text.replace(
        "| **Dedicated Defence KB Index** | 🟡 **Experimental** | Physical directory scaffold present; falls back to Main KB |",
        "| **Dedicated Defence KB Index** | ✅ **Implemented** | 397 chunks in FAISS (`defence_faiss.index`), live domain routing & quota pooling |"
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print("Successfully updated README.md with 14,813 total chunks across 3 active KBs!")

if __name__ == "__main__":
    update_readme()
