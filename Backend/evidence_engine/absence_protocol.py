from __future__ import annotations

from typing import Any, Dict, List

from .models import AbsenceVerification, EvidenceStatus


# ============================================================
# ABSENCE VERIFICATION PROTOCOL
# ============================================================

def verify_absence(
    claim: str,
    sources_examined: List[str],
    authoritative_sources_examined: List[str],
    positive_evidence: List[str],
    negative_evidence: List[str],
    search_scope: str,
    limitations: List[str],
) -> AbsenceVerification:
    """
    Conservative absence verification.

    IMPORTANT:
    Retrieval failure is NEVER treated as proof that a
    requirement, regulation, standard, or policy does not exist.

    The protocol can establish that absence has NOT been
    established, but cannot declare non-existence merely because
    evidence was not retrieved.
    """

    sources_examined = sources_examined or []
    authoritative_sources_examined = (
        authoritative_sources_examined or []
    )
    positive_evidence = positive_evidence or []
    negative_evidence = negative_evidence or []
    limitations = limitations or []

    # --------------------------------------------------------
    # Positive evidence exists
    # --------------------------------------------------------

    if positive_evidence:

        return AbsenceVerification(
            claim=claim,
            verification_status=(
                EvidenceStatus.ABSENCE_NOT_ESTABLISHED
            ),
            sources_examined=sources_examined,
            authoritative_sources_examined=(
                authoritative_sources_examined
            ),
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            search_scope=search_scope,
            limitations=(
                limitations
                + [
                    "Positive evidence was identified; "
                    "absence cannot be established."
                ]
            ),
        )

    # --------------------------------------------------------
    # No positive evidence but authoritative sources examined
    # --------------------------------------------------------

    if authoritative_sources_examined:

        return AbsenceVerification(
            claim=claim,
            verification_status=(
                EvidenceStatus.ABSENCE_NOT_ESTABLISHED
            ),
            sources_examined=sources_examined,
            authoritative_sources_examined=(
                authoritative_sources_examined
            ),
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            search_scope=search_scope,
            limitations=(
                limitations
                + [
                    "No positive evidence was identified "
                    "within the examined sources.",
                    "The examined-source result does not "
                    "establish that the requirement or "
                    "provision does not exist elsewhere."
                ]
            ),
        )

    # --------------------------------------------------------
    # No authoritative sources examined
    # --------------------------------------------------------

    return AbsenceVerification(
        claim=claim,
        verification_status=(
            EvidenceStatus.ABSENCE_NOT_ESTABLISHED
        ),
        sources_examined=sources_examined,
        authoritative_sources_examined=(
            authoritative_sources_examined
        ),
        positive_evidence=positive_evidence,
        negative_evidence=negative_evidence,
        search_scope=search_scope,
        limitations=(
            limitations
            + [
                "No authoritative source set was examined.",
                "Retrieval failure cannot establish absence.",
                "Additional authoritative-source verification "
                "is required before making an absence claim."
            ]
        ),
    )


# ============================================================
# BUILD ABSENCE VERIFICATION FROM RAG RESULTS
# ============================================================

def build_absence_verification(
    claim: str,
    evidence_records: List[Dict[str, Any]],
    search_scope: str,
    authoritative_jurisdictions: List[str] | None = None,
) -> AbsenceVerification:
    """
    Build a conservative absence-verification record from
    retrieved RAG evidence.

    This function does NOT claim that a requirement is absent.

    It records:
        - sources examined
        - authoritative sources examined
        - retrieved positive evidence
        - search scope
        - limitations

    The classifier determines whether evidence is relevant;
    this function only preserves the verification boundary.
    """

    authoritative_jurisdictions = (
        authoritative_jurisdictions
        or ["India"]
    )

    sources_examined: List[str] = []
    authoritative_sources_examined: List[str] = []
    positive_evidence: List[str] = []

    for evidence in evidence_records:

        evidence_id = evidence.get(
            "evidence_id",
            "",
        )

        provenance = evidence.get(
            "provenance",
            {},
        )

        document = provenance.get(
            "document"
        )

        source_file = provenance.get(
            "source_file"
        )

        jurisdiction = provenance.get(
            "jurisdiction"
        )

        page = provenance.get(
            "page"
        )

        source_label = (
            f"{document}"
            if document
            else f"{source_file}"
            if source_file
            else evidence_id
        )

        if page is not None:
            source_label += f", page {page}"

        if source_label not in sources_examined:
            sources_examined.append(
                source_label
            )

        if (
            jurisdiction
            and jurisdiction in authoritative_jurisdictions
        ):
            if source_label not in authoritative_sources_examined:
                authoritative_sources_examined.append(
                    source_label
                )

        # Any retrieved evidence means that we have evidence
        # relevant enough to be examined. It is deliberately
        # NOT interpreted as proof of a requirement here.
        if evidence.get("text"):
            positive_evidence.append(
                evidence_id
            )

    limitations = [
        "This verification is based only on the supplied "
        "retrieval results.",
        "The retrieval set is not equivalent to an exhaustive "
        "legal or regulatory database search.",
        "Absence of a retrieved provision does not establish "
        "that no such provision exists.",
    ]

    return verify_absence(
        claim=claim,
        sources_examined=sources_examined,
        authoritative_sources_examined=(
            authoritative_sources_examined
        ),
        positive_evidence=positive_evidence,
        negative_evidence=[],
        search_scope=search_scope,
        limitations=limitations,
    )


# ============================================================
# SERIALIZATION
# ============================================================

def absence_verification_to_dict(
    verification: AbsenceVerification,
) -> Dict[str, Any]:
    """
    Convert the dataclass into an audit-friendly dictionary.
    """

    return {
        "claim": verification.claim,

        "verification_status": (
            verification.verification_status.value
            if hasattr(
                verification.verification_status,
                "value",
            )
            else str(
                verification.verification_status
            )
        ),

        "sources_examined": (
            verification.sources_examined
        ),

        "authoritative_sources_examined": (
            verification.authoritative_sources_examined
        ),

        "positive_evidence": (
            verification.positive_evidence
        ),

        "negative_evidence": (
            verification.negative_evidence
        ),

        "search_scope": (
            verification.search_scope
        ),

        "limitations": (
            verification.limitations
        ),
    }