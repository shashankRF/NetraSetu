from __future__ import annotations
import re
from typing import Any, Dict, List, Set


def validate_synthesis_claims(
    synthesis_result: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Pre-output validation gate.
    Ensures every substantive claim in the final synthesis is grounded in an actual
    retrieved evidence ID and supported by the retrieved evidence text.
    If a claim lacks an evidence ID or is unsupported, replaces it or marks it as
    'NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE.'
    """
    valid_ev_ids: Set[str] = {
        rec.get("evidence_id") for rec in evidence_records if rec.get("evidence_id")
    }

    # Map EV ID to its text content for grounding checks
    ev_text_map: Dict[str, str] = {}
    for rec in evidence_records:
        ev_id = rec.get("evidence_id")
        if ev_id:
            txt = (rec.get("text") or rec.get("content") or "").lower()
            ev_text_map[ev_id] = txt

    claims = synthesis_result.get("claims", [])
    validated_claims = []

    for c in claims:
        claim_text = c.get("claim", "")
        ev_ids = c.get("evidence_ids", [])

        # Check if EV IDs are present and valid
        valid_ids_present = [eid for eid in ev_ids if eid in valid_ev_ids]

        if not valid_ids_present:
            # Ungrounded claim: reject/replace
            c["claim"] = f"Claim regarding '{claim_text[:60]}...' is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE."
            c["status"] = "INSUFFICIENT"
            c["confidence"] = 0.0
            c["evidence_ids"] = []
        else:
            # Validate that at least one cited EV contains relevant semantic terms
            words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', claim_text.lower()) if w not in {"that", "with", "from", "this", "which", "shall", "must", "have", "been"}]
            grounded = False
            for eid in valid_ids_present:
                ev_content = ev_text_map.get(eid, "")
                matches = sum(1 for w in words if w in ev_content)
                if matches >= 2 or len(words) <= 2:
                    grounded = True
                    break

            if not grounded:
                c["claim"] = f"Claim '{claim_text[:60]}...' is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE."
                c["status"] = "INSUFFICIENT"
                c["confidence"] = 0.0
            else:
                c["evidence_ids"] = valid_ids_present

        validated_claims.append(c)

    synthesis_result["claims"] = validated_claims

    # Validate regulatory implications
    reg_impls = synthesis_result.get("regulatory_implications", [])
    validated_reg_impls = []
    for ri in reg_impls:
        if isinstance(ri, dict):
            status = str(ri.get("mandatory_status") or ri.get("status") or "")
            statement = ri.get("statement") or ri.get("implication") or ""
            # Strict mandatory reporting guardrail:
            if "mandatory reporting" in statement.lower() and status == "ESTABLISHED":
                # Check if evidence establishes mandatory trigger
                ev_ids = ri.get("authority_evidence_ids") or ri.get("evidence_ids") or []
                trigger_established = any(
                    "mandatory reporting" in ev_text_map.get(eid, "") or "report within" in ev_text_map.get(eid, "")
                    for eid in ev_ids
                )
                if not trigger_established:
                    ri["status"] = "NOT_ESTABLISHED"
                    ri["mandatory_status"] = "NOT_ESTABLISHED"
                    ri["statement"] = "Mandatory reporting obligation is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE."
                    if "implication" in ri:
                        ri["implication"] = "Mandatory reporting obligation is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE."
            validated_reg_impls.append(ri)
        else:
            validated_reg_impls.append(ri)

    synthesis_result["regulatory_implications"] = validated_reg_impls
    return synthesis_result
