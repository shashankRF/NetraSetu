from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class RevisionType(str, Enum):
    AMENDMENT = "AMENDMENT"
    REPEAL_AND_REPLACE = "REPEAL_AND_REPLACE"
    STATUTORY_DIRECTION = "STATUTORY_DIRECTION"
    STANDARD_VERSION_BUMP = "STANDARD_VERSION_BUMP"


class ImpactSeverity(str, Enum):
    HIGH = "HIGH"         # Invalidates existing evidence or introduces mandatory penal obligations
    MEDIUM = "MEDIUM"     # Adjusts reporting thresholds, timelines, or technical specifications
    LOW = "LOW"           # Editorial, terminology alignment, or non-binding clarifications


@dataclass
class DocumentRevision:
    revision_id: str
    document_id: str
    document_title: str
    previous_version_date: str
    new_version_date: str
    revision_type: RevisionType
    summary: str
    affected_clauses: List[str]
    is_active: bool = True


@dataclass
class EvidenceDependency:
    chunk_id: str
    document_id: str
    clause_reference: str
    page_number: int
    dependent_scenarios: List[str]
    dependent_rules: List[str]
    last_verified_version: str


@dataclass
class ImpactAssessmentPlan:
    plan_id: str
    revision_id: str
    status: str                        # "ARCHITECTURAL_PLAN", "READY_FOR_EVALUATION", "NOT_YET_TESTED"
    affected_evidence_chunks: List[str]
    affected_scenarios: List[str]
    re_evaluation_triggers: List[str]
    implementation_status: str = "PLANNED_PHASE_2"
    testing_verified: bool = False     # Explicit safety invariant: Do not claim implemented until tested
