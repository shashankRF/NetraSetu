"""
NetraSetu Dynamic Knowledge Base Data Models
============================================

Authoritative schemas for:
- Document Records and Approval Lifecycles
- Index Generation Manifests and Lineage
- Ingestion Operations and Stage-level Auditing
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceApprovalStatus(str, Enum):
    """Controlled source trust lifecycle stages (Part 6)."""
    DISCOVERED = "DISCOVERED"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_FOR_RETRIEVAL = "APPROVED_FOR_RETRIEVAL"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    INGESTION_FAILED = "INGESTION_FAILED"


class ExtractionStatus(str, Enum):
    NOT_EXTRACTED = "NOT_EXTRACTED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    OCR_EXTRACTED = "OCR_EXTRACTED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


class IndexingStatus(str, Enum):
    UNINDEXED = "UNINDEXED"
    CHUNKS_GENERATED = "CHUNKS_GENERATED"
    EMBEDDINGS_GENERATED = "EMBEDDINGS_GENERATED"
    INDEX_UPDATED = "INDEX_UPDATED"
    INDEX_STAGED = "INDEX_STAGED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass
class DocumentRecord:
    """Authoritative document metadata in the controlled registry (Part 2)."""
    doc_id: str
    filename: str
    title: str
    source_url: str = ""
    local_path: str = ""
    issuing_org: str = ""
    doc_type: str = "PDF"
    jurisdiction: str = "India"
    subject_area: str = "Telecommunications / Emergency Communication"
    publication_date: str = ""
    effective_date: str = ""
    version: str = "1.0"
    ingestion_timestamp: str = ""
    content_hash: str = ""  # SHA-256 of physical file
    extraction_status: str = ExtractionStatus.TEXT_EXTRACTED.value
    indexing_status: str = IndexingStatus.ACTIVE.value
    verification_status: str = "VERIFIED"
    approval_status: str = SourceApprovalStatus.APPROVED_FOR_RETRIEVAL.value
    legal_status: str = "BINDING_STATUTORY"
    active: bool = True
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    chunk_count: int = 0
    chunk_ids: List[str] = field(default_factory=list)
    index_generation_id: str = "GEN-0001"
    metadata_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentRecord":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class IndexGenerationManifest:
    """Provenance and lineage for atomic index generations (Part 4)."""
    generation_id: str
    created_at: str
    vector_count: int
    dimension: int = 1024
    embedding_model: str = "BAAI/bge-m3"
    document_count: int = 0
    active_doc_ids: List[str] = field(default_factory=list)
    active: bool = True
    parent_generation_id: Optional[str] = None
    index_file: str = "faiss_new.index"
    chunks_file: str = "chunks_new.json"
    embeddings_file: str = "embeddings_new.npy"
    checksum: str = ""
    invariants_verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexGenerationManifest":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class IngestionResult:
    """Stage-tracked outcome of incremental ingestion (Part 3 & Part 11)."""
    doc_id: str
    operation: str  # UNCHANGED | METADATA_UPDATED | NEW_INGESTED | VERSION_REPLACED | RETIRED | FAILED
    status: str     # SUCCESS | FAILED | SKIPPED
    generation_id: str
    chunks_added: int = 0
    chunks_removed: int = 0
    total_vectors: int = 0
    extraction_duration_seconds: float = 0.0
    embedding_duration_seconds: float = 0.0
    indexing_duration_seconds: float = 0.0
    total_duration_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
