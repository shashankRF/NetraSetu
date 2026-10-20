from typing import Any, Dict, List, Optional

from .reranker import EvidenceReranker
from .evidence_analyzer import analyze_evidence
from .counter_evidence import build_counter_query


class EvidenceRankingPipeline:
    """
    Evidence ranking pipeline.

    FULL mode:
        Reranks the complete candidate set supplied by the caller.

    DEMO/COMPACT mode:
        Allows the caller to explicitly bound the number of candidates
        sent to the expensive cross-encoder reranker.

    Important:
        The evidence architecture is unchanged.
        Candidate reduction is only a computational optimization.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
    ):
        self.reranker = EvidenceReranker(
            model_name=model_name
        )

    def run(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        final_top_k: int = 8,
        candidate_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run evidence reranking and evidence-role analysis.

        Parameters
        ----------
        query:
            Original or counter-evidence query.

        candidates:
            Retrieved evidence candidates.

        final_top_k:
            Number of reranked evidence records to retain.

        candidate_limit:
            Optional upper bound on the number of candidates passed
            to the expensive cross-encoder reranker.

            None = FULL mode.
            Integer = bounded/compact mode.

        Returns
        -------
        Dict containing:
            query
            candidate_count
            reranker_candidate_count
            reranked_evidence
            evidence_analysis
            counter_evidence_query
        """

        if not query or not query.strip():
            raise ValueError(
                "Evidence ranking query cannot be empty."
            )

        if candidates is None:
            candidates = []

        original_candidate_count = len(candidates)

        # ---------------------------------------------------------
        # BOUNDED DEMO CANDIDATE SET
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        # We preserve the retrieval ordering here.
        # The expensive cross-encoder then evaluates only the
        # bounded candidate set in demo mode.
        #
        # FULL mode is unchanged when candidate_limit=None.
        # ---------------------------------------------------------

        ranking_candidates = list(candidates)

        if candidate_limit is not None:
            if candidate_limit < 1:
                raise ValueError(
                    "candidate_limit must be >= 1."
                )

            ranking_candidates = ranking_candidates[
                :candidate_limit
            ]

        if not ranking_candidates:
            return {
                "query": query,
                "candidate_count": original_candidate_count,
                "reranker_candidate_count": 0,
                "reranked_evidence": [],
                "evidence_analysis": {
                    "supporting_evidence": [],
                    "contradicting_evidence": [],
                    "contextual_evidence": [],
                    "evidence_gaps": [],
                    "candidate_count": 0,
                    "final_top_k": final_top_k,
                    "contradiction_search_performed": False,
                },
                "counter_evidence_query": build_counter_query(
                    query
                ),
            }

        # ---------------------------------------------------------
        # EXPENSIVE CROSS-ENCODER RERANKING
        # ---------------------------------------------------------

        reranked = self.reranker.rerank(
            query=query,
            candidates=ranking_candidates,
            top_k=final_top_k,
        )

        # ---------------------------------------------------------
        # DETERMINISTIC EVIDENCE ROLE ANALYSIS
        # ---------------------------------------------------------

        analysis = analyze_evidence(
            candidates=reranked,
            query=query,
            final_top_k=final_top_k,
        )

        return {
            "query": query,

            # Number retrieved before compacting.
            "candidate_count": original_candidate_count,

            # Number actually passed into BGE reranker.
            "reranker_candidate_count": len(
                ranking_candidates
            ),

            "reranked_evidence": reranked,

            "evidence_analysis": analysis.to_dict(),

            "counter_evidence_query": build_counter_query(
                query
            ),
        }


def run_evidence_ranking(
    query: str,
    candidates: List[Dict[str, Any]],
    final_top_k: int = 8,
    candidate_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper.

    FULL:
        candidate_limit=None

    DEMO:
        candidate_limit=5 / 6 / etc.
    """

    pipeline = EvidenceRankingPipeline()

    return pipeline.run(
        query=query,
        candidates=candidates,
        final_top_k=final_top_k,
        candidate_limit=candidate_limit,
    )