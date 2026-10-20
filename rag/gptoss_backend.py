import os
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq


# ============================================================
# PATHS
# ============================================================

RAG_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = RAG_DIR / "chunks_new.json"
FAISS_FILE = RAG_DIR / "faiss_new.index"


# ============================================================
# CONFIG
# ============================================================

MODEL_NAME = "BAAI/bge-m3"
GROQ_MODEL = "openai/gpt-oss-120b"


# ============================================================
# LOAD MAIN KNOWLEDGE BASE ONCE
# ============================================================

print("[GPT-OSS BACKEND] Loading Main KB...")

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(
    f"[GPT-OSS BACKEND] Loaded {len(chunks)} chunks."
)


print("[GPT-OSS BACKEND] Loading FAISS...")

index = faiss.read_index(
    str(FAISS_FILE)
)

print(
    f"[GPT-OSS BACKEND] FAISS vectors: "
    f"{index.ntotal}"
)


# ============================================================
# LOAD BGE-M3 ONCE
# ============================================================

print("[GPT-OSS BACKEND] Loading BGE-M3...")

embedding_model = SentenceTransformer(
    MODEL_NAME,
    device="cpu",
)

print("[GPT-OSS BACKEND] BGE-M3 loaded.")


# ============================================================
# GROQ / GPT-OSS
# ============================================================

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found. "
        "Set your Groq API key as an environment variable."
    )

client = Groq(
    api_key=api_key
)

print("[GPT-OSS BACKEND] Groq connected.")
print(
    f"[GPT-OSS BACKEND] Model: {GROQ_MODEL}"
)


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve(
    query,
    k=8,
):

    query = str(query).strip()

    if not query:
        return []

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32",
    )

    distances, indices = index.search(
        query_embedding,
        k,
    )

    results = []

    for rank, (distance, idx) in enumerate(
        zip(
            distances[0],
            indices[0],
        ),
        start=1,
    ):

        if idx == -1:
            continue

        chunk = chunks[idx]

        results.append(
            {
                "rank": rank,
                "distance": float(distance),
                "text": chunk["text"],
                "metadata": chunk.get(
                    "metadata",
                    {},
                ),
            }
        )

    return results


# ============================================================
# GPT-OSS GENERATION
# ============================================================

def generate_gptoss(
    system_prompt,
    user_prompt,
    reasoning_effort="low",
    max_tokens=1200,
):

    response = client.chat.completions.create(
        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        reasoning_effort=reasoning_effort,

        temperature=0.2,

        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


# ============================================================
# EVIDENCE FORMATTER
# ============================================================

def format_evidence(
    results,
):

    if not results:
        return "No retrieved evidence."

    parts = []

    for r in results:

        metadata = r.get(
            "metadata",
            {},
        )

        parts.append(
            f"""
SOURCE {r['rank']}

Document:
{metadata.get('document', 'Unknown')}

Page:
{metadata.get('page', 'Unknown')}

Source:
{metadata.get('source_file', 'Unknown')}

Evidence:
{r['text']}
"""
        )

    return "\n".join(parts)