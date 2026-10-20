from __future__ import annotations

from Backend.orchestrator import run_pipeline


REQUIRED_KEYS = {
    "question",
    "retrieval",
    "classification",
    "validation",
    "evidence_assessment",
    "absence_verification",
    "gap_analysis",
    "risk_assessment",
    "final_synthesis",
    "claim_evidence_mappings",
    "audit_id",
}


def main():

    print("=" * 70)
    print("HACKGRID — PIPELINE CONTRACT TEST")
    print("=" * 70)

    result = run_pipeline(
        "What is network slicing in 5G?"
    )

    missing = REQUIRED_KEYS - set(result.keys())

    assert not missing, (
        f"Missing pipeline keys: {missing}"
    )

    assert result["retrieval"]["count"] > 0

    assert result["audit_id"]

    assert result["final_synthesis"]["status"] == "SUCCESS"

    assert result["risk_assessment"]["risk_level"]

    print("PIPELINE KEYS: PASS")
    print("RETRIEVAL: PASS")
    print("AUDIT: PASS")
    print("FINAL SYNTHESIS: PASS")
    print("RISK ENGINE: PASS")
    print("PIPELINE CONTRACT: PASS")


if __name__ == "__main__":
    main()