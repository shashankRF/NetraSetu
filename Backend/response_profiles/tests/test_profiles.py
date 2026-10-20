from Backend.response_profiles.profiles import (
    get_profile,
)


def test_telecom_profile():

    profile = get_profile(
        "Telecom/5G"
    )

    assert profile.domain == "Telecom/5G"

    assert (
        "Root-Cause Analysis"
        in profile.sections
    )

    assert (
        "Remediation"
        in profile.sections
    )


def test_maritime_profile():

    profile = get_profile(
        "Maritime"
    )

    assert (
        "Vessel/AIS Findings"
        in profile.sections
    )

    assert (
        "Timeline"
        in profile.sections
    )


def test_policy_profile():

    profile = get_profile(
        "Policy/Compliance"
    )

    assert (
        "Requirement Comparison"
        in profile.sections
    )

    assert (
        "Gap"
        in profile.sections
    )


def test_research_profile():

    profile = get_profile(
        "Research"
    )

    assert (
        "Research Gaps"
        in profile.sections
    )

    assert (
        "Contradictory Findings"
        in profile.sections
    )


def test_defence_profile():

    profile = get_profile(
        "Defence"
    )

    assert (
        "Uncertainty"
        in profile.sections
    )

    assert (
        "Evidence Gaps"
        in profile.sections
    )


def test_fallback_profile():

    profile = get_profile(
        "Unknown Domain"
    )

    assert (
        profile.domain
        == "General Evidence"
    )