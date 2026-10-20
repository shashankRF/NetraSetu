import json

with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("=" * 60)
print("CHUNK INSPECTION")
print("=" * 60)

print(f"\nTotal chunks: {len(chunks)}")

for i, chunk in enumerate(chunks[:3], start=1):

    print("\n" + "-" * 60)
    print(f"CHUNK {i}")

    print("\nChunk ID:")
    print(chunk["chunk_id"])

    print("\nMetadata:")
    print(json.dumps(chunk["metadata"], indent=2))

    print("\nText:")
    print(chunk["text"][:1000])

    print("\nCharacter count:")
    print(len(chunk["text"]))


print("\n" + "=" * 60)
print("INSPECTION COMPLETE")
print("=" * 60)