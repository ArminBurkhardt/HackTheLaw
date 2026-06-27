"""Build arena-ready scenarios from uploaded playbook text."""
from __future__ import annotations

import json
import re
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from crucible.agents.base import ModelClient
from crucible.schemas import OpponentPlaybook, Playbook
from crucible.scenarios.generated import GeneratedScenario, ScenarioBrief


class ScenarioDraft(BaseModel):
    label: str
    description: str
    playbook: Playbook
    opp_playbook: OpponentPlaybook
    brief: ScenarioBrief


def build_generated_scenario(
    *,
    client: ModelClient,
    model: str,
    raw_playbook_text: str,
    filename: str,
    language: str = "en",
) -> GeneratedScenario:
    if len(raw_playbook_text.strip()) < 600:
        raise ValueError("The uploaded playbook text is too short to build a scenario.")

    raw = client.generate(
        model=model,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"LANGUAGE: {language}\n"
                    f"FILENAME: {filename}\n\n"
                    f"UPLOADED PLAYBOOK:\n{raw_playbook_text[:30000]}\n\n"
                    "Return the JSON object now."
                ),
            }
        ],
        temperature=0.15,
        max_output_tokens=6500,
    )
    data = _extract_json(raw)
    try:
        draft = ScenarioDraft.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Generated scenario did not match the arena schema: {exc}") from exc

    return GeneratedScenario(
        id=f"generated-{_slug(draft.label)}-{uuid4().hex[:8]}",
        label=draft.label[:80],
        description=draft.description[:220],
        playbook=draft.playbook,
        opp_playbook=draft.opp_playbook,
        brief=draft.brief,
    )


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        return json.loads(match.group(1), strict=False)
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end], strict=False)
        raise ValueError(f"Cannot extract JSON from scenario builder response: {raw[:200]!r}")


def _slug(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug[:40] or "scenario"


_SYSTEM_PROMPT = """You are a senior legal training scenario architect.

Convert an uploaded lawyer playbook into one arena-ready sparring scenario. The playbook is NOT the contract being negotiated. It describes what the junior lawyer should learn and how the sparring partner should behave.

Return ONLY valid JSON. No prose. No markdown fences.

Rules:
- Use the uploaded playbook as the source of truth. Do not invent a different case.
- The trainee is the junior lawyer being trained.
- The AI opponent is the counterpart, partner, client, or negotiating party described by the playbook.
- Make opponent behavior concrete: goals, pressure tactics, concession ladder, BATNA.
- Make trainee goals measurable: must-haves, traps, model moves, fallback discipline.
- Keep legal authorities from the playbook as source "firm_playbook". Do not add web sources.
- Set playbook.scenario to "negotiation" unless the uploaded playbook is clearly a hot-seat or difficult-client exercise.
- Use German labels and briefing text when LANGUAGE is "de"; otherwise use English.
- Build 5-8 playbook.items. Include at least two "must_have", one "trap", and one "model_move".
- Build 3-5 opponent concession_ladder rungs ordered from hardest opening position to best realistic concession.

Exact JSON shape:
{
  "label": "<short scenario name>",
  "description": "<one sentence describing the training case>",
  "playbook": {
    "scenario": "negotiation",
    "matter_summary": "<training case summary and role setup>",
    "objectives": ["<trainee learning objective>", "..."],
    "items": [
      {
        "id": "<snake_case_id>",
        "label": "<short label>",
        "kind": "must_have",
        "target": "<what a good trainee move looks like>",
        "walk_away": "<line not to cross, or null>",
        "authorities": [
          {"celex": null, "eli": null, "title": "<authority or playbook rule>", "pinpoint": "<section>", "source": "firm_playbook", "url": null}
        ],
        "weight": 1.0
      }
    ],
    "fallback_ladder": ["<fallback step>", "..."],
    "walk_away_conditions": ["<condition>", "..."],
    "authorities": [
      {"celex": null, "eli": null, "title": "<authority or playbook rule>", "pinpoint": "<section>", "source": "firm_playbook", "url": null}
    ]
  },
  "opp_playbook": {
    "objectives": ["<opponent objective>", "..."],
    "batna": "<opponent walk-away or escalation path>",
    "concession_ladder": [
      {"position": "<opponent position>", "unlock_condition": "<specific trainee behavior required>"}
    ]
  },
  "brief": {
    "authorities": [
      {"title": "<authority or rule>", "pinpoint": "<pinpoint>", "note": "<why it matters in the session>"}
    ],
    "strategy": ["<pre-session trainee strategy tip>", "..."],
    "watchOut": ["<trap or behavior to avoid>", "..."]
  }
}
"""
