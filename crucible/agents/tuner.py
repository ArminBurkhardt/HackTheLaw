"""Difficulty Tuner — runs between rounds, adapts next-round pressure.

Reads UserProfile (recurring weaknesses, weak_vs_persona) and outputs a
TunerDirective that tells the next Opponent which weakness to probe and how
hard to press it. This is the engine behind "Run it again" doing something
different from the previous round.

The directive is injected into the Opponent's system prompt at session start.
"""
from __future__ import annotations
import json
import re

from crucible.agents.base import ModelClient
from crucible.rl import recommend_difficulty, skill_scalar
from crucible.schemas import TunerDirective, UserProfile


def _build_system_prompt(profile: UserProfile, scenario: str) -> str:
    weaknesses_text = (
        "\n".join(f"  - {w}" for w in profile.recurring_weaknesses)
        if profile.recurring_weaknesses
        else "  (no recorded weaknesses yet — this is the first round)"
    )
    persona_text = (
        "\n".join(
            f"  - {p}: weakness={v:.2f} (0=strong, 1=weak)"
            for p, v in profile.weak_vs_persona.items()
        )
        if profile.weak_vs_persona
        else "  (no persona data yet)"
    )
    scores_text = str(profile.scores) if profile.scores else "(no previous scores)"
    return f"""You are the difficulty-tuning module for a legal training system.

TRAINEE HISTORY — scenario: {scenario}
Previous scores: {scores_text}
Streak: {profile.streak} consecutive improvements

KNOWN WEAKNESSES:
{weaknesses_text}

PERFORMANCE BY PERSONA:
{persona_text}

Your task: produce a TunerDirective for the NEXT round.

The directive must:
1. Name the single most important weakness to pressure this round (target_weakness)
2. Specify an aggression adjustment (-0.3 to +0.3; positive = harder)
3. Write a pressure_note: a ONE-sentence instruction for the opponent that
   names the specific gap to exploit (e.g., "Probe the trainee's pattern of
   conceding the liability cap before locking sub-processor authorisation").

Return ONLY valid JSON:
{{
  "target_weakness": "<exact weakness string from the list above, or a concise synthesis>",
  "aggression_delta": <float -0.3 to +0.3>,
  "pressure_note": "<one sentence injected directly into the opponent prompt>"
}}

Rules:
- If there are no recorded weaknesses, set target_weakness to "general resistance" and
  aggression_delta to 0.1 (slightly harder than baseline)
- The pressure_note must be SPECIFIC — not "be harder" but "probe their tendency to X"
- Never tell the opponent to soften resistance or coach the trainee
- Return ONLY the JSON object
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1), strict=False)
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end], strict=False)
        raise ValueError(f"Could not extract JSON from tuner response: {raw[:200]!r}")


class DifficultyTuner:
    def __init__(self, client: ModelClient, model: str) -> None:
        self._client = client
        self._model = model

    def tune(
        self,
        profile: UserProfile,
        scenario: str = "negotiation",
    ) -> TunerDirective:
        """Given a UserProfile, produce a TunerDirective for the next round."""
        system = _build_system_prompt(profile, scenario)
        raw = self._client.generate(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": "Generate the tuner directive."}],
        )
        parsed = _extract_json(raw)

        # ZPD matchmaking: ground the difficulty in the IRT skill posterior so the
        # opponent holds the trainee's win-rate in the zone of proximal development.
        # The model still names the weakness (qualitative); the math sets the dial.
        skill = skill_scalar(profile.skill_theta_mean)
        zpd_delta, zpd_note = recommend_difficulty(skill)
        llm_delta = float(parsed.get("aggression_delta", 0.0))
        aggression_delta = max(-0.3, min(0.3, 0.5 * llm_delta + zpd_delta))

        pressure_note = str(parsed.get("pressure_note", "")).strip()
        pressure_note = f"{pressure_note} {zpd_note}".strip() if pressure_note else zpd_note

        return TunerDirective(
            target_weakness=str(parsed.get("target_weakness", "general resistance")),
            aggression_delta=round(aggression_delta, 4),
            pressure_note=pressure_note,
        )
