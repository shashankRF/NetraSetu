from rag.retrieval import (
    retrieve,
    JURISDICTION_PROFILES,
)


def test_india_profile_returns_only_allowed_jurisdictions():

    results = retrieve(
        "5G network slicing security",
        k=8,
        jurisdiction="India",
    )

    assert results

    allowed = JURISDICTION_PROFILES["India"]

    for result in results:

        jurisdiction = result["metadata"].get(
            "jurisdiction"
        )

        assert jurisdiction in allowed


def test_eu_profile_returns_only_allowed_jurisdictions():

    results = retrieve(
        "cybersecurity incident requirements",
        k=8,
        jurisdiction="European Union",
    )

    assert results

    allowed = JURISDICTION_PROFILES[
        "European Union"
    ]

    for result in results:

        jurisdiction = result["metadata"].get(
            "jurisdiction"
        )

        assert jurisdiction in allowed


def test_invalid_jurisdiction_rejected():

    try:

        retrieve(
            "5G security",
            k=8,
            jurisdiction="United States",
        )

    except ValueError as exc:

        assert "Unsupported jurisdiction profile" in str(
            exc
        )

    else:

        raise AssertionError(
            "Invalid jurisdiction should raise ValueError"
        )


def test_legacy_retrieval_still_works():

    results = retrieve(
        "5G network slicing security",
        k=8,
    )

    assert results
    assert len(results) <= 8