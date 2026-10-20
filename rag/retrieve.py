import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# -----------------------------
# Load data
# -----------------------------

print("Loading chunks...")
with open("chunks_new.json", "r", encoding="utf-8") as f:

print(f"Loaded {len(chunks)} chunks.")

print("Loading FAISS index...")
index = faiss.read_index("faiss.index")

print(f"FAISS vectors: {index.ntotal}")

print("Loading BGE-M3...")
model = SentenceTransformer("BAAI/bge-m3", device="cpu")

print("Ready.\n")


# -----------------------------
# Retrieval function
# -----------------------------

def retrieve(query, k=5):

    # Convert query to embedding
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32"
    )

    # Search FAISS
    distances, indices = index.search(
        query_embedding,
        k
    )

    results = []

    for rank, (distance, idx) in enumerate(
        zip(distances[0], indices[0]),
        start=1
    ):

        if idx == -1:
            continue

        chunk = chunks[idx]

        results.append({
            "rank": rank,
            "score": float(distance),
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "metadata": chunk["metadata"]
        })

    return results


# -----------------------------
# Interactive search
# -----------------------------

while True:

    query = input("\nEnter your question (or type 'exit'): ")

    if query.lower() == "exit":
        break

    results = retrieve(query, k=5)

    print("\n" + "=" * 80)
    print("RETRIEVED RESULTS")
    print("=" * 80)

    for r in results:

        print(f"\n--- Rank {r['rank']} ---")
        print(f"Distance: {r['score']:.4f}")
        print(f"Chunk ID: {r['chunk_id']}")
        print(f"Document: {r['metadata'].get('document')}")
        print(f"Page: {r['metadata'].get('page')}")
        print(f"Source: {r['metadata'].get('source_file')}")
        print("\nText:")
        print(r["text"])