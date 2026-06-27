"""Session-local generated scenario registry."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from crucible.schemas import OpponentPlaybook, Playbook


class BriefEntry(BaseModel):
    title: str
    pinpoint: str
    note: str


class ScenarioBrief(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    authorities: list[BriefEntry]
    strategy: list[str]
    watch_out: list[str] = Field(alias="watchOut")

    def frontend_dict(self) -> dict:
        return {
            "authorities": [entry.model_dump() for entry in self.authorities],
            "strategy": self.strategy,
            "watchOut": self.watch_out,
        }


class GeneratedScenario(BaseModel):
    id: str
    label: str
    description: str
    playbook: Playbook
    opp_playbook: OpponentPlaybook
    brief: ScenarioBrief

    def frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "available": True,
            "brief": self.brief.frontend_dict(),
        }


_GENERATED_SCENARIOS: dict[str, GeneratedScenario] = {}


def register_generated_scenario(scenario: GeneratedScenario) -> GeneratedScenario:
    _GENERATED_SCENARIOS[scenario.id] = scenario
    return scenario


def get_generated_scenario(scenario_id: str) -> GeneratedScenario | None:
    return _GENERATED_SCENARIOS.get(scenario_id)
