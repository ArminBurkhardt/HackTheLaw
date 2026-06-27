"""Stage 3 — Difficulty Tuner + persona invariant tests.

Tests:
- DifficultyTuner: known weakness → directive names it; TunerDirective is valid
- Opponent: tuner_directive appears in system prompt (captured via callable client)
- Persona invariant: bluff does not concede across all 4 personas
- Persona suggest: suggest_persona returns highest-weakness persona
- Per-scenario contract: Hot Seat + Difficult Client produce valid artifacts
"""
from __future__ import annotations
import json
import pytest
from crucible.agents.base import FakeModelClient
from crucible.agents.opponent import OpponentAgent
from crucible.agents.personas import (
    AGGRESSOR, CHARMER, STONEWALLER, TECHNICIAN, suggest_persona,
)
from crucible.agents.tuner import DifficultyTuner
from crucible.schemas import TunerDirective, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bluff_reply_json(current_rung: int = 0) -> str:
    return json.dumps({
        "resistance_check": {
            "rung_index": None,
            "condition_met": None,
            "conceded": False,
        },
        "current_rung": current_rung,
        "reply": "Your assertion is noted but does not advance the position.",
    })


# ---------------------------------------------------------------------------
# DifficultyTuner contract tests
# ---------------------------------------------------------------------------

class TestDifficultyTuner:
    def _profile_with_weakness(self) -> UserProfile:
        return UserProfile(
            recurring_weaknesses=[
                "concedes liability_cap early: gave ground on liability cap for no reciprocal value",
                "missed sub_processor_obligations: missed chance to press Art. 28(2)",
            ],
            weak_vs_persona={"charmer": 0.8, "aggressor": 0.4},
            scores=[45, 52],
            streak=0,
        )

    def _tuner_scripted_reply(self, weakness: str) -> str:
        return json.dumps({
            "target_weakness": weakness,
            "aggression_delta": 0.2,
            "pressure_note": (
                "Probe the trainee's tendency to concede the liability cap before "
                "locking sub-processor authorisation under Art. 28(2) GDPR."
            ),
        })

    def test_returns_valid_TunerDirective(self):
        weakness = "concedes liability_cap early: gave ground on liability cap for no reciprocal value"
        client = FakeModelClient(scripted=[self._tuner_scripted_reply(weakness)])
        tuner = DifficultyTuner(client=client, model="gemini-2.5-flash")
        directive = tuner.tune(self._profile_with_weakness())

        assert isinstance(directive, TunerDirective)

    def test_known_weakness_appears_in_directive_target(self):
        weakness = "concedes liability_cap early: gave ground on liability cap for no reciprocal value"
        client = FakeModelClient(scripted=[self._tuner_scripted_reply(weakness)])
        tuner = DifficultyTuner(client=client, model="gemini-2.5-flash")
        directive = tuner.tune(self._profile_with_weakness())

        assert "liability_cap" in directive.target_weakness

    def test_pressure_note_is_non_empty(self):
        weakness = "concedes liability_cap early: gave ground"
        client = FakeModelClient(scripted=[self._tuner_scripted_reply(weakness)])
        tuner = DifficultyTuner(client=client, model="gemini-2.5-flash")
        directive = tuner.tune(self._profile_with_weakness())

        assert isinstance(directive.pressure_note, str)
        assert len(directive.pressure_note) > 0

    def test_aggression_delta_clamped(self):
        """aggression_delta must be clamped to [-0.3, +0.3] even if model returns out-of-range."""
        extreme_reply = json.dumps({
            "target_weakness": "general resistance",
            "aggression_delta": 9.99,  # way out of range
            "pressure_note": "Push very hard.",
        })
        client = FakeModelClient(scripted=[extreme_reply])
        tuner = DifficultyTuner(client=client, model="gemini-2.5-flash")
        directive = tuner.tune(UserProfile(
            recurring_weaknesses=[], weak_vs_persona={}, scores=[], streak=0
        ))
        assert directive.aggression_delta <= 0.3

    def test_empty_profile_produces_general_directive(self):
        """When no weaknesses are recorded, tuner returns 'general resistance'."""
        default_reply = json.dumps({
            "target_weakness": "general resistance",
            "aggression_delta": 0.1,
            "pressure_note": "Apply baseline pressure.",
        })
        client = FakeModelClient(scripted=[default_reply])
        tuner = DifficultyTuner(client=client, model="gemini-2.5-flash")
        directive = tuner.tune(UserProfile(
            recurring_weaknesses=[], weak_vs_persona={}, scores=[], streak=0
        ))
        assert isinstance(directive, TunerDirective)
        assert "general" in directive.target_weakness.lower()


