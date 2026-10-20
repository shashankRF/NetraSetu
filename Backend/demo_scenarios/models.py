from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ScenarioStep:
    step_id: str
    title: str
    event: str
    evidence_prompt: str
    verified_source: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    title: str
    domain: str
    jurisdiction: str
    description: str
    simulated: bool
    steps: List[ScenarioStep]
    verified_source: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "domain": self.domain,
            "jurisdiction": self.jurisdiction,
            "description": self.description,
            "simulated": self.simulated,
            "verified_source": self.verified_source,
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "event": step.event,
                    "evidence_prompt": step.evidence_prompt,
                    "verified_source": step.verified_source,
                }
                for step in self.steps
            ],
        }
