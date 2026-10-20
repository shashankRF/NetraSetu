import urllib.request
import json
import sys

URL = "http://127.0.0.1:8000/api/query"

test_question = """A Tier-1 Indian telecom operator detects abnormal behaviour in a production 5G network slice supporting emergency communications.

At 02:17 UTC, the slice begins communicating with an unfamiliar external management endpoint. Network telemetry shows intermittent isolation violations between the affected slice and a management-plane service.

At the same time:
- A recently updated network-function container has a valid vendor signature.
- Its SBOM contains no known CVE matching the observed behaviour.
- The vendor claims the release is compliant with applicable 3GPP security requirements.
- An internal security analyst discovers that one retrieved security guidance document contains a modified requirement that appears to weaken isolation controls.
- A second authoritative document appears to impose a stricter requirement.
- Logs indicate privileged credentials associated with the network-function deployment were used shortly before the anomaly.

The operator cannot yet determine whether this is:
1. compromised network function,
2. credential compromise,
3. malicious configuration,
4. supply-chain compromise,
5. false positive/interoperability problem.

Assess the incident from technical, regulatory, evidentiary and governance perspectives for an Indian telecom operator.

Determine what is established, what remains unproven, whether the incident should be treated as a potentially serious security event, what evidence is required before attribution, what regulatory obligations may be relevant, and whether automated operational action is appropriate."""

payload = {
    "question": test_question,
    "jurisdiction": "India",
    "demo_mode": True
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})

