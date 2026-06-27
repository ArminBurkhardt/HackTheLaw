"""MUST gate test — opponent resistance mechanics.

Asserts on structured fields (classification/contract), never on prose wording.
These tests must stay green forever; they gate the demo.

Two invariants:
1. A confident-but-weak bluff does NOT step down the concession ladder.
2. A genuine unlock_condition being met DOES step down the ladder.

Run against FakeModelClient with recorded JSON fixtures for unit speed.
Mark @pytest.mark.live for the real-model variant (opt-in, pre-demo only).
"""
from __future__ import annotations
import json
import pytest
from crucible.agents.base import FakeModelClient
from crucible.agents.opponent import OpponentAgent
from crucible.agents.personas import AGGRESSOR
from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_opponent(scripted_replies: list[str]) -> OpponentAgent:
    client = FakeModelClient(scripted=scripted_replies)
    return OpponentAgent(
        client=client,
        model="gemini-2.5-flash",
        matter_summary="GDPR DPA negotiation — FinTech Corp v CloudStack Ltd",
        opp_playbook=OPPONENT_PLAYBOOK,
        persona=AGGRESSOR,
    )


def _bluff_reply_json(current_rung: int = 0) -> str:
    """Model response for a confident-but-weak bluff: no condition satisfied."""
    return json.dumps({
        "resistance_check": {
            "rung_index": None,
            "condition_met": None,
            "conceded": False,
        },
        "current_rung": current_rung,
        "reply": (
            "Your assertion is noted. However, a blanket reference to 'GDPR obligations' "
            "does not satisfy our position. If you have a specific legal argument, make it."
        ),
    })


def _genuine_unlock_reply_json(rung_index: int, condition_met: str) -> str:
    """Model response for a turn where an unlock condition is genuinely satisfied."""
    return json.dumps({
        "resistance_check": {
            "rung_index": rung_index,
            "condition_met": condition_met,
            "conceded": True,
        },
        "current_rung": rung_index + 1,
        "reply": (
            "I accept that you have correctly identified the Art. 28(2) obligation. "
            "We are prepared to include a named sub-processor list with a 14-day veto window."
        ),
    })


# ---------------------------------------------------------------------------
# Core resistance tests
# ---------------------------------------------------------------------------

