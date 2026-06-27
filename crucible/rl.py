"""Mathematically-grounded estimators — the RL backbone (THEORY_ADDENDUM.md).

Pure, deterministic, side-effect-free functions. No model calls, no I/O.
Everything here is exhaustively unit-tested; it is the contract the tests enforce.

What lives here (and where it lands in the product):
  - Absorbing-Markov value function V(s) = P(good outcome | current standing),
    computed via the fundamental matrix N = (I − Q)⁻¹.  → win-probability readout.
  - Per-turn advantage A = V(after) − V(before) and counterfactual regret;
    the turn of maximal regret IS the turning point (CFR, not a heuristic).
  - Expected Calibration Error (ECE) between asserted confidence and SECV-verified
    correctness — "overplaying a weak hand", quantified.
  - IRT skill posterior θ (Bayesian update per rubric dimension) + ZPD matchmaking
    that holds the win-rate in the zone of proximal development (~0.78).

The heavy "opt-in sophistication" (full MaxEnt IRL) is intentionally not here; this
is the highest-ROI subset the addendum calls out to ship first.
"""
from __future__ import annotations
import math
from collections.abc import Sequence

from crucible.schemas import MoveEvent, RLInsights, SkillDimension

# Rubric dimension → display label and its max points (mirrors scoring weights).
# Kept here so θ is reported per the same axes the user already sees.
_SKILL_LABELS: dict[str, str] = {
    "outcome": "Outcome",
    "must_haves": "Must-haves",
    "concession_discipline": "Concession discipline",
    "legal_grounding": "Legal grounding",
    "composure": "Composure",
}

# SECV status → correctness in [0,1] for calibration scoring.
_CORRECTNESS: dict[str, float] = {
    "verified": 1.0,
    "weak": 0.5,
    "misattributed": 0.0,
    "fabricated_identifier": 0.0,
    "not_in_force": 0.0,
}

_TARGET_SUCCESS = 0.78  # centre of the zone of proximal development (0.7–0.85)


# ---------------------------------------------------------------------------
# Small numeric helpers (kept dependency-free — no numpy)
# ---------------------------------------------------------------------------

