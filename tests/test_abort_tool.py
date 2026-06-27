"""Conversation abort guard tests."""
from __future__ import annotations

from crucible.agents.abort import evaluate_conversation_abort
from crucible.schemas import MoveEvent
from crucible.scenarios.fixtures.saas_license_negotiation import PLAYBOOK


def _event(turn: int, classification: str, refs: list[str], delta: float) -> MoveEvent:
    return MoveEvent(
        turn=turn,
        classification=classification,
        refs=refs,
        position_delta=delta,
        note="test",
    )


def test_does_not_abort_after_one_bad_turn():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [_event(1, "overplayed", ["overreach_trap"], -0.6)],
    )

    assert decision.should_abort is False


def test_aborts_after_repeated_trap_overreach():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [
            _event(1, "overplayed", ["overreach_trap"], -0.4),
            _event(2, "overplayed", ["overreach_trap"], -0.4),
        ],
    )

    assert decision.should_abort is True
    assert decision.reason is not None


def test_aborts_after_two_strong_negative_turns():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [
            _event(1, "overplayed", ["overreach_trap"], -0.5),
            _event(2, "missed_point", [], -0.5),
        ],
    )

    assert decision.should_abort is True


def test_aborts_after_three_counterproductive_turns():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [
            _event(1, "missed_point", [], -0.4),
            _event(2, "conceded_early", ["liability_cap_anchor"], -0.4),
            _event(3, "overplayed", ["overreach_trap"], -0.5),
        ],
    )

    assert decision.should_abort is True


def test_aborts_after_three_stalled_turns():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [
            _event(1, "neutral", [], 0.0),
            _event(2, "missed_point", [], 0.0),
            _event(3, "neutral", [], 0.0),
        ],
    )

    assert decision.should_abort is True


def test_aborts_when_training_objective_is_reached():
    decision = evaluate_conversation_abort(
        PLAYBOOK,
        [
            _event(1, "good_move", ["liability_cap_anchor"], 0.6),
            _event(2, "held_firm", ["mandatory_exceptions"], 0.6),
            _event(3, "good_move", ["trade_offs"], 0.6),
        ],
    )

    assert decision.should_abort is True
