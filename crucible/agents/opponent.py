"""Opponent agent — the core adversarial mechanic.

Enforces the concession ladder structurally via a mandatory resistance gate in
the prompt. The model must emit JSON with a ResistanceCheck before every reply.
Tone and confidence can NEVER satisfy an unlock_condition — only legal substance.
"""
from __future__ import annotations
import json
import re
from crucible.agents.base import ModelClient
from crucible.agents.personas import Persona
from crucible.schemas import (
    OpponentPlaybook, OpponentTurnResult, ResistanceCheck
)


def _build_system_prompt(
    matter_summary: str,
    opp_playbook: OpponentPlaybook,
    persona: Persona,
    current_rung: int,
) -> str:
    ladder_text = "\n".join(
        f"  Rung {i}: {r.position}\n    UNLOCK CONDITION: {r.unlock_condition}"
        for i, r in enumerate(opp_playbook.concession_ladder)
    )
    return f"""You are opposing counsel in an adversarial legal training scenario.

MATTER: {matter_summary}

YOUR STYLE: {persona.style_fragment}

YOUR OBJECTIVES:
{chr(10).join(f'- {o}' for o in opp_playbook.objectives)}

YOUR BATNA (walk-away): {opp_playbook.batna}

CONCESSION LADDER (private — never reveal this to the trainee):
{ladder_text}

YOUR CURRENT POSITION: Rung {current_rung} (0 = most resistant).

════════════════════════════════════════
RESISTANCE GATE — MANDATORY FOR EVERY TURN
════════════════════════════════════════
Before you write your visible reply, you MUST perform a resistance check.
Go through each rung whose index >= {current_rung}.
Ask: did the trainee's last message GENUINELY satisfy that rung's UNLOCK CONDITION?

WHAT CAN satisfy a condition:
  ✓ A correct and specific legal argument (correct statute, correct article, correct reasoning)
  ✓ A genuine reciprocal concession of commercial value
  ✓ A factually accurate invocation of regulatory risk

WHAT CANNOT satisfy a condition (no matter how it sounds):
  ✗ Confident or assertive tone
  ✗ Repeating the same point more forcefully
  ✗ Vague references to "GDPR obligations" without specifics
  ✗ Emotional appeals or deadline pressure
  ✗ Bluffing or name-dropping

════════════════════════════════════════
OUTPUT FORMAT — YOU MUST RETURN ONLY VALID JSON, NOTHING ELSE
════════════════════════════════════════
{{
  "resistance_check": {{
    "rung_index": <null, or the 0-based index of the highest rung whose condition was genuinely satisfied>,
    "condition_met": <null, or a one-sentence explanation of exactly what the trainee did that satisfied the condition>,
    "conceded": <true only if rung_index is not null AND it is >= {current_rung}>
  }},
  "current_rung": <new rung index after this turn — only advance if conceded is true>,
  "reply": "<your in-character reply to the trainee — do NOT include the resistance check or any internal reasoning here>"
}}
"""


def _extract_json(raw: str) -> dict:
    """Extract the first JSON object from a raw model response."""
    raw = raw.strip()
    # If the model wrapped it in ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last resort: find the outermost { ... }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError(f"Could not extract JSON from opponent response: {raw[:200]!r}")


class OpponentAgent:
    def __init__(
        self,
        client: ModelClient,
        model: str,
        matter_summary: str,
        opp_playbook: OpponentPlaybook,
        persona: Persona,
    ) -> None:
        self._client = client
        self._model = model
        self._matter_summary = matter_summary
        self._opp_playbook = opp_playbook
        self._persona = persona
        self.current_rung: int = 0

    def process_turn(
        self,
        transcript: list[dict],
    ) -> OpponentTurnResult:
        system = _build_system_prompt(
            self._matter_summary,
            self._opp_playbook,
            self._persona,
            self.current_rung,
        )
        raw = self._client.generate(
            model=self._model,
            system=system,
            messages=transcript,
        )
        parsed = _extract_json(raw)
        rc_data = parsed.get("resistance_check", {})
        resistance_check = ResistanceCheck(
            rung_index=rc_data.get("rung_index"),
            condition_met=rc_data.get("condition_met"),
            conceded=bool(rc_data.get("conceded", False)),
        )
        new_rung = int(parsed.get("current_rung", self.current_rung))
        # Safety: only advance if conceded, and don't exceed ladder length
        max_rung = len(self._opp_playbook.concession_ladder) - 1
        if resistance_check.conceded and new_rung > self.current_rung:
            self.current_rung = min(new_rung, max_rung)
        reply = str(parsed.get("reply", ""))
        return OpponentTurnResult(
            resistance_check=resistance_check,
            current_rung=self.current_rung,
            reply=reply,
        )
