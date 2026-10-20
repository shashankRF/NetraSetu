from __future__ import annotations
from typing import Dict, List, Optional, Any
from .models import (
    DocumentRevision,
    RevisionType,
    EvidenceDependency,
    ImpactAssessmentPlan,
    ImpactSeverity,
)


class ChangeImpactEngine:
    """
    Change-Impact Engine for Statutory Instruments & Technical Standards.

    SAFETY AND ARCHITECTURAL SPECIFICATION:
    - Preserves existing retrieval and evidence pipeline intact.
    - Tracks document version revisions, affected evidence dependencies, and selective re-evaluation plans.
    - Explicitly reports 'PLANNED_PHASE_2 / NOT_YET_TESTED' until end-to-end continuous diffing is fully operational.
    """

    def __init__(self):
        # Initial repository of tracked statutory revisions
        self.tracked_revisions: Dict[str, DocumentRevision] = {
            "REV-TELECOM-2023": DocumentRevision(
                revision_id="REV-TELECOM-2023",
                document_id="DOT-TELECOM-ACT-2023",
                document_title="Telecommunications Act, 2023",
                previous_version_date="1885-10-01 (Telegraph Act)",
                new_version_date="2023-12-24",
                revision_type=RevisionType.REPEAL_AND_REPLACE,
                summary="Repeals Indian Telegraph Act 1885 and Wireless Telegraphy Act 1933; establishes national security interception and critical telecom infrastructure safeguards.",
                affected_clauses=["Section 3", "Section 4", "Section 7", "Section 22"],
            ),
            "REV-CERTIN-70B-2022": DocumentRevision(
                revision_id="REV-CERTIN-70B-2022",
                document_id="CERTIN-DIR-2022",
                document_title="Directions under Section 70B of IT Act 2000",
                previous_version_date="2013-01-16 (CERT-In Rules 2013)",
                new_version_date="2022-04-28",
                revision_type=RevisionType.STATUTORY_DIRECTION,
                summary="Mandatory reporting of 20 categories of cyber security incidents within 6 hours; 180-day log preservation within Indian jurisdiction.",
                affected_clauses=["Paragraph 2(i)", "Paragraph 2(ii)", "Annexure I"],
            ),
            "REV-DPDP-2023": DocumentRevision(
                revision_id="REV-DPDP-2023",
                document_id="MEITY-DPDP-2023",
                document_title="Digital Personal Data Protection Act, 2023",
                previous_version_date="2000-06-09 (IT Act Section 43A)",
                new_version_date="2023-08-11",
                revision_type=RevisionType.REPEAL_AND_REPLACE,
                summary="Enacts comprehensive personal data protection framework; repeals Section 43A of IT Act 2000.",
                affected_clauses=["Section 4", "Section 5", "Section 8", "Section 9", "Section 33"],
            ),
        }

    def get_tracked_revisions(self) -> List[Dict[str, Any]]:
        return [
            {
                "revision_id": r.revision_id,
                "document_id": r.document_id,
                "document_title": r.document_title,
                "previous_version_date": r.previous_version_date,
                "new_version_date": r.new_version_date,
                "revision_type": r.revision_type.value,
                "summary": r.summary,
                "affected_clauses": r.affected_clauses,
            }
            for r in self.tracked_revisions.values()
        ]

    def build_impact_plan(self, revision_id: str) -> ImpactAssessmentPlan:
        """
        Plan dependency tracking and selective re-evaluation for a document revision.
        Maintains strict auditability without claiming completed execution.
        """
        rev = self.tracked_revisions.get(revision_id)
        if not rev:
            raise ValueError(f"Revision {revision_id} not found in tracked registry.")

        # Map affected chunks and scenarios based on revision
        if revision_id == "REV-CERTIN-70B-2022":
            chunks = ["kb-certin-p1-chunk1", "kb-certin-p2-chunk1", "kb-certin-p3-chunk1"]
            scenarios = ["HG-CERTIN-008", "HG-INDIA-5G-001"]
            triggers = [
                "Re-evaluate Step C1 (Incident Reporting Window): confirm 6-hour mandate",
                "Re-evaluate Step C2 (Log Retention Jurisdiction): confirm 180-day log mandate",
            ]
        elif revision_id == "REV-TELECOM-2023":
            chunks = ["kb-telecom-act-s22", "kb-crit-infra-r4"]
            scenarios = ["HG-INDIA-5G-001", "HG-DEMO-002"]
            triggers = [
                "Re-evaluate Critical Telecommunication Infrastructure authorization requirements",
                "Re-evaluate Trusted Sources procurement compliance under National Security Directive",
            ]
        else:
            chunks = ["kb-dpdp-s8", "kb-dpdp-s9"]
            scenarios = ["HG-DEMO-001"]
            triggers = [
                "Re-evaluate Data Fiduciary data breach notification requirements",
                "Re-evaluate cross-border data transfer permissions",
            ]

        return ImpactAssessmentPlan(
            plan_id=f"PLAN-{revision_id}",
            revision_id=revision_id,
            status="READY_FOR_EVALUATION",
            affected_evidence_chunks=chunks,
            affected_scenarios=scenarios,
            re_evaluation_triggers=triggers,
            implementation_status="PLANNED_PHASE_2",
            testing_verified=False,
        )


_change_impact_engine: Optional[ChangeImpactEngine] = None

def get_change_impact_engine() -> ChangeImpactEngine:
    global _change_impact_engine
    if _change_impact_engine is None:
        _change_impact_engine = ChangeImpactEngine()
    return _change_impact_engine
