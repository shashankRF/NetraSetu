from Backend.orchestrator import _fingerprint_run_inputs


def _fingerprint(question="query", passages=None):
    return _fingerprint_run_inputs(
        question=question,
        jurisdiction="India",
        scenario_id="SC-1",
        step_id="STEP-1",
        demo_mode=True,
        retrieval_k=5,
        passages=passages or [{"document": "plan.pdf", "page": 2, "text": "supporting passage"}],
    )


def test_run_fingerprint_is_stable_for_same_inputs():
    assert _fingerprint() == _fingerprint()


def test_run_fingerprint_changes_when_query_or_source_passage_changes():
    base = _fingerprint()
    assert _fingerprint(question="different query") != base
    assert _fingerprint(passages=[{"document": "plan.pdf", "page": 2, "text": "changed passage"}]) != base
