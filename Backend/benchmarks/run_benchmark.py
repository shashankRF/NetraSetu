import json
import os
import time
from datetime import datetime

from Backend.orchestrator import run_pipeline


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCHMARK_FILE = os.path.join(BASE_DIR, "benchmarks", "benchmark_questions.json")
RESULTS_DIR = os.path.join(BASE_DIR, "benchmarks", "results")
RESULTS_FILE = os.path.join(RESULTS_DIR, "benchmark_results.json")


def load_questions():
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark():
    questions = load_questions()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    results = {
        "benchmark_version": "hackgrid-benchmark-v1",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "total_questions": len(questions),
        "completed_questions": 0,
        "cases": [],
    }

    print("=" * 80)
    print("HACKGRID — RESEARCH BENCHMARK")
    print("=" * 80)
    print(f"Total questions: {len(questions)}")

    for i, case in enumerate(questions, start=1):
        case_id = case["id"]
        question = case["question"]

        print("\n" + "=" * 80)
        print(f"[{i}/{len(questions)}] {case_id}")
        print(question)
        print("=" * 80)

        started = time.time()

        try:
            pipeline_result = run_pipeline(question)

            elapsed = round(time.time() - started, 2)

            result = {
                "id": case_id,
                "question": question,
                "category": case.get("category"),
                "expected_focus": case.get("expected_focus"),
                "pipeline": pipeline_result,
                "runtime_seconds": elapsed,
                "status": "SUCCESS",
            }

            results["cases"].append(result)
            results["completed_questions"] += 1

            print(f"STATUS: SUCCESS")
            print(f"Runtime: {elapsed}s")
            print(f"Audit ID: {pipeline_result['audit_id']}")

        except Exception as e:
            elapsed = round(time.time() - started, 2)

            result = {
                "id": case_id,
                "question": question,
                "category": case.get("category"),
                "expected_focus": case.get("expected_focus"),
                "runtime_seconds": elapsed,
                "status": "FAILED",
                "error": str(e),
            }

            results["cases"].append(result)

            print("STATUS: FAILED")
            print(f"Error: {e}")

    results["finished_at"] = datetime.utcnow().isoformat() + "Z"

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print(f"Completed: {results['completed_questions']}/{results['total_questions']}")
    print(f"Results: {RESULTS_FILE}")


if __name__ == "__main__":
    run_benchmark()