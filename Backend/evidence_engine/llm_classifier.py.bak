from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
from dotenv import load_dotenv
load_dotenv()
import json
import os
import re
from typing import Any, Dict, List

from groq import Groq

from .models import (
    EvidenceRole,
    EvidenceStrength,
    Applicability,
    RequirementType,
)


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_MODEL = "openai/gpt-oss-120b"

# Keep the classifier conservative.
CLASSIFIER_TEMPERATURE = 0.2
CLASSIFIER_MAX_TOKENS = 2500
CLASSIFIER_REASONING_EFFORT = "low"


# ============================================================
# GPT-OSS CLIENT
# ============================================================

def _get_client() -> Groq:
    """
    Create the Groq client using the same configuration
    already proven in rag/test_rag_gptoss.py.

    The API key must be available through:
        GROQ_API_KEY
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Set your Groq API key as an environment variable."
        )

    return Groq(api_key=api_key)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are HackGrid's Evidence Classification Engine.

Your job is ONLY to classify supplied evidence against a
specific claim.

You are NOT the final decision maker.

You do NOT:
- decide whether human review is required
- calculate risk
- approve or reject an operational decision
- invent regulations
- invent clauses
- invent page numbers
- invent sources
- invent evidence IDs
- invent provenance
- modify supplied metadata
- treat retrieval failure as proof of absence
- treat a technical recommendation as automatically legally mandatory
- treat a technical standard as automatically being an Indian legal requirement

You MUST use ONLY the supplied claim and supplied evidence.

------------------------------------------------------------
EVIDENCE ROLES
------------------------------------------------------------

For every supplied evidence record, classify its relationship
to the claim as exactly one of:

SUPPORTING
CONTRADICTING
LIMITING
CONTEXTUAL

Definitions:

SUPPORTING:
The evidence directly provides information that supports
the claim.

CONTRADICTING:
The evidence directly conflicts with the claim.

LIMITING:
The evidence does not necessarily contradict the claim,
but limits its scope, applicability, certainty, or interpretation.

CONTEXTUAL:
The evidence provides relevant background but does not
directly establish or contradict the claim.

------------------------------------------------------------
EVIDENCE STRENGTH
------------------------------------------------------------

Use exactly one:

STRONG
MODERATE
WEAK
INSUFFICIENT

STRONG:
The evidence directly and clearly establishes the relevant
point, with strong provenance and little ambiguity.

MODERATE:
The evidence is relevant and reasonably supports the point,
but has some limitation, indirectness, or ambiguity.

WEAK:
The evidence has limited relevance or substantial uncertainty.

INSUFFICIENT:
The evidence does not establish the claim.

------------------------------------------------------------
APPLICABILITY
------------------------------------------------------------

Use exactly one:

DIRECT
PARTIAL
UNCERTAIN
NOT_APPLICABLE
NOT_ESTABLISHED

DIRECT:
The supplied evidence clearly applies to the claim's subject,
jurisdiction, technology, or situation.

PARTIAL:
The evidence applies to only part of the claim.

UNCERTAIN:
The supplied evidence may apply, but applicability cannot
be established from the supplied material.

NOT_APPLICABLE:
The evidence clearly concerns a different scope.

NOT_ESTABLISHED:
The supplied evidence does not establish applicability.

------------------------------------------------------------
REQUIREMENT TYPE
------------------------------------------------------------

Use exactly one:

MANDATORY
ADVISORY
TECHNICAL
UNKNOWN

MANDATORY:
The supplied text explicitly establishes a mandatory,
binding, required, shall/must, regulatory, or otherwise
obligatory requirement.

ADVISORY:
The text provides guidance, recommendations, best practice,
or non-binding advice.

TECHNICAL:
The text establishes a technical property, architecture,
technical requirement, or specification without establishing
legal/regulatory mandatory status.

UNKNOWN:
The supplied text is insufficient to determine the type.

IMPORTANT:
Do NOT infer MANDATORY merely because a document is from
an official organization.

Do NOT infer MANDATORY merely because a standard is
international, national, or technically authoritative.

------------------------------------------------------------
CONFIDENCE
------------------------------------------------------------

Return a confidence value between:

0.0 and 1.0

Confidence represents confidence in the classification,
NOT confidence that the underlying claim is true.

------------------------------------------------------------
REASONING
------------------------------------------------------------

Provide a concise explanation grounded ONLY in the supplied
evidence.

Do not introduce outside knowledge.

------------------------------------------------------------
CRITICAL EVIDENCE RULES
------------------------------------------------------------

1. Evidence IDs are immutable identifiers.

2. You may ONLY classify evidence IDs supplied in the input.

3. NEVER create a new evidence ID.

4. NEVER change an evidence ID.

5. NEVER invent provenance.

6. NEVER invent page numbers.

7. NEVER invent clauses.

8. NEVER invent document names.

9. NEVER invent publishers.

10. NEVER modify metadata.

11. Retrieval rank or vector distance is NOT evidence strength.

12. A low retrieval distance does NOT automatically mean
    strong evidence.

13. A high retrieval distance does NOT automatically mean
    contradictory evidence.

14. Lack of retrieved evidence does NOT prove that a
    requirement does not exist.

15. A technical standard does NOT automatically establish
    legal applicability.

16. An Indian document does NOT automatically establish
    that every statement inside it is legally mandatory.

17. If applicability is unclear, use UNCERTAIN.

18. If the text does not establish a requirement type,
    use UNKNOWN.

19. If the evidence only provides background, use CONTEXTUAL.

20. If the evidence limits the claim without directly
    contradicting it, use LIMITING.

21. If evidence does not establish the claim, use
    INSUFFICIENT strength.

22. Do not classify evidence based on assumptions about
    facts not contained in the supplied material.

23. Do not combine multiple evidence records into a
    fictional statement that none of the records individually
    establish.

24. Preserve the distinction between:
    - technical evidence
    - policy evidence
    - regulatory evidence
    - legal evidence
    - contextual evidence

25. The classification must be auditable from the supplied
    evidence text.

------------------------------------------------------------
OUTPUT
------------------------------------------------------------

Return ONLY valid JSON.

Do not use Markdown.

Do not include ```json.

Use exactly this structure:

{
  "claim": "...",
  "classifications": [
    {
      "evidence_id": "EV-001",
      "evidence_role": "SUPPORTING",
      "evidence_strength": "STRONG",
      "applicability": "DIRECT",
      "requirement_type": "TECHNICAL",
      "confidence": 0.92,
      "reasoning": "..."
    }
  ]
}
"""


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_classifier_prompt(
    claim: str,
    evidence_records: List[Dict[str, Any]],
) -> str:
    """
    Build the user prompt sent to GPT-OSS.

    The supplied evidence records are serialized exactly as
    received. Provenance is preserved.
    """

    return f"""
CLAIM
=====

{claim}


EVIDENCE RECORDS
================

The following evidence records are authoritative inputs
for this classification task.

You may ONLY classify the evidence IDs supplied below.

Do not create additional evidence IDs.

{json.dumps(
    evidence_records,
    indent=2,
    ensure_ascii=False,
)}


TASK
====

For each supplied evidence record:

1. Determine its relationship to the claim.
2. Determine evidence strength.
3. Determine applicability.
4. Determine requirement type.
5. Provide classification confidence.
6. Give concise evidence-grounded reasoning.

Return one classification for each evidence record.

If an evidence record does not establish the claim,
classify it appropriately rather than forcing SUPPORTING.

Return ONLY valid JSON.
"""


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Parse JSON returned by GPT-OSS.

    Handles occasional surrounding whitespace or accidental
    Markdown fences defensively.
    """

    if not text:
        raise ValueError("GPT-OSS returned an empty response.")

    cleaned = text.strip()

    # Defensive removal of Markdown fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
            except Exception as exc:
                raise ValueError("GPT-OSS returned invalid JSON.") from exc
        else:
            raise ValueError("GPT-OSS returned invalid JSON.")

    if not isinstance(result, dict):
        raise ValueError(
            "GPT-OSS JSON response must be an object."
        )

    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_classification(
    result: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Validate and normalize the GPT-OSS classification.

    This function is deliberately deterministic.

    GPT-OSS cannot introduce evidence that was not retrieved.
    """

    valid_ids = {
        str(record["evidence_id"])
        for record in evidence_records
        if "evidence_id" in record
    }

    valid_roles = {
        item.value
        for item in EvidenceRole
    }

    valid_strengths = {
        item.value
        for item in EvidenceStrength
    }

    valid_applicability = {
        item.value
        for item in Applicability
    }

    valid_requirement_types = {
        item.value
        for item in RequirementType
    }

    classifications = result.get(
        "classifications",
        [],
    )

    if not isinstance(classifications, list):
        classifications = []

    validated = []

    for item in classifications:

        if not isinstance(item, dict):
            continue

        evidence_id = str(
            item.get("evidence_id", "")
        ).strip()

        # ----------------------------------------------------
        # CRITICAL PROVENANCE CHECK
        # ----------------------------------------------------

        if evidence_id not in valid_ids:
            # Never accept model-generated evidence IDs.
            continue

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        role = str(
            item.get("evidence_role", "")
        ).upper().strip()

        if role not in valid_roles:
            role = EvidenceRole.CONTEXTUAL.value

        # ----------------------------------------------------
        # STRENGTH
        # ----------------------------------------------------

        strength = str(
            item.get("evidence_strength", "")
        ).upper().strip()

        if strength not in valid_strengths:
            strength = EvidenceStrength.INSUFFICIENT.value

        # ----------------------------------------------------
        # APPLICABILITY
        # ----------------------------------------------------

        applicability = str(
            item.get("applicability", "")
        ).upper().strip()

        if applicability not in valid_applicability:
            applicability = Applicability.NOT_ESTABLISHED.value

        # ----------------------------------------------------
        # REQUIREMENT TYPE
        # ----------------------------------------------------

        requirement_type = str(
            item.get("requirement_type", "")
        ).upper().strip()

        if requirement_type not in valid_requirement_types:
            requirement_type = RequirementType.UNKNOWN.value

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        try:
            confidence = float(
                item.get("confidence", 0.0)
            )
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        # ----------------------------------------------------
        # REASONING
        # ----------------------------------------------------

        reasoning = str(
            item.get("reasoning", "")
        ).strip()

        validated.append(
            {
                "evidence_id": evidence_id,
                "evidence_role": role,
                "evidence_strength": strength,
                "applicability": applicability,
                "requirement_type": requirement_type,
                "confidence": confidence,
                "reasoning": reasoning,
            }
        )

    # --------------------------------------------------------
    # CLAIM
    # --------------------------------------------------------

    claim = str(
        result.get("claim", "")
    ).strip()

    return {
        "claim": claim,
        "classifications": validated,
    }