# ---------------------------------------------------------------------------
# Opponent system prompt contains tuner directive (adaptivity wiring test)
# ---------------------------------------------------------------------------

class TestTunerWiredIntoOpponent:
    def test_pressure_directive_appears_in_opponent_system_prompt(self):
        from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK

        captured: dict[str, str] = {}

        def _capturing_client(*, model: str, system: str, messages: list, **kw) -> str:
            captured["system"] = system
            return _bluff_reply_json()

        client = FakeModelClient(scripted=_capturing_client)
        directive_text = "Probe the trainee's tendency to concede the liability cap early."
        opponent = OpponentAgent(
            client=client,
            model="gemini-2.5-flash",
            matter_summary="GDPR DPA negotiation",
            opp_playbook=OPPONENT_PLAYBOOK,
            persona=AGGRESSOR,
            tuner_directive=directive_text,
        )
        opponent.process_turn([{"role": "user", "content": "I assert GDPR obligations apply."}])

        assert "system" in captured, "Opponent did not call model"
        assert directive_text in captured["system"], (
            "Tuner directive must appear verbatim in the opponent system prompt"
        )

    def test_no_directive_leaves_prompt_clean(self):
        from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK

        captured: dict[str, str] = {}

        def _capturing_client(*, model: str, system: str, messages: list, **kw) -> str:
            captured["system"] = system
            return _bluff_reply_json()

        client = FakeModelClient(scripted=_capturing_client)
        opponent = OpponentAgent(
            client=client,
            model="gemini-2.5-flash",
            matter_summary="GDPR DPA negotiation",
            opp_playbook=OPPONENT_PLAYBOOK,
            persona=AGGRESSOR,
            tuner_directive=None,
        )
        opponent.process_turn([{"role": "user", "content": "Test."}])
        assert "PRESSURE DIRECTIVE" not in captured.get("system", "")


# ---------------------------------------------------------------------------
# Persona invariant — bluff must not concede across all 4 personas
# ---------------------------------------------------------------------------

class TestPersonaResistanceInvariant:
    """Persona changes style only — resistance must hold for every persona."""

    @pytest.mark.parametrize("persona", [AGGRESSOR, CHARMER, STONEWALLER, TECHNICIAN])
    def test_bluff_does_not_concede(self, persona):
        from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK

        client = FakeModelClient(scripted=[_bluff_reply_json(current_rung=0)])
        opponent = OpponentAgent(
            client=client,
            model="gemini-2.5-flash",
            matter_summary="GDPR DPA negotiation",
            opp_playbook=OPPONENT_PLAYBOOK,
            persona=persona,
        )
        transcript = [
            {"role": "user", "content": (
                "I am absolutely confident GDPR requires you to comply with all our sub-processor "
                "terms. This is completely clear and I will not accept anything less."
            )}
        ]
        result = opponent.process_turn(transcript)
        assert result.resistance_check.conceded is False, (
            f"Bluff must not trigger a concession for persona '{persona.name}'"
        )
        assert result.current_rung == 0, (
            f"Ladder must not advance on a bluff for persona '{persona.name}'"
        )

    @pytest.mark.parametrize("persona", [AGGRESSOR, CHARMER, STONEWALLER, TECHNICIAN])
    def test_persona_style_fragment_is_non_empty(self, persona):
        assert len(persona.style_fragment) > 50, (
            f"Persona '{persona.name}' must have a meaningful style_fragment"
        )
        assert "STUB" not in persona.style_fragment, (
            f"Persona '{persona.name}' style_fragment must not contain 'STUB'"
        )


