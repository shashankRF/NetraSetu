from __future__ import annotations

from typing import List

from .models import (
    ClaimAssessment,
    EvidenceAssessment,
    EvidenceStatus,
    EvidenceStrength,
)


class EvidenceEngine:

    def assess(
        self,
        claims: List[ClaimAssessment],
    ) -> EvidenceAssessment:

        supporting_count = 0
        contradicting_count = 0
        primary_source_count = 0
        official_source_count = 0

        source_types = set()
        evidence_confidences = []
        claim_confidences = []
        missing_evidence = []

        overall_status = EvidenceStatus.SUFFICIENT
        overall_strength = EvidenceStrength.STRONG

        for claim in claims:

            claim_confidences.append(claim.confidence)

            supporting_count += len(claim.supporting)
            contradicting_count += len(claim.contradicting)

            for evidence in (
                claim.supporting
                + claim.contradicting
                + claim.limiting
                + claim.contextual
            ):

                metadata = evidence.metadata

                if metadata.source_type:
                    source_types.add(metadata.source_type)

                if metadata.publisher:
                    official_source_count += 1

                if metadata.source_type in {
                    "PRIMARY",
                    "NATIONAL_REGULATION",
                    "LAW",
                    "REGULATION",
                }:
                    primary_source_count += 1

                evidence_confidences.append(
                    evidence.confidence
                )

            # ------------------------------------------------
            # Claim-status aggregation
            # ------------------------------------------------

            if claim.status == EvidenceStatus.CONFLICTING:

                overall_status = EvidenceStatus.CONFLICTING

                if (
                    "Conflicting evidence requires resolution."
                    not in missing_evidence
                ):
                    missing_evidence.append(
                        "Conflicting evidence requires resolution."
                    )

            elif (
                claim.status == EvidenceStatus.INSUFFICIENT
                and overall_status != EvidenceStatus.CONFLICTING
            ):

                overall_status = EvidenceStatus.INSUFFICIENT

            elif (
                claim.status == EvidenceStatus.ABSENCE_NOT_ESTABLISHED
                and overall_status
                not in {
                    EvidenceStatus.CONFLICTING,
                    EvidenceStatus.INSUFFICIENT,
                }
            ):

                overall_status = (
                    EvidenceStatus.ABSENCE_NOT_ESTABLISHED
                )

            elif (
                claim.status == EvidenceStatus.AMBIGUOUS
                and overall_status
                not in {
                    EvidenceStatus.CONFLICTING,
                    EvidenceStatus.INSUFFICIENT,
                    EvidenceStatus.ABSENCE_NOT_ESTABLISHED,
                }
            ):

                overall_status = EvidenceStatus.AMBIGUOUS

            # ------------------------------------------------
            # Missing evidence tracking
            # ------------------------------------------------

            if claim.status in {
                EvidenceStatus.INSUFFICIENT,
                EvidenceStatus.ABSENCE_NOT_ESTABLISHED,
            }:

                missing_evidence.append(
                    claim.claim_id
                )

            # ------------------------------------------------
            # Confidence → strength
            # ------------------------------------------------

            if (
                claim.confidence < 0.5
                and overall_strength == EvidenceStrength.STRONG
            ):

                overall_strength = EvidenceStrength.MODERATE

        # ----------------------------------------------------
        # Overall strength
        # ----------------------------------------------------

        if not claims:

            overall_status = EvidenceStatus.INSUFFICIENT
            overall_strength = EvidenceStrength.INSUFFICIENT

        elif contradicting_count > 0:

            overall_strength = EvidenceStrength.MODERATE

        elif supporting_count == 0:

            overall_strength = EvidenceStrength.INSUFFICIENT

        elif overall_status in {
            EvidenceStatus.INSUFFICIENT,
            EvidenceStatus.ABSENCE_NOT_ESTABLISHED,
        }:

            overall_strength = EvidenceStrength.INSUFFICIENT

        # ----------------------------------------------------
        # Overall confidence
        #
        # Evidence-backed assessments are capped at 0.90.
        # When there is no evidence, preserve the claim-level
        # confidence instead of manufacturing confidence.
        # ----------------------------------------------------

        if evidence_confidences:

            overall_confidence = min(
                sum(evidence_confidences)
                / len(evidence_confidences),
                0.90,
            )

        elif claim_confidences:

            overall_confidence = min(
                sum(claim_confidences)
                / len(claim_confidences),
                0.90,
            )

        else:

            overall_confidence = 0.0

        # ----------------------------------------------------
        # Final deterministic safety normalization
        # ----------------------------------------------------

        if overall_status == EvidenceStatus.ABSENCE_NOT_ESTABLISHED:

            overall_strength = EvidenceStrength.INSUFFICIENT

        if overall_status == EvidenceStatus.CONFLICTING:

            overall_strength = EvidenceStrength.MODERATE

        # ----------------------------------------------------
        # Return
        # ----------------------------------------------------

        return EvidenceAssessment(
            claims=claims,
            absence_verifications=[],
            overall_status=overall_status,
            overall_strength=overall_strength,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            primary_source_count=primary_source_count,
            official_source_count=official_source_count,
            source_diversity=len(source_types),
            missing_evidence=missing_evidence,
            overall_confidence=overall_confidence,
        )