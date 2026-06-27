"""Contract tests for the grounded RL estimators (crucible/rl.py).

Pure-math, deterministic. We test the *properties* the addendum guarantees
(monotonicity, bounds, turning-point = max-regret, ECE behaviour, posterior
shrinkage, ZPD direction) — never exact prose.
"""
from __future__ import annotations
import math
import pytest

from crucible.rl import (
    calibration_from_citations,
    compute_rl_insights,
    expected_calibration_error,
    fisher_information,
    recommend_difficulty,
    regret_trajectory,
    sigmoid,
    skill_scalar,
    update_skill,
    update_skill_vector,
    value_function,
    win_prob_trajectory,
)
from crucible.schemas import Authority, CitationCheck, MoveEvent


def _move(turn: int, delta: float, classification: str = "neutral") -> MoveEvent:
    return MoveEvent(
        turn=turn, classification=classification, refs=[],
        position_delta=delta, note="t",
    )


# ---------------------------------------------------------------------------
# Absorbing-Markov value function
# ---------------------------------------------------------------------------

def test_value_function_is_bounded_and_monotonic():
    vals = [value_function(p) for p in range(-5, 6)]
    assert all(0.0 <= v <= 1.0 for v in vals)
    # V must be non-decreasing in position (more ground held → higher win prob).
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))


def test_value_function_barriers():
    assert value_function(-5) == pytest.approx(0.0, abs=1e-9)
    assert value_function(5) == pytest.approx(1.0, abs=1e-9)
    assert value_function(0) == pytest.approx(0.5, abs=0.05)  # symmetric prior ≈ even


def test_value_function_reflects_momentum():
    """A round of concessions should value the same standing lower than a round of gains."""
    losing = [_move(i, -0.5) for i in range(1, 5)]
    winning = [_move(i, 0.5) for i in range(1, 5)]
    assert value_function(0.0, losing) < value_function(0.0, winning)


# ---------------------------------------------------------------------------
# Trajectory + counterfactual regret → turning point
# ---------------------------------------------------------------------------

def test_win_prob_trajectory_tracks_position():
    events = [_move(1, 1.0), _move(2, 1.0), _move(3, -2.0)]
    traj = win_prob_trajectory(events)
    assert len(traj) == 3
    assert traj[1] > traj[0]      # climbed
    assert traj[2] < traj[1]      # then dropped


def test_turning_point_is_max_regret_turn():
    # Turn 3 destroys the most ground → must be the turning point.
    events = [_move(1, 0.4), _move(2, 0.2), _move(3, -1.6), _move(4, 0.1)]
    regrets, tp = regret_trajectory(events)
    assert tp == 3
    assert regrets[2] == max(regrets)
    assert all(r >= 0.0 for r in regrets)


def test_regret_empty():
    assert regret_trajectory([]) == ([], 0)


# ---------------------------------------------------------------------------
# Expected Calibration Error
# ---------------------------------------------------------------------------

def test_ece_none_without_pairs():
    assert expected_calibration_error([], []) is None


def test_ece_zero_when_perfectly_calibrated():
    # Confident-and-correct, unsure-and-wrong → ECE ≈ 0.
    ece = expected_calibration_error([1.0, 1.0, 0.0], [1.0, 1.0, 0.0])
    assert ece == pytest.approx(0.0, abs=1e-9)


def test_ece_large_when_overconfident():
    # High confidence, zero correctness → maximal miscalibration.
    ece = expected_calibration_error([1.0, 1.0], [0.0, 0.0])
    assert ece == pytest.approx(1.0, abs=1e-9)


def test_calibration_from_citations_flags_overplay():
    cited = [
        Authority(title="A", source="cellar", check=CitationCheck(
            status="misattributed", support="neutral", semantic_entropy=0.1,
            confidence=0.9, citation_score=0.2, n_clusters=1, samples=5, note="x")),
    ]
    ece, note = calibration_from_citations(cited)
    assert ece is not None and ece > 0.3
    assert "verweg" not in note  # sanity: it's a real sentence
    assert isinstance(note, str) and note


def test_calibration_none_without_checks():
    ece, note = calibration_from_citations([Authority(title="A", source="cellar")])
    assert ece is None
    assert note


# ---------------------------------------------------------------------------
# IRT skill posterior
# ---------------------------------------------------------------------------

def test_update_skill_shrinks_variance_and_moves_toward_observation():
    m0, v0 = 0.0, 4.0
    m1, v1 = update_skill(m0, v0, observed_p=0.9)
    assert v1 < v0                 # posterior is more certain
    assert m1 > m0                 # strong round pushes skill up


def test_update_skill_vector_reports_dimensions():
    subs = {"outcome": 30, "legal_grounding": 5}
    weights = {"outcome": 35, "legal_grounding": 15, "composure": 5}
    mean, var, dims = update_skill_vector(subs, weights, {}, {})
    labels = {d.label for d in dims}
    assert "Outcome" in labels and "Legal grounding" in labels
    assert all(0.0 <= d.theta <= 1.0 for d in dims)
    # outcome (30/35) should land higher than legal_grounding (5/15)
    by_label = {d.label: d.theta for d in dims}
    assert by_label["Outcome"] > by_label["Legal grounding"]


def test_fisher_information_peaks_at_match():
    assert fisher_information(0.0, b=0.0) > fisher_information(3.0, b=0.0)


# ---------------------------------------------------------------------------
# ZPD matchmaking
# ---------------------------------------------------------------------------

def test_recommend_difficulty_direction_and_clamp():
    up, _ = recommend_difficulty(0.95)
    down, _ = recommend_difficulty(0.10)
    assert up > 0 and down < 0
    assert -0.3 <= up <= 0.3 and -0.3 <= down <= 0.3


def test_skill_scalar_bounds():
    assert skill_scalar({}) == 0.5
    assert 0.0 <= skill_scalar({"a": 2.0, "b": -2.0}) <= 1.0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def test_compute_rl_insights_end_to_end():
    events = [_move(1, 0.5, "good_move"), _move(2, -1.5, "conceded_early"), _move(3, 0.2)]
    subs = {"outcome": 20, "must_haves": 10, "concession_discipline": 8,
            "legal_grounding": 9, "composure": 4}
    weights = {"outcome": 35, "must_haves": 25, "concession_discipline": 20,
               "legal_grounding": 15, "composure": 5}
    insights, mean, var = compute_rl_insights(events, subs, weights, user_citations=[])
    assert len(insights.win_prob_trajectory) == 3
    assert insights.max_regret_turn == 2          # the early concession
    assert insights.calibration_error is None     # no citations
    assert len(insights.skill) == 5
    assert set(mean) and set(var)
    assert -0.3 <= insights.recommended_aggression_delta <= 0.3