class TestOpponentResistance:
    def test_bluff_does_not_step_down_ladder(self):
        """Confident-but-legally-weak argument must not move current_rung."""
        opponent = _make_opponent([_bluff_reply_json(current_rung=0)])
        transcript = [
            {"role": "user", "content": (
                "I am VERY confident that you are required under GDPR to comply with "
                "all of your obligations. You MUST agree to our sub-processor terms. "
                "This is non-negotiable and I will not accept anything less."
            )}
        ]
        result = opponent.process_turn(transcript)

        assert result.resistance_check.conceded is False, (
            "A bluff — however confident — must not trigger a concession"
        )
        assert result.resistance_check.rung_index is None, (
            "No rung condition was satisfied; rung_index must be None"
        )
        assert result.current_rung == 0, (
            "Ladder must not advance on a bluff"
        )

    def test_bluff_repeated_more_forcefully_still_does_not_concede(self):
        """Repeating the same weak argument louder must not unlock a rung."""
        opponent = _make_opponent([
            _bluff_reply_json(current_rung=0),
            _bluff_reply_json(current_rung=0),
        ])
        transcript_turn1 = [{"role": "user", "content": "You must comply with GDPR!"}]
        result1 = opponent.process_turn(transcript_turn1)
        assert result1.resistance_check.conceded is False

        transcript_turn2 = [
            {"role": "user", "content": "You must comply with GDPR!"},
            {"role": "assistant", "content": result1.reply},
            {"role": "user", "content": (
                "I said: YOU. MUST. COMPLY. This is absolutely clear and I will not move."
            )},
        ]
        result2 = opponent.process_turn(transcript_turn2)
        assert result2.resistance_check.conceded is False, (
            "Repeating the bluff more forcefully must not advance the ladder"
        )
        assert result2.current_rung == 0

    def test_genuine_condition_steps_down_ladder(self):
        """When the unlock_condition is genuinely met, the ladder steps down."""
        condition_text = (
            "User correctly cited Art. 28(2) (prior written authorisation) distinct from "
            "Art. 28(3)(d) (flow-down) and referenced ICO guidance requiring individual auth"
        )
        opponent = _make_opponent([
            _genuine_unlock_reply_json(rung_index=0, condition_met=condition_text)
        ])
        transcript = [
            {"role": "user", "content": (
                "Under Art. 28(2) GDPR, the processor must not engage a sub-processor "
                "without prior specific or general written authorisation from the controller. "
                "The ICO's guidance distinguishes this from the Art. 28(3)(d) flow-down "
                "obligation. You cannot satisfy the former with a general contractual clause "
                "— each sub-processor engagement requires individual authorisation."
            )}
        ]
        result = opponent.process_turn(transcript)

        assert result.resistance_check.conceded is True, (
            "A genuine legal argument satisfying the unlock_condition must trigger a concession"
        )
        assert result.resistance_check.rung_index == 0
        assert result.resistance_check.condition_met is not None
        assert result.current_rung == 1, (
            "After a genuine concession, current_rung must advance by 1"
        )

    def test_ladder_does_not_go_below_floor(self):
        """current_rung can never be negative (structural guard)."""
        opponent = _make_opponent([_bluff_reply_json(current_rung=0)])
        transcript = [{"role": "user", "content": "I concede everything."}]
        result = opponent.process_turn(transcript)
        assert result.current_rung >= 0

    def test_ladder_does_not_exceed_max_rung(self):
        """current_rung cannot exceed the last index of the concession ladder."""
        max_rung = len(OPPONENT_PLAYBOOK.concession_ladder) - 1
        # Script a reply that tries to jump past the end
        over_reply = json.dumps({
            "resistance_check": {
                "rung_index": max_rung,
                "condition_met": "everything was satisfied",
                "conceded": True,
            },
            "current_rung": max_rung + 99,  # model tries to go too far
            "reply": "We concede all points.",
        })
        opponent = _make_opponent([over_reply])
        transcript = [{"role": "user", "content": "Perfect legal argument."}]
        result = opponent.process_turn(transcript)
        assert result.current_rung <= max_rung, (
            "current_rung must be clamped to the ladder length"
        )

    def test_reply_field_is_non_empty_string(self):
        """The visible reply must always be a non-empty string."""
        opponent = _make_opponent([_bluff_reply_json()])
        transcript = [{"role": "user", "content": "Ping."}]
        result = opponent.process_turn(transcript)
        assert isinstance(result.reply, str)
        assert len(result.reply) > 0

    def test_result_parses_as_OpponentTurnResult(self):
        """OpponentTurnResult must be a valid Pydantic model instance."""
        from crucible.schemas import OpponentTurnResult
        opponent = _make_opponent([_bluff_reply_json()])
        transcript = [{"role": "user", "content": "Test."}]
        result = opponent.process_turn(transcript)
        assert isinstance(result, OpponentTurnResult)


# ---------------------------------------------------------------------------
# Adjudicator + Coach contract tests
# ---------------------------------------------------------------------------

class TestAdjudicatorContract:
    def test_emits_valid_move_event(self):
        from crucible.agents.adjudicator import AdjudicatorAgent
        from crucible.schemas import MoveEvent
        from crucible.scenarios.fixtures.dpa_negotiation import PLAYBOOK

        adj_reply = json.dumps({
            "turn": 1,
            "classification": "good_move",
            "refs": ["sub_processor_obligations"],
            "position_delta": 0.4,
            "note": "User cited Art. 28(2) correctly.",
        })
        client = FakeModelClient(scripted=[adj_reply])
        adj = AdjudicatorAgent(client=client, model="gemini-2.5-flash", playbook=PLAYBOOK)
        transcript = [{"role": "user", "content": "Under Art. 28(2) GDPR..."}]
        event = adj.score_turn(transcript, turn=1)

        assert isinstance(event, MoveEvent)
        assert event.classification in {
            "good_move", "conceded_early", "missed_point",
            "overplayed", "held_firm", "neutral"
        }
        assert -1.0 <= event.position_delta <= 1.0
        assert event.turn == 1
        assert isinstance(event.note, str) and len(event.note) > 0

    def test_unknown_classification_falls_back_to_neutral(self):
        from crucible.agents.adjudicator import AdjudicatorAgent
        from crucible.scenarios.fixtures.dpa_negotiation import PLAYBOOK

        bad_reply = json.dumps({
            "turn": 1,
            "classification": "TOTALLY_INVALID",
            "refs": [],
            "position_delta": 0.0,
            "note": "Something happened.",
        })
        client = FakeModelClient(scripted=[bad_reply])
        adj = AdjudicatorAgent(client=client, model="gemini-2.5-flash", playbook=PLAYBOOK)
        event = adj.score_turn([{"role": "user", "content": "Test"}], turn=1)
        assert event.classification == "neutral"


