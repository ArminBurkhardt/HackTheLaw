"""Deterministic scoring tests — no model calls, pure functions.

Crafted MoveEvent lists assert exact subscores, totals, and turning-point
detection. These tests pin the contract of scoring.py.
"""
from __future__ import annotations
import pytest
from crucible.schemas import MoveEvent, Authority
from crucible.scoring import (
    compute_subscores,
    compute_total_score,
    find_biggest,
    find_turning_point,
)
from crucible.scenarios.fixtures.dpa_negotiation import PLAYBOOK

# Shorthand weights for tests (avoid re-loading YAML in every test)
_WEIGHTS = {
    "outcome": 35,
    "must_haves": 25,
    "concession_discipline": 20,
    "legal_grounding": 15,
    "composure": 5,
}

_AUTH = Authority(title="GDPR Art. 28(2)", source="firm_playbook")


def _event(
    turn: int,
    classification: str,
    refs: list[str],
    position_delta: float,
    note: str = "test",
) -> MoveEvent:
    return MoveEvent(
        turn=turn,
        classification=classification,
        refs=refs,
        position_delta=position_delta,
        note=note,
    )


# ---------------------------------------------------------------------------
# compute_subscores
# ---------------------------------------------------------------------------

class TestComputeSubscores:
    def test_empty_events_returns_all_zeros(self):
        scores = compute_subscores([], PLAYBOOK, _WEIGHTS)
        assert all(v == 0 for v in scores.values())
        assert set(scores.keys()) == set(_WEIGHTS.keys())

    def test_perfect_round_max_outcome(self):
        events = [
            _event(1, "good_move", ["sub_processor_obligations"], 1.0),
            _event(2, "good_move", ["liability_cap"], 1.0),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        # mean_delta = 1.0 → outcome should be max weight
        assert scores["outcome"] == _WEIGHTS["outcome"]

    def test_zero_delta_gives_half_outcome(self):
        events = [_event(1, "neutral", [], 0.0)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        # mean_delta=0.0 → (0+1)/2 * 35 = 17 (int)
        assert scores["outcome"] == 17

    def test_all_negative_delta_gives_zero_outcome(self):
        events = [_event(1, "conceded_early", ["liability_cap"], -1.0)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["outcome"] == 0

    def test_must_haves_full_coverage(self):
        # Both must_have items positively touched
        events = [
            _event(1, "good_move", ["sub_processor_obligations"], 0.5),
            _event(2, "good_move", ["liability_cap"], 0.5),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["must_haves"] == _WEIGHTS["must_haves"]

    def test_must_haves_partial_coverage(self):
        # Only one of two must_haves touched
        events = [
            _event(1, "good_move", ["sub_processor_obligations"], 0.5),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        # 1/2 must_haves → int(0.5 * 25) = 12
        assert scores["must_haves"] == 12

    def test_must_haves_not_credited_for_negative_delta(self):
        # Touching a must_have with negative delta does NOT count
        events = [
            _event(1, "conceded_early", ["sub_processor_obligations"], -0.5),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["must_haves"] == 0

    def test_must_haves_not_credited_for_conceded_classification(self):
        # Must use good_move or held_firm classification to earn must_haves credit
        events = [
            _event(1, "conceded_early", ["sub_processor_obligations"], 0.5),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["must_haves"] == 0

    def test_concession_discipline_full_when_no_concessions(self):
        events = [_event(1, "good_move", [], 0.3)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["concession_discipline"] == _WEIGHTS["concession_discipline"]

    def test_concession_discipline_reduced_by_concession(self):
        # One conceded_early with delta -1.0 → penalty = 1.0 * 10 = 10
        events = [_event(1, "conceded_early", ["liability_cap"], -1.0)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["concession_discipline"] == _WEIGHTS["concession_discipline"] - 10

    def test_concession_discipline_floored_at_zero(self):
        # Two large concessions should not go negative
        events = [
            _event(1, "conceded_early", ["liability_cap"], -1.0),
            _event(2, "conceded_early", ["sub_processor_obligations"], -1.0),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["concession_discipline"] == 0

    def test_legal_grounding_credited_for_good_move_with_authorities(self):
        # good_move referencing an item that has authorities
        events = [_event(1, "good_move", ["sub_processor_obligations"], 0.5)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        # sub_processor_obligations has authorities → 1/1 good moves grounded → full score
        assert scores["legal_grounding"] == _WEIGHTS["legal_grounding"]

    def test_legal_grounding_zero_when_no_good_moves(self):
        events = [_event(1, "conceded_early", ["liability_cap"], -0.5)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["legal_grounding"] == 0

    def test_composure_full_when_no_overplayed(self):
        events = [_event(1, "good_move", [], 0.3)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["composure"] == _WEIGHTS["composure"]

    def test_composure_reduced_per_overplayed(self):
        events = [_event(1, "overplayed", [], -0.2)]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["composure"] == _WEIGHTS["composure"] - 2

    def test_composure_floored_at_zero(self):
        events = [
            _event(1, "overplayed", [], -0.2),
            _event(2, "overplayed", [], -0.2),
            _event(3, "overplayed", [], -0.2),
        ]
        scores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        assert scores["composure"] == 0

    def test_total_score_sums_subscores(self):
        events = [_event(1, "good_move", ["sub_processor_obligations"], 0.5)]
        subscores = compute_subscores(events, PLAYBOOK, _WEIGHTS)
        total = compute_total_score(subscores)
        assert total == sum(subscores.values())


# ---------------------------------------------------------------------------
# find_turning_point
# ---------------------------------------------------------------------------

class TestFindTurningPoint:
    def test_empty_events(self):
        turn, event = find_turning_point([], PLAYBOOK)
        assert turn == 0
        assert event is None

    def test_worst_negative_delta_is_turning_point(self):
        events = [
            _event(1, "good_move", [], 0.5),
            _event(2, "conceded_early", ["liability_cap"], -0.9),
            _event(3, "neutral", [], -0.2),
        ]
        turn, event = find_turning_point(events, PLAYBOOK)
        assert turn == 2
        assert event is not None
        assert event.position_delta == -0.9

    def test_fallback_to_highest_weight_miss_when_no_negative(self):
        # All deltas non-negative but there are missed points
        events = [
            _event(1, "good_move", ["breach_notification"], 0.3),
            _event(2, "missed_point", ["liability_cap"], 0.0),   # weight=1.5
            _event(3, "missed_point", ["sub_processor_obligations"], 0.0),  # weight=1.5
        ]
        turn, event = find_turning_point(events, PLAYBOOK)
        # Both have same weight; either is valid — just ensure a miss is picked
        assert event is not None
        assert event.classification in ("missed_point", "conceded_early")

    def test_no_negative_no_misses_returns_lowest_delta_turn(self):
        events = [
            _event(1, "good_move", [], 0.8),
            _event(2, "good_move", [], 0.3),
        ]
        turn, event = find_turning_point(events, PLAYBOOK)
        assert turn == 2  # lowest delta (0.3) turn


# ---------------------------------------------------------------------------
# find_biggest
# ---------------------------------------------------------------------------

class TestFindBiggest:
    def test_returns_none_when_no_match(self):
        events = [_event(1, "good_move", [], 0.5)]
        assert find_biggest("conceded_early", events) is None

    def test_returns_event_with_most_negative_delta(self):
        events = [
            _event(1, "conceded_early", [], -0.3),
            _event(2, "conceded_early", [], -0.8),
            _event(3, "good_move", [], 0.5),
        ]
        result = find_biggest("conceded_early", events)
        assert result is not None
        assert result.position_delta == -0.8

    def test_find_biggest_miss(self):
        events = [
            _event(1, "missed_point", [], 0.0),
            _event(2, "missed_point", [], -0.1),
        ]
        result = find_biggest("missed_point", events)
        assert result is not None
        assert result.turn == 2  # -0.1 < 0.0

    def test_find_biggest_overplay(self):
        events = [_event(1, "overplayed", [], -0.5)]
        result = find_biggest("overplayed", events)
        assert result is not None
        assert result.classification == "overplayed"
