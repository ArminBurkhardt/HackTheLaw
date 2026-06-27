"""Conservative conversation-abort guard for legal sparring sessions."""
from __future__ import annotations

from pydantic import BaseModel

from crucible.schemas import MoveEvent, Playbook

NEGATIVE_CLASSIFICATIONS = {"conceded_early", "missed_point", "overplayed"}
STALL_CLASSIFICATIONS = {"missed_point", "neutral"}


class AbortDecision(BaseModel):
    should_abort: bool = False
    reason: str | None = None


def evaluate_conversation_abort(playbook: Playbook, move_events: list[MoveEvent]) -> AbortDecision:
    if len(move_events) < 2:
        return AbortDecision()

    trap_ids = {item.id for item in playbook.items if item.kind == "trap"}
    if _repeated_trap_overreach(move_events, trap_ids):
        return AbortDecision(
            should_abort=True,
            reason=(
                "Provider counsel walks away after repeated overreach on a known walk-away issue."
            ),
        )

    total_position = sum(event.position_delta for event in move_events)
    if len(move_events) >= 3 and total_position <= -1.5:
        return AbortDecision(
            should_abort=True,
            reason="Provider counsel ends the negotiation because the trainee has lost the core position.",
        )
    if len(move_events) >= 3 and total_position >= 1.5:
        return AbortDecision(
            should_abort=True,
            reason="The training objective is reached; the trainee has secured enough ground for debrief.",
        )

    last_two = move_events[-2:]
    if (
        all(event.classification in NEGATIVE_CLASSIFICATIONS for event in last_two)
        and sum(event.position_delta for event in last_two) <= -1.0
    ):
        return AbortDecision(
            should_abort=True,
            reason=(
                "Provider counsel ends the negotiation after repeated counterproductive turns."
            ),
        )

    last_three = move_events[-3:]
    if (
        len(last_three) == 3
        and
        all(event.classification in NEGATIVE_CLASSIFICATIONS for event in last_three)
        and sum(event.position_delta for event in last_three) <= -1.2
    ):
        return AbortDecision(
            should_abort=True,
            reason=(
                "Provider counsel ends the negotiation after three consecutive counterproductive turns."
            ),
        )

    if len(move_events) >= 3:
        last_four = move_events[-3:]
        if (
            all(event.classification in STALL_CLASSIFICATIONS for event in last_four)
            and sum(event.position_delta for event in last_four) <= 0
        ):
            return AbortDecision(
                should_abort=True,
                reason=(
                    "Provider counsel ends the negotiation because the discussion has stalled."
                ),
            )

    return AbortDecision()


def _repeated_trap_overreach(move_events: list[MoveEvent], trap_ids: set[str]) -> bool:
    if not trap_ids:
        return False
    recent_trap_overplays = [
        event
        for event in move_events[-3:]
        if event.classification == "overplayed"
        and event.position_delta <= -0.3
        and trap_ids.intersection(event.refs)
    ]
    return len(recent_trap_overplays) >= 2
