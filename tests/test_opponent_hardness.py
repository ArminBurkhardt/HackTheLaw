"""Opponent hardness prompt wiring tests."""
from __future__ import annotations

import json

from crucible.agents.base import FakeModelClient
from crucible.agents.opponent import OpponentAgent
from crucible.agents.personas import AGGRESSOR
from crucible.scenarios.fixtures.saas_license_negotiation import OPPONENT_PLAYBOOK


def test_hardness_directive_reaches_resistance_prompt():
    """Selected hardness must affect the real opponent prompt, not just UI state."""
    captured_systems: list[str] = []

    def capture_generate(*, model: str, system: str, messages: list[dict], **kw) -> str:
        captured_systems.append(system)
        return json.dumps({
            "resistance_check": {
                "rung_index": None,
                "condition_met": None,
                "conceded": False,
            },
            "current_rung": 0,
            "reply": "We need a more concrete position before changing our cap.",
        })

    opponent = OpponentAgent(
        client=FakeModelClient(capture_generate),
        model="gemini-2.5-flash",
        matter_summary="SaaS liability negotiation",
        opp_playbook=OPPONENT_PLAYBOOK,
        persona=AGGRESSOR,
        hardness_directive="Hard mode marker: require precise trade-offs.",
    )
    opponent.process_turn([{"role": "user", "content": "We need better liability."}])

    assert captured_systems
    assert "THIS ROUND'S HARDNESS SETTING" in captured_systems[0]
    assert "Hard mode marker: require precise trade-offs." in captured_systems[0]