def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def logit(p: float, eps: float = 1e-3) -> float:
    p = min(1.0 - eps, max(eps, p))
    return math.log(p / (1.0 - p))


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve the dense linear system a·x = b by Gaussian elimination.

    Used to invert (I − Q) for the absorbing-Markov value function. The transient
    state space is tiny (≤ 2K−1 ≈ 9), so a pure-Python solve is exact and instant.
    """
    n = len(b)
    # Work on an augmented copy.
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        # Partial pivot for numerical stability.
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            continue  # singular column — leave as-is (degenerate chain)
        m[col], m[pivot] = m[pivot], m[col]
        piv = m[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col] / piv
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                m[r][c] -= factor * m[col][c]
    return [m[i][n] / m[i][i] if abs(m[i][i]) > 1e-12 else 0.0 for i in range(n)]


# ---------------------------------------------------------------------------
# Absorbing-Markov value function  V(s) = P(good outcome | state)
# ---------------------------------------------------------------------------

def _momentum(move_events: Sequence[MoveEvent], move_prob: float) -> tuple[float, float]:
    """Estimate up/down step probabilities from the round's revealed dynamics.

    Counts how often the trainee gained vs. lost ground (Laplace-smoothed), then
    splits a fixed 'moving' mass; the remainder is the probability of holding.
    A trainee who keeps conceding gets q > p, which pulls every V(s) down.
    """
    pos = sum(1 for e in move_events if e.position_delta > 0.05)
    neg = sum(1 for e in move_events if e.position_delta < -0.05)
    p_up = (pos + 1) / (pos + neg + 2)  # Bayesian shrink toward 0.5
    return move_prob * p_up, move_prob * (1.0 - p_up)


def value_function(
    position: float,
    move_events: Sequence[MoveEvent] = (),
    k: int = 5,
    move_prob: float = 0.7,
) -> float:
    """V(position) ∈ [0,1] — absorption probability into the 'good outcome' barrier.

    The episode is an absorbing Markov chain on integer standings −k..+k with
    absorbing barriers at the ends (deal-on-your-terms at +k, walk-away at −k).
    V is the fundamental-matrix solution B = N·R for the transient states; the
    value at a fractional `position` is linearly interpolated between buckets.
    """
    p_up, p_down = _momentum(move_events, move_prob)
    n_states = 2 * k + 1                     # states indexed 0..2k  (0 = −k, 2k = +k)
    transient = list(range(1, n_states - 1)) # interior states are transient
    idx = {s: i for i, s in enumerate(transient)}
    size = len(transient)

    # Build (I − Q) and R (absorption into the WIN barrier at state 2k).
    a = [[0.0] * size for _ in range(size)]
    r = [0.0] * size
    for s in transient:
        i = idx[s]
        a[i][i] = 1.0
        stay = 1.0 - p_up - p_down
        a[i][i] -= stay  # self-loop contributes to (I − Q)
        # up neighbour
        if s + 1 == n_states - 1:
            r[i] += p_up           # absorbed into WIN
        else:
            a[i][idx[s + 1]] -= p_up
        # down neighbour
        if s - 1 == 0:
            pass                   # absorbed into LOSS → contributes 0 to WIN
        else:
            a[i][idx[s - 1]] -= p_down

    win_prob = _solve(a, r)
    value_by_state = {0: 0.0, n_states - 1: 1.0}
    for s in transient:
        value_by_state[s] = max(0.0, min(1.0, win_prob[idx[s]]))

    # Map continuous position (−k..+k) → state coord (0..2k) and interpolate.
    coord = max(0.0, min(float(n_states - 1), position + k))
    lo = int(math.floor(coord))
    hi = min(lo + 1, n_states - 1)
    frac = coord - lo
    return value_by_state[lo] * (1 - frac) + value_by_state[hi] * frac


def win_prob_trajectory(
    move_events: Sequence[MoveEvent], k: int = 5
) -> list[float]:
    """V(s) after each turn — the win-probability curve over the round."""
    running = 0.0
    traj: list[float] = []
    for e in move_events:
        running += e.position_delta
        traj.append(round(value_function(running, move_events, k=k), 4))
    return traj


def regret_trajectory(
    move_events: Sequence[MoveEvent], k: int = 5
) -> tuple[list[float], int]:
    """Counterfactual regret per turn + the 1-based turn of maximal regret.

    Regret_t = max(0, V(before) − V(after)): the win-probability the move
    destroyed relative to simply holding ground. The argmax is the turning point.
    """
    regrets: list[float] = []
    running = 0.0
    for e in move_events:
        before = value_function(running, move_events, k=k)
        running += e.position_delta
        after = value_function(running, move_events, k=k)
        regrets.append(round(max(0.0, before - after), 4))
    if not regrets:
        return [], 0
    max_turn = max(range(len(regrets)), key=lambda i: regrets[i]) + 1
    return regrets, max_turn


# ---------------------------------------------------------------------------
# Expected Calibration Error — confidence vs. SECV-verified correctness
# ---------------------------------------------------------------------------

def expected_calibration_error(
    confidences: Sequence[float],
    correctness: Sequence[float],
    n_bins: int = 5,
) -> float | None:
    """ECE over (confidence, correctness) pairs. None if there are no pairs.

    The judgment-heavy rubric item, operationalised: a large gap means the trainee
    asserted authorities more (or less) firmly than the ground actually supports.
    """
    pairs = list(zip(confidences, correctness))
    if not pairs:
        return None
    n = len(pairs)
    total = 0.0
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        bucket = [
            (c, y) for c, y in pairs
            if (lo <= c < hi) or (b == n_bins - 1 and c == 1.0)
        ]
        if not bucket:
            continue
        avg_conf = sum(c for c, _ in bucket) / len(bucket)
        avg_acc = sum(y for _, y in bucket) / len(bucket)
        total += (len(bucket) / n) * abs(avg_conf - avg_acc)
    return round(total, 4)


def calibration_from_citations(citations: Sequence) -> tuple[float | None, str]:
    """Compute ECE + a coaching note from SECV-checked Authority objects."""
    confs: list[float] = []
    corr: list[float] = []
    for auth in citations:
        check = getattr(auth, "check", None)
        if check is None:
            continue
        confs.append(float(check.confidence))
        corr.append(_CORRECTNESS.get(check.status, 0.0))
    ece = expected_calibration_error(confs, corr)
    if ece is None:
        return None, "No citations to calibrate this round — ground your assertions to get a read."
    verified = sum(1 for y in corr if y >= 1.0)
    gap = (sum(confs) / len(confs)) - (sum(corr) / len(corr))
    if ece < 0.12:
        note = f"Well-calibrated — {verified}/{len(corr)} citations held up and you claimed them at the right strength."
    elif gap > 0:
        note = f"Overplayed a weak hand — you asserted authorities harder than the ground supports ({verified}/{len(corr)} verified)."
    else:
        note = f"Under-claimed — your citations were stronger than you pressed them ({verified}/{len(corr)} verified)."
    return ece, note


# ---------------------------------------------------------------------------
# IRT skill posterior θ  (Bayesian update per rubric dimension)
# ---------------------------------------------------------------------------

def update_skill(
    prior_mean: float,
    prior_var: float,
    observed_p: float,
    obs_var: float = 1.0,
) -> tuple[float, float]:
    """One Gaussian (Kalman) step of the latent-skill posterior in logit space.

    Observation = this round's normalised subscore, read as a noisy sample of
    σ(θ). Returns (posterior_mean, posterior_var); variance shrinks each round,
    which is exactly the IRT "we now know your skill more precisely" signal.
    """
    y = logit(observed_p)
    gain = prior_var / (prior_var + obs_var)
    mean = prior_mean + gain * (y - prior_mean)
    var = (1.0 - gain) * prior_var
    return mean, max(var, 1e-3)


def fisher_information(theta: float, b: float = 0.0, a: float = 1.0) -> float:
    """Fisher information I(θ) = a²·P·(1−P) for next-item selection (CAT)."""
    p = sigmoid(a * (theta - b))
    return a * a * p * (1.0 - p)


def update_skill_vector(
    subscores: dict[str, int],
    weights: dict[str, int],
    prior_mean: dict[str, float],
    prior_var: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], list[SkillDimension]]:
    """Update θ for every rubric dimension; return new posteriors + a UI view."""
    new_mean: dict[str, float] = dict(prior_mean)
    new_var: dict[str, float] = dict(prior_var)
    dims: list[SkillDimension] = []
    for key, label in _SKILL_LABELS.items():
        if key not in subscores or key not in weights or weights[key] <= 0:
            continue
        p_obs = subscores[key] / weights[key]
        m0 = prior_mean.get(key, 0.0)
        v0 = prior_var.get(key, 4.0)  # diffuse prior on the first round
        m1, v1 = update_skill(m0, v0, p_obs)
        new_mean[key] = round(m1, 4)
        new_var[key] = round(v1, 4)
        dims.append(SkillDimension(
            label=label,
            theta=round(sigmoid(m1), 4),
            delta=round(sigmoid(m1) - sigmoid(m0), 4),
            uncertainty=round(math.sqrt(v1), 4),
        ))
    return new_mean, new_var, dims


def skill_scalar(mean: dict[str, float]) -> float:
    """Aggregate mastery ∈ [0,1] — mean of σ(θ_d) across dimensions."""
    if not mean:
        return 0.5
    return sum(sigmoid(v) for v in mean.values()) / len(mean)


def recommend_difficulty(
    skill: float, target: float = _TARGET_SUCCESS
) -> tuple[float, str]:
    """ZPD matchmaking: pick next-round pressure to hold win-rate near `target`.

    The stronger the trainee, the harder the opponent must press to keep success
    in the zone of proximal development. Returns (aggression_delta, note).
    """
    delta = max(-0.3, min(0.3, (skill - 0.5) * 0.6))
    if delta > 0.05:
        note = (f"You're ahead of the curve (mastery {skill:.0%}); next opponent presses "
                f"~{delta:+.2f} harder to keep your win-rate near the {target:.0%} learning sweet-spot.")
    elif delta < -0.05:
        note = (f"Consolidating (mastery {skill:.0%}); next opponent eases ~{delta:+.2f} so you can "
                f"rebuild before the difficulty climbs again.")
    else:
        note = f"Dialled into your zone of proximal development (mastery {skill:.0%}, target win-rate {target:.0%})."
    return round(delta, 4), note


# ---------------------------------------------------------------------------
# Orchestrator — assembles the RLInsights bundle the runner attaches to Debrief
# ---------------------------------------------------------------------------

def compute_rl_insights(
    move_events: Sequence[MoveEvent],
    subscores: dict[str, int],
    weights: dict[str, int],
    user_citations: Sequence,
    prior_mean: dict[str, float] | None = None,
    prior_var: dict[str, float] | None = None,
    k: int = 5,
) -> tuple[RLInsights, dict[str, float], dict[str, float]]:
    """Bundle every grounded estimator for one finished round.

    Returns (insights, posterior_mean, posterior_var) so the caller can persist
    the updated skill posterior to the UserProfile.
    """
    traj = win_prob_trajectory(move_events, k=k)
    regrets, max_regret_turn = regret_trajectory(move_events, k=k)
    ece, cal_note = calibration_from_citations(user_citations)

    new_mean, new_var, dims = update_skill_vector(
        subscores, weights, prior_mean or {}, prior_var or {}
    )
    skill = skill_scalar(new_mean)
    agg_delta, zpd_note = recommend_difficulty(skill)

    insights = RLInsights(
        win_prob_trajectory=traj,
        regret_by_turn=regrets,
        max_regret_turn=max_regret_turn,
        final_win_prob=traj[-1] if traj else 0.5,
        calibration_error=ece,
        calibration_note=cal_note,
        skill=dims,
        skill_scalar=round(skill, 4),
        target_success=_TARGET_SUCCESS,
        recommended_aggression_delta=agg_delta,
        zpd_note=zpd_note,
    )
    return insights, new_mean, new_var
