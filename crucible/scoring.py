"""Deterministic scoring module — no model calls, pure functions.

Computes subscores from MoveEvents against the negotiation rubric.
All logic here is exhaustively unit-tested; it is the contract the tests enforce.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from crucible.schemas import MoveEvent, Playbook


def _load_weights(scenario: str = "negotiation") -> dict[str, int]:
    path = Path(__file__).parent / "scenarios" / f"{scenario}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in data["rubric_weights"].items()}


def compute_subscores(
    move_events: list[MoveEvent],
    playbook: Playbook,
    weights: dict[str, int] | None = None,
) -> dict[str, int]:
    if weights is None:
        weights = _load_weights()

    n = len(move_events)
    if n == 0:
        return {k: 0 for k in weights}

    item_map = {item.id: item for item in playbook.items}

    # --- Outcome (0 → weights["outcome"]) ---
    # Mean position_delta in [-1, 1], mapped to [0, weight]
    mean_delta = sum(e.position_delta for e in move_events) / n
    outcome = int(max(0.0, min(1.0, (mean_delta + 1.0) / 2.0)) * weights["outcome"])

    # --- Must-haves (0 → weights["must_haves"]) ---
    # Fraction of must_have items that were positively secured
    must_have_ids = {item.id for item in playbook.items if item.kind == "must_have"}
    positively_touched: set[str] = set()
    for e in move_events:
        if e.position_delta > 0 and e.classification in ("good_move", "held_firm"):
            for ref in e.refs:
                if ref in must_have_ids:
                    positively_touched.add(ref)
    must_haves_frac = len(positively_touched) / max(1, len(must_have_ids))
    must_haves = int(must_haves_frac * weights["must_haves"])

    # --- Concession discipline (0 → weights["concession_discipline"]) ---
    # Start full; subtract for each conceded_early event weighted by delta magnitude
    concession_penalty = sum(
        abs(e.position_delta) * 10.0
        for e in move_events
        if e.classification == "conceded_early"
    )
    concession_discipline = max(0, int(weights["concession_discipline"] - concession_penalty))

    # --- Legal grounding (0 → weights["legal_grounding"]) ---
    # Among good/held moves, fraction that reference items with non-empty authorities
    good_or_held = [e for e in move_events if e.classification in ("good_move", "held_firm")]
    if good_or_held:
        grounded = sum(
            1 for e in good_or_held
            if any(
                item_map.get(ref) is not None and bool(item_map[ref].authorities)
                for ref in e.refs
            )
        )
        legal_grounding = int(grounded / len(good_or_held) * weights["legal_grounding"])
    else:
        legal_grounding = 0

    # --- Composure (0 → weights["composure"]) ---
    overplayed_count = sum(1 for e in move_events if e.classification == "overplayed")
    composure = max(0, weights["composure"] - overplayed_count * 2)

    return {
        "outcome": outcome,
        "must_haves": must_haves,
        "concession_discipline": concession_discipline,
        "legal_grounding": legal_grounding,
        "composure": composure,
    }


def compute_total_score(subscores: dict[str, int]) -> int:
    return sum(subscores.values())


def find_turning_point(
    move_events: list[MoveEvent],
    playbook: Playbook,
) -> tuple[int, MoveEvent | None]:
    """Return (turn_number, event) of the critical turning-point turn.

    Primary: the turn with the most negative position_delta.
    Fallback (no negative delta): highest-weight missed opportunity.
    Returns (0, None) if there are no events.
    """
    if not move_events:
        return (0, None)

    item_map = {item.id: item for item in playbook.items}

    worst = min(move_events, key=lambda e: e.position_delta)
    if worst.position_delta < 0:
        return (worst.turn, worst)

    # No negative delta — find highest-weight missed opportunity
    misses = [
        e for e in move_events
        if e.classification in ("missed_point", "conceded_early")
    ]
    if not misses:
        # Everything went well; return the lowest-delta turn as a formality
        return (worst.turn, worst)

    def miss_weight(e: MoveEvent) -> float:
        return max(
            (item_map[ref].weight for ref in e.refs if ref in item_map),
            default=0.0,
        )

    best_miss = max(misses, key=miss_weight)
    return (best_miss.turn, best_miss)


def find_biggest(
    classification: str,
    move_events: list[MoveEvent],
) -> MoveEvent | None:
    """Return the worst event of a given classification by |position_delta|, or None."""
    candidates = [e for e in move_events if e.classification == classification]
    if not candidates:
        return None
    return min(candidates, key=lambda e: e.position_delta)
