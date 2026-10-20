from Backend.evidence_reranking.reranker import (
    EvidenceReranker,
)


class FakeReranker:
    def compute_score(
        self,
        pairs,
        normalize=True,
    ):
        return [
            0.20,
            0.95,
            0.55,
        ]


def test_reranker_orders_candidates():

    reranker = EvidenceReranker.__new__(
        EvidenceReranker
    )

    reranker.model_name = "TEST_MODEL"
    reranker.reranker = FakeReranker()

    candidates = [
        {
            "rank": 1,
            "text": "Weak evidence",
        },
        {
            "rank": 2,
            "text": "Strong evidence",
        },
        {
            "rank": 3,
            "text": "Medium evidence",
        },
    ]

    result = reranker.rerank(
        query="test query",
        candidates=candidates,
        top_k=2,
    )

    assert len(result) == 2

    assert result[0]["text"] == "Strong evidence"
    assert result[1]["text"] == "Medium evidence"

    assert result[0]["rerank_rank"] == 1
    assert result[1]["rerank_rank"] == 2

    assert result[0]["reranker_score"] > (
        result[1]["reranker_score"]
    )


def test_empty_candidates():

    reranker = EvidenceReranker.__new__(
        EvidenceReranker
    )

    reranker.model_name = "TEST_MODEL"
    reranker.reranker = FakeReranker()

    result = reranker.rerank(
        query="test",
        candidates=[],
        top_k=5,
    )

    assert result == []