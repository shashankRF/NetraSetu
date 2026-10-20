"""
Regional Comparative Gap Analysis Module for HackGrid.
Extends jurisdiction-aware gap analysis with host, international, and regional comparative evidence layers.
Preserves strict legal separation between host applicable law and regional comparative evidence.
"""

from .models import (
    JurisdictionRole,
    RegionalRelationshipType,
    RegionalGapStatus,
    RegionalActionType,
    RegionalCoverageStatus,
    RegionalEvidenceItem,
    RegionalComparisonMapping,
    RegionalComparativeAnalysisResult,
)
from .engine import RegionalComparativeGapEngine
from .formatter import format_regional_comparative_markdown
from .claim_guardrail import validate_regional_claims
from .jurisdiction_matrix import (
    get_relevant_regional_jurisdictions,
    assess_regional_kb_coverage,
)

__all__ = [
    "JurisdictionRole",
    "RegionalRelationshipType",
    "RegionalGapStatus",
    "RegionalActionType",
    "RegionalCoverageStatus",
    "RegionalEvidenceItem",
    "RegionalComparisonMapping",
    "RegionalComparativeAnalysisResult",
    "RegionalComparativeGapEngine",
    "format_regional_comparative_markdown",
    "validate_regional_claims",
    "get_relevant_regional_jurisdictions",
    "assess_regional_kb_coverage",
]
