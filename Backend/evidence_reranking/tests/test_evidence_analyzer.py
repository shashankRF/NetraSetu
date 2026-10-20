from Backend.evidence_reranking.evidence_analyzer import (
    analyze_evidence,
    classify_evidence_role,
)


def test_supporting_evidence():

    text = (
        "The requirement states that operators shall "
        "implement authentication controls."
    )

    role, confidence = classify_evidence_role(
        text
    )

    assert role == "Supporting Evidence"
    assert confidence > 0


def test_contradicting_evidence():

    text = (
        "The available framework does not establish "
        "a mandatory requirement for this control."
    )

    role, confidence = classify_evidence_role(
        text
    )

    assert role == "Contradicting Evidence"
    assert confidence > 0


def test_contextual_evidence():

    text = (
        "This section provides background information "
        "and describes the general architecture."
    )

    role, confidence = classify_evidence_role(
        text
    )

    assert role == "Contextual Evidence"
    assert confidence > 0


def test_evidence_gaps():

    candidates = [
        {
            "evidence_id": "EV-001",
            "text": (
                "The requirement states that operators "
                "shall implement authentication."
            ),
        }
    ]

    result = analyze_evidence(
        candidates=candidates,
        query="What security requirement exists?",
        final_top_k=1,
    )

    output = result.to_dict()

    assert len(
        output["supporting_evidence"]
    ) == 1

    assert len(
        output["contradicting_evidence"]
    ) == 0

    assert (
        "No clearly contradicting evidence"
        in output["evidence_gaps"][0]
    )