from dataclasses import dataclass, field
from typing import Any, Dict, List


EVIDENCE_ROLES = [
    "Supporting Evidence",
    "Contradicting Evidence",
    "Contextual Evidence",
]


@dataclass
class RerankedEvidence:
    evidence_id: str
    original_rank: int
    rerank_rank: int

    retrieval_score: float
    reranker_score: float

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    role: str = "Contextual Evidence"
    role_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "original_rank": self.original_rank,
            "rerank_rank": self.rerank_rank,
            "retrieval_score": self.retrieval_score,
            "reranker_score": self.reranker_score,
            "text": self.text,
            "metadata": self.metadata,
            "role": self.role,
            "role_confidence": self.role_confidence,
        }


@dataclass
class EvidenceAnalysisResult:
    supporting_evidence: List[Dict[str, Any]]
    contradicting_evidence: List[Dict[str, Any]]
    contextual_evidence: List[Dict[str, Any]]
    evidence_gaps: List[str]

    candidate_count: int
    final_top_k: int

    contradiction_search_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "contextual_evidence": self.contextual_evidence,
            "evidence_gaps": self.evidence_gaps,
            "candidate_count": self.candidate_count,
            "final_top_k": self.final_top_k,
            "contradiction_search_performed": (
                self.contradiction_search_performed
            ),
        }