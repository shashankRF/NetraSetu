from Backend.demo_scenarios.library import get_scenarios, get_scenario


def test_scenario_library_has_required_domains():
    scenarios = get_scenarios()

    assert len(scenarios) >= 7

    domains = {scenario["domain"] for scenario in scenarios}

    assert "Defence" in domains
    assert "Maritime" in domains
    assert "Telecom/5G" in domains
    assert "Research" in domains
    assert "Enterprise Incident" in domains


def test_eu_scenario_exists():
    scenarios = get_scenarios()

    eu_scenarios = [
        scenario
        for scenario in scenarios
        if scenario["jurisdiction"] == "European Union"
    ]

    assert len(eu_scenarios) >= 1


def test_all_scenarios_are_explicitly_simulated():
    scenarios = get_scenarios()

    assert all(
        scenario["simulated"] is True
        for scenario in scenarios
    )


def test_all_scenarios_have_steps():
    scenarios = get_scenarios()

    assert all(
        len(scenario["steps"]) >= 2
        for scenario in scenarios
    )


def test_lookup_scenario():
    scenario = get_scenario("HG-DEFENCE-001")

    assert scenario is not None
    assert scenario["domain"] == "Defence"
    assert scenario["jurisdiction"] == "India"


def test_unknown_scenario_returns_none():
    assert get_scenario("DOES-NOT-EXIST") is None