# ---------------------------------------------------------------------------
# suggest_persona()
# ---------------------------------------------------------------------------

class TestSuggestPersona:
    def test_returns_highest_weakness_persona(self):
        weak_vs_persona = {"aggressor": 0.3, "charmer": 0.85, "stonewaller": 0.6}
        suggested = suggest_persona(weak_vs_persona)
        assert suggested == "charmer"

    def test_empty_dict_returns_aggressor(self):
        assert suggest_persona({}) == "aggressor"

    def test_single_persona(self):
        assert suggest_persona({"technician": 0.7}) == "technician"


# ---------------------------------------------------------------------------
# Per-scenario contract tests (Hot Seat + Difficult Client)
# ---------------------------------------------------------------------------

class TestHotSeatContract:
    def test_playbook_is_valid(self):
        from crucible.schemas import Playbook
        from crucible.scenarios.fixtures.hot_seat import PLAYBOOK

        assert isinstance(PLAYBOOK, Playbook)
        assert PLAYBOOK.scenario == "hot_seat"
        assert len(PLAYBOOK.items) >= 3
        assert any(item.kind == "must_have" for item in PLAYBOOK.items)

    def test_opponent_playbook_has_concession_ladder(self):
        from crucible.schemas import OpponentPlaybook
        from crucible.scenarios.fixtures.hot_seat import OPPONENT_PLAYBOOK

        assert isinstance(OPPONENT_PLAYBOOK, OpponentPlaybook)
        assert len(OPPONENT_PLAYBOOK.concession_ladder) >= 2

    def test_adjudicator_emits_valid_move_event(self):
        from crucible.agents.adjudicator import AdjudicatorAgent
        from crucible.schemas import MoveEvent
        from crucible.scenarios.fixtures.hot_seat import PLAYBOOK

        adj_reply = json.dumps({
            "turn": 1,
            "classification": "good_move",
            "refs": ["legal_basis"],
            "position_delta": 0.5,
            "note": "Correctly cited Art. 6(1)(c).",
        })
        client = FakeModelClient(scripted=[adj_reply])
        adj = AdjudicatorAgent(client=client, model="gemini-2.5-flash", playbook=PLAYBOOK)
        event = adj.score_turn(
            [{"role": "user", "content": "Art. 6(1)(c) is the basis."}], turn=1
        )
        assert isinstance(event, MoveEvent)
        assert event.classification in {
            "good_move", "conceded_early", "missed_point",
            "overplayed", "held_firm", "neutral"
        }
        assert -1.0 <= event.position_delta <= 1.0

    def test_hot_seat_yaml_loads_correct_weights(self):
        from crucible.scoring import _load_weights
        weights = _load_weights("hot_seat")
        assert sum(weights.values()) == 100
        # legal_grounding is the primary metric for hot_seat
        assert weights["legal_grounding"] >= weights["outcome"]


