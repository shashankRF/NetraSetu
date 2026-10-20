from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


BASE_DIR = Path(__file__).resolve().parents[2]

QUESTIONS_FILE = (
    BASE_DIR
    / "benchmarks"
    / "benchmark_questions.json"
)

TAXONOMY_FILE = (
    BASE_DIR
    / "benchmarks"
    / "evaluation"
    / "benchmark_taxonomy.json"
)


def main():

    with QUESTIONS_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    with TAXONOMY_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        taxonomy = json.load(f)

    questions = data

    if isinstance(data, dict):
        questions = (
            data.get("questions")
            or data.get("cases")
            or []
        )

    print("=" * 70)
    print("HACKGRID — BENCHMARK COVERAGE")
    print("=" * 70)

    print("TOTAL QUESTIONS:", len(questions))

    categories = Counter()

    for q in questions:

        category = q.get(
            "category",
            "UNCLASSIFIED",
        )

        categories[category] += 1

    print()
    print("CATEGORY DISTRIBUTION:")

    for category, count in sorted(
        categories.items()
    ):
        print(
            f"  {category}: {count}"
        )

    taxonomy_ids = {
        x["id"]
        for x in taxonomy["categories"]
    }

    missing_categories = taxonomy_ids - set(
        categories.keys()
    )

    print()

    if missing_categories:
        print(
            "UNCOVERED TAXONOMY CATEGORIES:"
        )

        for x in sorted(missing_categories):
            print(" ", x)

    else:
        print(
            "TAXONOMY COVERAGE: PASS"
        )

    print()
    print(
        "COVERAGE REPORT: COMPLETE"
    )


if __name__ == "__main__":
    main()