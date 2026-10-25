from rag.multi_kb_retriever import MultiKBRetriever


def test_bm25_candidate_search_finds_specific_clause_and_keeps_provenance():
    retriever = object.__new__(MultiKBRetriever)
    retriever.chunks = {
        "MAIN": [
            {
                "text": "Table of contents: Network slicing security, page 10",
                "metadata": {"jurisdiction": "International", "document": "Standard A", "page": 1},
            },
            {
                "text": "5.15.1 Network slice security requirements. Network slices shall enforce isolation between tenants and apply security controls.",
                "metadata": {"jurisdiction": "International", "document": "Standard A", "page": 42, "clause": "5.15.1"},
            },
            {
                "text": "Routine subscriber administration and billing processes.",
                "metadata": {"jurisdiction": "India", "document": "Policy B", "page": 3},
            },
        ]
    }
    retriever.active_generation_id = "GEN-TEST"

    results = retriever._search_bm25_single_kb(
        query="network slice security tenant isolation",
        kb_name="MAIN",
        k=3,
        allowed_jurisdictions={"International"},
    )

    assert results
    assert results[0]["metadata"]["clause"] == "5.15.1"
    assert results[0]["metadata"]["page"] == 42
    assert results[0]["metadata"]["index_generation_id"] == "GEN-TEST"
    assert all(item["metadata"]["jurisdiction"] == "International" for item in results)


def test_hybrid_rank_fuses_dense_and_lexical_candidates_without_losing_either():
    semantic = [{"kb": "MAIN", "vector_id": 1, "rank_in_kb": 1, "score": 0.9, "distance": 0.9, "text": "Dense candidate"}]
    lexical = [{"kb": "MAIN", "vector_id": 2, "rank_in_kb": 1, "score": 12.0, "distance": 12.0, "text": "Clause candidate"}]

    merged = MultiKBRetriever._merge_hybrid_candidates(semantic, lexical, limit=2)

    assert {item["vector_id"] for item in merged} == {1, 2}
    assert all(0 < item["hybrid_score"] <= 1 for item in merged)