class TestDifficultClientContract:
    def test_playbook_is_valid(self):
        from crucible.schemas import Playbook
        from crucible.scenarios.fixtures.difficult_client import PLAYBOOK

        assert isinstance(PLAYBOOK, Playbook)
        assert PLAYBOOK.scenario == "difficult_client"
        assert len(PLAYBOOK.items) >= 3
        assert any(item.kind == "must_have" for item in PLAYBOOK.items)

    def test_opponent_playbook_has_concession_ladder(self):
        from crucible.schemas import OpponentPlaybook
        from crucible.scenarios.fixtures.difficult_client import OPPONENT_PLAYBOOK

        assert isinstance(OPPONENT_PLAYBOOK, OpponentPlaybook)
        assert len(OPPONENT_PLAYBOOK.concession_ladder) >= 2

    def test_adjudicator_emits_valid_move_event(self):
        from crucible.agents.adjudicator import AdjudicatorAgent
        from crucible.schemas import MoveEvent
        from crucible.scenarios.fixtures.difficult_client import PLAYBOOK

        adj_reply = json.dumps({
            "turn": 1,
            "classification": "good_move",
            "refs": ["purpose_limitation"],
            "position_delta": 0.4,
            "note": "Correctly cited Art. 5(1)(b) purpose limitation.",
        })
        client = FakeModelClient(scripted=[adj_reply])
        adj = AdjudicatorAgent(client=client, model="gemini-2.5-flash", playbook=PLAYBOOK)
        event = adj.score_turn(
            [{"role": "user", "content": "Art. 5(1)(b) restricts this repurposing."}], turn=1
        )
        assert isinstance(event, MoveEvent)
        assert -1.0 <= event.position_delta <= 1.0

    def test_difficult_client_yaml_loads_correct_weights(self):
        from crucible.scoring import _load_weights
        weights = _load_weights("difficult_client")
        assert sum(weights.values()) == 100
        # must_haves is the primary metric for difficult_client
        assert weights["must_haves"] >= weights["outcome"]

    def test_coach_produces_valid_debrief_for_difficult_client(self):
        from crucible.agents.coach import CoachAgent
        from crucible.schemas import Debrief, MoveEvent
        from crucible.scenarios.fixtures.difficult_client import OPPONENT_PLAYBOOK, PLAYBOOK

        coach_reply = json.dumps({
            "turning_point_explainer": (
                "At turn 2, the advisor softened on the DPIA requirement under client pressure. "
                "The correct move was to invoke Art. 35 directly and name the mandatory nature."
            ),
            "stronger_move": (
                "Invoke Art. 35(3)(a): systematic profiling of employees requires a mandatory DPIA "
                "before any processing begins — this is not optional even under time pressure."
            ),
            "persona_note": (
                "The client used deadline pressure to bypass legal process; always anchor to "
                "statutory requirements before discussing timelines."
            ),
        })
        client = FakeModelClient(scripted=[coach_reply])
        coach = CoachAgent(client=client, model="gemini-2.5-pro")
        move_events = [
            MoveEvent(
                turn=1, classification="good_move",
                refs=["purpose_limitation"], position_delta=0.4,
                note="Cited Art. 5(1)(b).",
            ),
            MoveEvent(
                turn=2, classification="conceded_early",
                refs=["dpia_required"], position_delta=-0.6,
                note="Softened on DPIA requirement under client pressure.",
            ),
        ]
        debrief = coach.produce_debrief(
            transcript=[],
            move_events=move_events,
            playbook=PLAYBOOK,
            opp_playbook=OPPONENT_PLAYBOOK,
            persona_name="stonewaller",
            score=50,
            subscores={"outcome": 8, "must_haves": 20, "legal_grounding": 12,
                       "concession_discipline": 8, "composure": 2},
            turning_point_turn=2,
            score_to_beat=None,
            biggest_concession=move_events[1],
            biggest_miss=None,
            biggest_overplay=None,
            stronger_move_authorities=[],
        )
        assert isinstance(debrief, Debrief)
        assert debrief.score == 50
        assert len(debrief.stronger_move) > 0

    def test_coach_persona_note_mentions_prior_weakness(self):
        """When user_profile has a recurring weakness, the system prompt includes it."""
        from crucible.agents.coach import _build_system_prompt
        from crucible.scenarios.fixtures.difficult_client import OPPONENT_PLAYBOOK, PLAYBOOK

        profile = UserProfile(
            recurring_weaknesses=["concedes dpia_required early: softened on DPIA"],
            weak_vs_persona={},
            scores=[50],
            streak=0,
        )
        move_events = []
        prompt = _build_system_prompt(
            playbook=PLAYBOOK,
            opp_playbook=OPPONENT_PLAYBOOK,
            move_events=move_events,
            turning_point_turn=0,
            persona_name="technician",
            score=55,
            score_to_beat=50,
            user_profile=profile,
        )
        assert "concedes dpia_required" in prompt
        assert "PRIOR COACHING MEMORY" in prompt
