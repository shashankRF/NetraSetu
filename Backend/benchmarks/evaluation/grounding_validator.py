import json
from pathlib import Path


RESULTS_PATH = Path("Backend/benchmarks/results/benchmark_results.json")
OUTPUT_PATH = Path("Backend/benchmarks/results/grounding_validation.json")


def main():
    with RESULTS_PATH.open("r", encoding="utf-8") as f:
        results = json.load(f)

    total_claims = 0
    grounded_claims = 0
    unsupported_claims = 0
    invalid_evidence_claims = 0

    case_results = []

    for case in results["cases"]:
        # Benchmark schema uses "id", not "case_id"
        case_id = case["id"]
        pipeline = case["pipeline"]

        # Actual evidence records are stored here
        retrieval_evidence = pipeline["retrieval"]["evidence"]

        valid_evidence_ids = {
            item["evidence_id"]
            for item in retrieval_evidence
            if "evidence_id" in item
        }

        mappings = pipeline.get("claim_evidence_mappings", [])

        case_total = 0
        case_grounded = 0
        case_unsupported = 0
        case_invalid = 0

        claim_results = []

        for mapping in mappings:
            case_total += 1
            total_claims += 1

            evidence_ids = mapping.get("evidence_ids", [])
            original_status = mapping.get("status", "")

            invalid_ids = [
                evidence_id
                for evidence_id in evidence_ids
                if evidence_id not in valid_evidence_ids
            ]

            is_grounded = bool(evidence_ids) and not invalid_ids

            if invalid_ids:
                case_invalid += 1
                invalid_evidence_claims += 1
                validation_status = "INVALID_EVIDENCE_REFERENCE"

            elif is_grounded:
                case_grounded += 1
                grounded_claims += 1
                validation_status = "GROUNDED"

            else:
                validation_status = "NO_EVIDENCE_REFERENCE"

            if original_status == "UNSUPPORTED":
                case_unsupported += 1
                unsupported_claims += 1

            claim_results.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "original_status": original_status,
                    "validation_status": validation_status,
                    "evidence_ids": evidence_ids,
                    "invalid_evidence_ids": invalid_ids,
                    "grounded": is_grounded,
                    "confidence": mapping.get("confidence"),
                }
            )

        case_results.append(
            {
                "case_id": case_id,
                "total_claims": case_total,
                "grounded_claims": case_grounded,
                "unsupported_claims": case_unsupported,
                "invalid_evidence_claims": case_invalid,
                "valid_evidence_ids": sorted(valid_evidence_ids),
                "claims": claim_results,
            }
        )

    grounding_rate = (
        grounded_claims / total_claims
        if total_claims
        else 0.0
    )

    unsupported_claim_rate = (
        unsupported_claims / total_claims
        if total_claims
        else 0.0
    )

    invalid_evidence_reference_rate = (
        invalid_evidence_claims / total_claims
        if total_claims
        else 0.0
    )

    output = {
        "total_claims": total_claims,
        "grounded_claims": grounded_claims,
        "unsupported_claims": unsupported_claims,
        "invalid_evidence_claims": invalid_evidence_claims,
        "grounding_rate": round(grounding_rate, 4),
        "unsupported_claim_rate": round(
            unsupported_claim_rate, 4
        ),
        "invalid_evidence_reference_rate": round(
            invalid_evidence_reference_rate, 4
        ),
        "cases": case_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 80)
    print("HACKGRID — GROUNDING VALIDATION")
    print("=" * 80)
    print(f"Total claims: {total_claims}")
    print(f"Grounded claims: {grounded_claims}")
    print(f"Unsupported claims: {unsupported_claims}")
    print(f"Invalid evidence claims: {invalid_evidence_claims}")
    print(f"Grounding rate: {grounding_rate:.2%}")
    print(
        f"Unsupported claim rate: "
        f"{unsupported_claim_rate:.2%}"
    )
    print(
        f"Invalid evidence reference rate: "
        f"{invalid_evidence_reference_rate:.2%}"
    )
    print("=" * 80)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()