def _run_live_test():
    print("[TEST] Sending test query to /api/query...")
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print("\n[SUCCESS] Response received from pipeline!")
    
            synth = result.get("final_synthesis", {})
            print("\n================ FINAL SYNTHESIS ASSESSMENT ================")
            print(synth.get("assessment", ""))
    
            print("\n================ REGULATORY IMPLICATIONS ================")
            for idx, ri in enumerate(synth.get("regulatory_implications", []), 1):
                print(f"[{idx}] {json.dumps(ri, indent=2, ensure_ascii=False)}")
    
            print("\n================ COUNTER-EVIDENCE ================")
            for idx, ce in enumerate(synth.get("counter_evidence", []), 1):
                print(f"[{idx}] {json.dumps(ce, indent=2, ensure_ascii=False)}")
    
            # Verification Assertions
            reg_str = json.dumps(synth.get("regulatory_implications", []))
            assessment_str = synth.get("assessment", "")
    
            # 1. No unconditional overclaims
            overclaim_words = [
                "Mandatory regulatory and reporting obligations apply",
                "Mandatory reporting applies",
                "The operator must report this incident"
            ]
            for ow in overclaim_words:
                assert ow.lower() not in reg_str.lower(), f"Overclaim found in regulatory implications: {ow}"
                assert ow.lower() not in assessment_str.lower(), f"Overclaim found in assessment: {ow}"
            print("\n[PASS] No mandatory overclaims detected!")
    
            # 2. Counter-evidence is present and reaches final synthesis
            counter_ev = synth.get("counter_evidence", [])
            assert len(counter_ev) > 0, "Counter-evidence is empty!"
            for ce in counter_ev:
                assert "affected_conclusion" in ce and ce["affected_conclusion"], f"Missing affected_conclusion in {ce}"
                assert "confidence_impact" in ce and ce["confidence_impact"], f"Missing confidence_impact in {ce}"
                assert "evidence_ids" in ce, f"Missing evidence_ids in {ce}"
            print(f"[PASS] Counter-evidence populated with {len(counter_ev)} item(s) including affected_conclusion and confidence_impact!")
    
            # 3. Governance preserved
            risk = result.get("risk_assessment", {})
            print(f"[GOVERNANCE] Risk level: {risk.get('risk_level')}, Human review: {synth.get('human_review_required')}")
            assert synth.get("human_review_required") is True, "Human review requirement must be preserved!"
            print("[PASS] Governance invariants preserved!")
    
    except Exception as e:
        print(f"\n[ERROR] Pipeline query failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    
    # ============================================================
    # UNIT TESTS FOR DETERMINISTIC GUARDRAILS
    # ============================================================

if __name__ == '__main__':
    _run_live_test()

print("\n[TEST] Running comprehensive unit tests on _apply_regulatory_and_counter_guardrails...")
import sys
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from Backend.final_synthesis import _apply_regulatory_and_counter_guardrails

# Test Case 1: All mandatory phrases are detected and downgraded
test_phrases = [
    "mandatory reporting applies under IT Act",
    "mandatory notification is required",
    "reporting obligation applies to this incident",
    "the operator must report immediately",
    "the telecom entity is legally required to report",
    "mandatory regulatory obligation applies to the operator",
]

mock_evidence = [
    {"evidence_id": "EV-001", "text": "Valid vendor signature verified. SBOM contains no known CVE matching observed behavior."},
    {"evidence_id": "EV-002", "text": "ETSI TS 133 501 recommends slice isolation policies."},
]

for phrase in test_phrases:
    mock_input = {
        "assessment": f"Initial analysis: {phrase}.",
        "claims": [
            {"claim_id": "CLM-1", "claim": phrase, "status": "SUPPORTED", "evidence_ids": ["EV-001"], "confidence": 0.95}
        ],
        "regulatory_implications": [
            {
                "statement": phrase,
                "authority_evidence_ids": ["EV-002"],
                "mandatory_status": "ESTABLISHED",
                "applicability": "ESTABLISHED",
                "trigger": "ESTABLISHED",
                "conclusion": f"Conclusion: {phrase}"
            }
        ],
        "counter_evidence": []
    }
    guarded = _apply_regulatory_and_counter_guardrails(mock_input, mock_evidence)

    # Assert no mandatory overclaims remain
    reg_items = guarded["regulatory_implications"]
    for ri in reg_items:
        assert ri["mandatory_status"] == "UNCERTAIN", f"Failed for phrase '{phrase}': mandatory_status must be UNCERTAIN"
        assert ri["trigger"] == "NOT_ESTABLISHED", f"Failed for phrase '{phrase}': trigger must be NOT_ESTABLISHED"
        assert phrase.lower() not in ri["statement"].lower(), f"Unconditional phrase remained in statement: {phrase}"

    # Assert claim was downgraded
    cl = guarded["claims"][0]
    assert cl["status"] == "PARTIALLY_SUPPORTED", f"Claim status was not downgraded for {phrase}"
    assert cl["confidence"] <= 0.70, f"Claim confidence was not capped for {phrase}"

print("[PASS] All mandatory phrases successfully downgraded!")

# Test Case 2: Counter-evidence reflects affected_conclusion and confidence_impact
mock_input_with_counter = {
    "assessment": "Anomaly detected in slice.",
    "claims": [],
    "regulatory_implications": [],
    "counter_evidence": [
        {
            "claim_id": "CLM-001",
            "claim": "Vendor release supply chain compromise",
            "evidence_ids": ["EV-001"],
            "effect": "LIMITING",
            "explanation": "Valid signature and no known CVE limit immediate attribution.",
            "affected_conclusion": "Attribution to vendor release compromise",
            "confidence_impact": "Reduces attribution confidence from confirmed breach to unproven hypothesis"
        }
    ]
}
guarded2 = _apply_regulatory_and_counter_guardrails(mock_input_with_counter, mock_evidence)
ce = guarded2["counter_evidence"][0]
assert ce["affected_conclusion"] == "Attribution to vendor release compromise"
assert ce["confidence_impact"] == "Reduces attribution confidence from confirmed breach to unproven hypothesis"
assert ce["evidence_ids"] == ["EV-001"]
print("[PASS] Counter-evidence explicitly reflects affected_conclusion, confidence_impact, and evidence_ids!")

# Test Case 3: Empty counter-evidence set reflects standard non-global message
mock_input_no_counter = {
    "assessment": "Routine operations observed.",
    "claims": [],
    "regulatory_implications": [],
    "counter_evidence": []
}
guarded3 = _apply_regulatory_and_counter_guardrails(mock_input_no_counter, [])
ce3 = guarded3["counter_evidence"][0]
assert ce3["explanation"] == "No meaningful counter-evidence was identified in the supplied evidence set."
assert "globally" not in ce3["explanation"].lower()
assert "no counter-evidence exists globally" not in json.dumps(guarded3).lower()
print("[PASS] Default counter-evidence reflects supplied-set scope and avoids global claims!")

print("\n[ALL TESTS PASSED SUCCESSFULLY!]")