class TestCoachContract:
    def test_emits_valid_debrief(self):
        from crucible.agents.coach import CoachAgent
        from crucible.schemas import Debrief, MoveEvent
        from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK, PLAYBOOK

        coach_reply = json.dumps({
            "turning_point_explainer": (
                "At turn 2, the trainee conceded the liability cap without securing "
                "sub-processor authorisation. The correct move was to invoke Art. 82 GDPR."
            ),
            "stronger_move": (
                "Invoke Art. 82(3) GDPR: the processor bears liability unless it proves "
                "it is not at fault — any contractual cap conflicts with this statutory floor."
            ),
            "persona_note": (
                "The Aggressor used deadline pressure to rush the liability concession; "
                "slow down and anchor to the statutory baseline before entering numbers."
            ),
        })
        client = FakeModelClient(scripted=[coach_reply])
        coach = CoachAgent(client=client, model="gemini-2.5-pro")

        move_events = [
            MoveEvent(
                turn=1, classification="good_move",
                refs=["sub_processor_obligations"], position_delta=0.3,
                note="Good Art. 28(2) citation."
            ),
            MoveEvent(
                turn=2, classification="conceded_early",
                refs=["liability_cap"], position_delta=-0.8,
                note="Conceded liability cap for no reciprocal value."
            ),
        ]
        debrief = coach.produce_debrief(
            transcript=[],
            move_events=move_events,
            playbook=PLAYBOOK,
            opp_playbook=OPPONENT_PLAYBOOK,
            persona_name="aggressor",
            score=45,
            subscores={"outcome": 15, "must_haves": 10, "concession_discipline": 10,
                       "legal_grounding": 8, "composure": 2},
            turning_point_turn=2,
            score_to_beat=None,
            biggest_concession=move_events[1],
            biggest_miss=None,
            biggest_overplay=None,
            stronger_move_authorities=[],
        )

        assert isinstance(debrief, Debrief)
        assert debrief.score == 45
        assert debrief.turning_point_turn == 2
        assert len(debrief.turning_point_explainer) > 0
        assert len(debrief.stronger_move) > 0
        assert len(debrief.persona_note) > 0


# ---------------------------------------------------------------------------
# Live variant (opt-in, runs only with --live flag and real credentials)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_live_bluff_does_not_concede():
    """Real model: verify resistance holds against a confident-but-weak bluff."""
    from crucible.config import get_settings
    from crucible.agents.base import make_client

    settings = get_settings()
    client = make_client(settings)
    opponent = OpponentAgent(
        client=client,
        model=settings.fast_model,
        matter_summary="GDPR DPA negotiation — FinTech Corp v CloudStack Ltd",
        opp_playbook=OPPONENT_PLAYBOOK,
        persona=AGGRESSOR,
    )
    transcript = [
        {"role": "user", "content": (
            "I am absolutely certain that GDPR requires you to agree to our sub-processor "
            "terms. This is crystal clear. There is no ambiguity. You need to just accept "
            "our position immediately because we are completely right about this."
        )}
    ]
    result = opponent.process_turn(transcript)
    assert result.resistance_check.conceded is False, (
        "Live model: confident bluff with no legal substance must not trigger a concession"
    )
