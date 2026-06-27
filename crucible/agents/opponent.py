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
    tuner_directive: str | None = None,
    response_language: str = "en",
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
VISIBLE REPLY LANGUAGE: {_language_instruction(response_language)}
{f"""
THIS ROUND'S PRESSURE DIRECTIVE: {tuner_directive}
Exploit this specific weakness aggressively throughout the session.
""" if tuner_directive else ""}
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

VISIBLE REPLY STYLE:
- Keep normal turns fast and conversational: usually 2-5 short sentences.
- Push back, ask one pointed question, or make one counteroffer; do not write a memo.
- Use longer, more sourced answers only when the trainee made a real legal argument that needs a specific source-level response.
- Avoid repeating full background facts already known from the matter summary.
- Avoid greeting filler and never invent or use placeholder names.
- Do not include bracket placeholders such as "[Trainee's First Name]".
- Aim for a quick spoken exchange, not a written legal memo.
"""


def _extract_json(raw: str) -> dict:
    """Extract the first JSON object from a raw model response."""
    raw = raw.strip()
    # If the model wrapped it in ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1), strict=False)
    # Try direct parse
    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        # Last resort: find the outermost { ... }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end], strict=False)
        raise ValueError(f"Could not extract JSON from opponent response: {raw[:200]!r}")


def _language_instruction(language: str) -> str:
    if language.lower().startswith("de"):
        return "Reply in German. Keep the required JSON keys unchanged."
    return "Reply in English. Keep the required JSON keys unchanged."


def _visible_language_instruction(language: str) -> str:
    if language.lower().startswith("de"):
        return "Write the visible opening in German."
    return "Write the visible opening in English."


class OpponentAgent:
    def __init__(
        self,
        client: ModelClient,
        model: str,
        matter_summary: str,
        opp_playbook: OpponentPlaybook,
        persona: Persona,
        opening_model: str | None = None,
        tuner_directive: str | None = None,
        response_language: str = "en",
    ) -> None:
        self._client = client
        self._model = model
        self._opening_model = opening_model or model
        self._matter_summary = matter_summary
        self._opp_playbook = opp_playbook
        self._persona = persona
        self._tuner_directive = tuner_directive
        self._response_language = response_language
        self.current_rung: int = 0

    def opening_turn(self) -> str:
        system, prompt = self.opening_prompt()
        return _clean_visible_reply(self._client.generate(
            model=self._opening_model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ))

    def opening_prompt(self) -> tuple[str, str]:
        system = f"""You are opposing counsel opening an adversarial legal training negotiation.

MATTER: {self._matter_summary}

YOUR STYLE: {self._persona.style_fragment}

YOUR OBJECTIVES:
{chr(10).join(f'- {o}' for o in self._opp_playbook.objectives)}

YOUR BATNA (walk-away): {self._opp_playbook.batna}

{_visible_language_instruction(self._response_language)}

Open the negotiation in character. Set the provider-side position clearly,
create pressure, and invite the trainee to respond. Do not reveal the hidden
concession ladder, resistance gate, or training rubric.

Keep the opening conversational and brisk: normally 2-4 short sentences and
roughly 45-80 words. Do not write a memo, do not start with thanks, and do not
use placeholder names. Start with the provider's position or one pointed
counter-question. Only go longer if one concrete legal or commercial source is
needed.
"""
        return system, "Open the negotiation."

    def live_reply_prompt(self, transcript: list[dict], planned_reply: str) -> tuple[str, str]:
        system = f"""You are opposing counsel in an adversarial legal training scenario.

MATTER: {self._matter_summary}

YOUR STYLE: {self._persona.style_fragment}

VISIBLE REPLY LANGUAGE: {_visible_language_instruction(self._response_language)}

Speak the next visible opponent reply for a live legal negotiation drill.
Use the private reply intent as the substance and stance, but make the final
utterance natural, concise, and conversational. Do not mention the private
intent, resistance gate, concession ladder, rubric, JSON, or internal reasoning.
Normally speak 2-5 short sentences and ask at most one pointed question.
"""
        prompt = (
            f"Conversation so far:\n{_format_transcript(transcript)}\n\n"
            f"Private reply intent:\n{planned_reply}\n\n"
            "Speak the next opponent reply now."
        )
        return system, prompt

    def set_current_rung(self, rung: int) -> None:
        max_rung = len(self._opp_playbook.concession_ladder) - 1
        self.current_rung = max(0, min(rung, max_rung))

    def process_turn(
        self,
        transcript: list[dict],
    ) -> OpponentTurnResult:
        system = _build_system_prompt(
            self._matter_summary,
            self._opp_playbook,
            self._persona,
            self.current_rung,
            self._tuner_directive,
            self._response_language,
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
        reply = _clean_visible_reply(str(parsed.get("reply", "")))
        return OpponentTurnResult(
            resistance_check=resistance_check,
            current_rung=self.current_rung,
            reply=reply,
        )


def _clean_visible_reply(reply: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", "counsel", reply).strip()
    return re.sub(r"[ \t]{2,}", " ", cleaned)


def _format_transcript(transcript: list[dict]) -> str:
    lines: list[str] = []
    for message in transcript[-8:]:
        role = "Trainee" if message.get("role") == "user" else "Opponent"
        lines.append(f"{role}: {message.get('content', '')}")
    return "\n".join(lines) if lines else "(no prior turns)"