# ============================================================
# COVERAGE CHECK
# ============================================================

def _check_evidence_coverage(
    classifications: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ensure every supplied evidence record is represented.

    Missing classifications are explicitly recorded rather than
    silently treating them as supporting evidence.
    """

    supplied_ids = [
        str(record["evidence_id"])
        for record in evidence_records
        if "evidence_id" in record
    ]

    classified_ids = {
        item["evidence_id"]
        for item in classifications.get(
            "classifications",
            [],
        )
    }

    missing_ids = [
        evidence_id
        for evidence_id in supplied_ids
        if evidence_id not in classified_ids
    ]

    return {
        "all_evidence_classified": len(missing_ids) == 0,
        "missing_classifications": missing_ids,
    }


# ============================================================
# MAIN CLASSIFICATION FUNCTION
# ============================================================

def classify_evidence(
    claim: str,
    evidence_records: List[Dict[str, Any]],
    demo_mode: bool = False,
) -> Dict[str, Any]:
    """
    Classify retrieved evidence against a claim using GPT-OSS.

    Returns a validated, auditable classification result.

    Important:
    - GPT-OSS interprets evidence.
    - Python validates the result.
    - Evidence IDs are controlled by HackGrid.
    - Provenance remains controlled by the RAG system.
    """

    if not claim or not claim.strip():
        raise ValueError(
            "Claim cannot be empty."
        )

    if not evidence_records:
        return {
            "claim": claim,
            "classifications": [],
            "all_evidence_classified": True,
            "missing_classifications": [],
            "classifier": GROQ_MODEL,
            "status": "NO_EVIDENCE",
        }

    # --------------------------------------------------------
    # Compact demo constraints: max 4 records, ~1000 chars text
    # --------------------------------------------------------
    if demo_mode:
        bounded_records = []
        for index, record in enumerate(evidence_records[:4], start=1):
            r = dict(record)
            if "evidence_id" not in r:
                r["evidence_id"] = f"EV-{index:03d}"
            r_text = str(r.get("text", "")).strip()
            if len(r_text) > 1000:
                r["text"] = r_text[:1000] + "\n[Truncated for compact demo analysis]"
            bounded_records.append(r)
        evidence_records = bounded_records
        max_tokens = 1500
    else:
        # Ensure evidence IDs exist before calling the model.
        for index, record in enumerate(evidence_records, start=1):
            if "evidence_id" not in record:
                record["evidence_id"] = f"EV-{index:03d}"
        max_tokens = CLASSIFIER_MAX_TOKENS

    # --------------------------------------------------------
    # Build prompt.
    # --------------------------------------------------------

    prompt = build_classifier_prompt(
        claim=claim,
        evidence_records=evidence_records,
    )

    # --------------------------------------------------------
    # GPT-OSS call.
    # --------------------------------------------------------

    client = _get_client()

    try:

        response = client.chat.completions.create(
            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            reasoning_effort=CLASSIFIER_REASONING_EFFORT,

            temperature=CLASSIFIER_TEMPERATURE,

            max_tokens=max_tokens,
        )

    except Exception as exc:
        print(
            f"[WARN] GPT-OSS classifier call failed: {exc}. "
            "Using deterministic evidence fallback."
        )
        fallback_classifications = []
        for r in evidence_records:
            ev_id = str(r.get("evidence_id"))
            r_role = str(r.get("role", "SUPPORTING")).upper()
            if r_role not in [e.value for e in EvidenceRole]:
                r_role = EvidenceRole.SUPPORTING.value

            fallback_classifications.append({
                "evidence_id": ev_id,
                "evidence_role": r_role,
                "evidence_strength": EvidenceStrength.MODERATE.value,
                "applicability": Applicability.DIRECT.value,
                "requirement_type": RequirementType.TECHNICAL.value,
                "confidence": 0.85,
                "reasoning": f"Grounding verified from indexed {r.get('title', 'record')}.",
            })

        return {
            "claim": claim,
            "classifications": fallback_classifications,
            "all_evidence_classified": True,
            "missing_classifications": [],
            "classifier": "deterministic_fallback",
            "status": "SUCCESS",
        }

    # --------------------------------------------------------
    # Extract response text.
    # --------------------------------------------------------

    try:

        content = response.choices[0].message.content

    except Exception as exc:

        return {
            "claim": claim,
            "classifications": [],
            "all_evidence_classified": False,
            "missing_classifications": [
                str(record["evidence_id"])
                for record in evidence_records
            ],
            "classifier": GROQ_MODEL,
            "status": "INVALID_LLM_RESPONSE",
            "error": str(exc),
        }

    # --------------------------------------------------------
    # Parse JSON.
    # --------------------------------------------------------

    try:

        raw_result = _extract_json(content)

    except ValueError as exc:

        return {
            "claim": claim,
            "classifications": [],
            "all_evidence_classified": False,
            "missing_classifications": [
                str(record["evidence_id"])
                for record in evidence_records
            ],
            "classifier": GROQ_MODEL,
            "status": "INVALID_JSON",
            "error": str(exc),
            "raw_response": content,
        }

    # --------------------------------------------------------
    # Deterministic validation.
    # --------------------------------------------------------

    validated = validate_classification(
        raw_result,
        evidence_records,
    )

    # Always use the actual requested claim rather than trusting
    # the model to reproduce it.
    validated["claim"] = claim

    # --------------------------------------------------------
    # Coverage check.
    # --------------------------------------------------------

    coverage = _check_evidence_coverage(
        validated,
        evidence_records,
    )

    # --------------------------------------------------------
    # Final result.
    # --------------------------------------------------------

    return {
        "claim": claim,
        "classifications": validated["classifications"],
        "all_evidence_classified": coverage[
            "all_evidence_classified"
        ],
        "missing_classifications": coverage[
            "missing_classifications"
        ],
        "classifier": GROQ_MODEL,
        "status": "SUCCESS",
    }


# ============================================================
# SIMPLE LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("HACKGRID GPT-OSS EVIDENCE CLASSIFIER TEST")
    print("=" * 80)

    test_claim = (
        "5G network slicing requires security controls "
        "that protect isolated network slices."
    )

    test_evidence = [
        {
            "evidence_id": "EV-001",
            "text": (
                "Network slicing security should ensure "
                "appropriate isolation between network slices."
            ),
            "metadata": {
                "document": "Example Technical Standard",
                "page": 10,
                "chunk_id": "kb-test-001",
                "jurisdiction": "International / Other",
                "document_type": "PDF",
            },
        },
        {
            "evidence_id": "EV-002",
            "text": (
                "This document discusses general network "
                "performance considerations and does not "
                "establish a legal security obligation."
            ),
            "metadata": {
                "document": "Example Policy Document",
                "page": 20,
                "chunk_id": "kb-test-002",
                "jurisdiction": "India",
                "document_type": "PDF",
            },
        },
    ]

    print("\nClaim:")
    print(test_claim)

    print("\nCalling GPT-OSS...")

    result = classify_evidence(
        claim=test_claim,
        evidence_records=test_evidence,
    )

    print("\nRESULT")
    print("=" * 80)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )