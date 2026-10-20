from typing import Any, Dict, List

try:
    from FlagEmbedding import FlagReranker
except ImportError:
    FlagReranker = None


MODEL_NAME = "BAAI/bge-reranker-v2-m3"

_MODEL_CACHE: Dict[tuple, Any] = {}


def get_flag_reranker(model_name: str = MODEL_NAME, use_fp16: bool = False):
    global _MODEL_CACHE
    cache_key = (model_name, use_fp16)
    if cache_key not in _MODEL_CACHE:
        if FlagReranker is not None:
            try:
                _MODEL_CACHE[cache_key] = FlagReranker(
                    model_name,
                    use_fp16=use_fp16,
                )
            except Exception as e:
                print(f"[EvidenceReranker] Warning: Could not initialize FlagReranker ({e}). Using similarity score fallback.")
                _MODEL_CACHE[cache_key] = None
        else:
            _MODEL_CACHE[cache_key] = None
    return _MODEL_CACHE[cache_key]


class EvidenceReranker:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        use_fp16: bool = False,
    ):
        self.model_name = model_name
        self.reranker = get_flag_reranker(model_name, use_fp16=use_fp16)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 8,
    ) -> List[Dict[str, Any]]:

        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        if not candidates:
            return []

        if self.reranker is not None:
            pairs = [
                [
                    query,
                    candidate["text"],
                ]
                for candidate in candidates
            ]

            scores = self.reranker.compute_score(
                pairs,
                normalize=True,
            )

            if isinstance(scores, float):
                scores = [scores]

            ranked = []

            for index, candidate in enumerate(candidates):
                item = dict(candidate)

                item["reranker_score"] = float(
                    scores[index]
                )

                item["original_rank"] = int(
                    candidate.get(
                        "rank",
                        index + 1,
                    )
                )

                ranked.append(item)

            ranked.sort(
                key=lambda item: item["reranker_score"],
                reverse=True,
            )

            final = []

            for rank, item in enumerate(
                ranked[:top_k],
                start=1,
            ):
                item["rerank_rank"] = rank
                final.append(item)

            return final

        # Resilient fallback ranking by candidate similarity
        ranked = []
        for index, candidate in enumerate(candidates):
            item = dict(candidate)
            item["reranker_score"] = float(candidate.get("similarity", 1.0 / (index + 1)))
            item["original_rank"] = int(candidate.get("rank", index + 1))
            ranked.append(item)

        ranked.sort(
            key=lambda item: item["reranker_score"],
            reverse=True,
        )

        final = []
        for rank, item in enumerate(
            ranked[:top_k],
            start=1,
        ):
            item["rerank_rank"] = rank
            final.append(item)

        return final


def rerank_evidence(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 8,
    model_name: str = MODEL_NAME,
) -> List[Dict[str, Any]]:

    reranker = EvidenceReranker(
        model_name=model_name,
    )

    return reranker.rerank(
        query=query,
        candidates=candidates,
        top_k=top_k,
    )
