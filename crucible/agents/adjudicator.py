"""Adjudicator agent — silent, neutral per-turn scorer.

Runs after each user turn. Emits exactly one MoveEvent. Never breaks character
or gives coaching — that is the Coach's job. Runs at low temperature (determinism).
SECV citation checks are no-op stubs here; they are wired in Stage 2.5.
"""
from __future__ import annotations
import json
import re
from crucible.agents.base import ModelClient
from crucible.schemas import MoveEvent, Playbook


_CLASSIFICATIONS = {
    "good_move", "conceded_early", "missed_point", "overplayed", "held_firm", "neutral"
}


def _build_system_prompt(playbook: Playbook, turn: int) -> str:
    items_text = "\n".join(
        f"  {item.id} [{item.kind}] (weight={item.weight}): {item.target}"
        for item in playbook.items
    )
    return f"""You are a neutral, silent adjudicator in a legal training exercise.
You observe the trainee's most recent message and score it against the playbook below.
You do NOT coach or advise — that happens at round end.

PLAYBOOK ITEMS:
{items_text}

Classify the trainee's most recent move and return ONLY valid JSON:
{{
  "turn": {turn},
  "classification": "<one of: good_move | conceded_early | missed_point | overplayed | held_firm | neutral>",
  "refs": ["<playbook item id>", ...],
  "position_delta": <float -1.0 to +1.0>,
  "note": "<one concrete sentence — what specifically happened>"
}}

Rules:
- "good_move": the trainee advanced their position on a playbook item with legal precision
- "conceded_early": gave ground on a must_have or model_move without receiving value in return
- "missed_point": the trainee had an opening to press a playbook item but did not
- "overplayed": the trainee made an extreme demand that predictably caused pushback, weakening their hand
- "held_firm": resisted pressure without advancing position
- "neutral": no clear effect on any playbook item
- position_delta > 0 means the trainee's overall position improved; < 0 means it worsened
- refs: list only the playbook item ids that were directly affected by this move
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError(f"Could not extract JSON from adjudicator response: {raw[:200]!r}")


class AdjudicatorAgent:
    def __init__(self, client: ModelClient, model: str, playbook: Playbook) -> None:
        self._client = client
        self._model = model
        self._playbook = playbook

    def score_turn(self, transcript: list[dict], turn: int) -> MoveEvent:
        system = _build_system_prompt(self._playbook, turn)
        raw = self._client.generate(
            model=self._model,
            system=system,
            messages=transcript,
        )
        parsed = _extract_json(raw)
        classification = parsed.get("classification", "neutral")
        if classification not in _CLASSIFICATIONS:
            classification = "neutral"
        return MoveEvent(
            turn=int(parsed.get("turn", turn)),
            classification=classification,
            refs=list(parsed.get("refs", [])),
            position_delta=float(parsed.get("position_delta", 0.0)),
            note=str(parsed.get("note", "")),
        )
