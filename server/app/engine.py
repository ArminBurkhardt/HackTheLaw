from .schemas import Debrief, Difficulty, Message, MoveEvent, MoveKind, Persona, Role, RoundState


PERSONA_OPENERS: dict[Persona, str] = {
    Persona.aggressor: (
        "Thanks for joining. On the DPA, our main concern is keeping audit rights and processor "
        "liability commercially bounded. Tell me what change you need and the legal basis for it."
    ),
    Persona.charmer: (
        "Thanks for making time. I think we both want a practical DPA, so I would rather keep the "
        "audit mechanics simple unless there is a specific GDPR issue you need to solve."
    ),
    Persona.stonewaller: (
        "Let us start with the DPA points. Our template already covers sub-processors and audits, "
        "so I will need a concrete reason before we reopen those clauses."
    ),
    Persona.technician: (
        "Before we edit the DPA, walk me through the exact GDPR hook for each requested change and "
        "what reciprocal concession you are offering."
    ),
}

PRESSURE: dict[Difficulty, int] = {
    Difficulty.junior: 4,
    Difficulty.associate: 7,
    Difficulty.partner: 10,
}


def create_round(round_id: str, persona: Persona, difficulty: Difficulty) -> RoundState:
    return RoundState(
        id=round_id,
        persona=persona,
        difficulty=difficulty,
        score=50,
        turn=0,
        ladder=0,
        messages=[Message(role=Role.opponent, text=PERSONA_OPENERS[persona])],
        events=[],
    )


def play_turn(state: RoundState, text: str) -> tuple[RoundState, MoveEvent]:
    move = evaluate_move(text, state.turn + 1, state.difficulty)
    ladder = min(state.ladder + 1, 2) if move.classification == MoveKind.good_move else state.ladder
    reply = opponent_reply(move, state.persona, ladder)

    next_state = state.model_copy(
        update={
            "turn": state.turn + 1,
            "ladder": ladder,
            "score": clamp_score(state.score + move.points),
            "messages": [
                *state.messages,
                Message(role=Role.user, text=text),
                Message(role=Role.opponent, text=reply),
            ],
            "events": [*state.events, move],
        }
    )
    return next_state, move


def evaluate_move(text: str, turn: int, difficulty: Difficulty) -> MoveEvent:
    user_input = text.lower()
    hard_mode = PRESSURE[difficulty] >= 7
    cites_art_28 = "28" in user_input or "sub-processor" in user_input or "subprocessor" in user_input
    asks_reciprocal = (
        "reciprocal" in user_input or "in exchange" in user_input or "if you" in user_input
    )
    protects_audit = "audit" in user_input or "inspect" in user_input
    rejects_concession = any(
        phrase in user_input
        for phrase in ("cannot accept", "can't accept", "do not accept", "won't accept")
    )
    concedes = not rejects_concession and any(
        phrase in user_input for phrase in ("accept", "fine", "agree to your")
    )
    bluffs = any(
        phrase in user_input for phrase in ("non-negotiable", "trust me", "standard market")
    )
    wrong_citation = "art. 33" in user_input or "article 33" in user_input

    if wrong_citation and "sub" in user_input:
        return event(turn, MoveKind.overplayed, -10, "Art. 33 is breach notification territory.")
    if cites_art_28 and asks_reciprocal and protects_audit:
        return event(turn, MoveKind.good_move, 14, "You tied the ask to GDPR and trade value.")
    if bluffs:
        return event(turn, MoveKind.overplayed, -8, "Confidence without a legal hook does not unlock movement.")
    if concedes and not asks_reciprocal:
        return event(turn, MoveKind.conceded_early, -12, "You gave ground before securing reciprocal value.")
    if cites_art_28 or protects_audit:
        points = 6 if hard_mode else 8
        return event(turn, MoveKind.held_firm, points, "You held a legally relevant line.")
    return event(turn, MoveKind.missed_point, -5, "You missed the audit, sub-processor, or trade leverage.")


def end_round(state: RoundState) -> Debrief:
    worst = min(
        state.events,
        key=lambda move: move.points,
        default=event(0, MoveKind.neutral, 0, "No moves were played."),
    )
    exchange = turning_point_exchange(state, worst.turn)
    return Debrief(
        score=clamp_score(state.score),
        headline="You controlled the negotiation." if state.score >= 75 else "You let pressure shape the frame.",
        turning_point=f"Turn {worst.turn}: {worst.note}",
        turning_point_turn=worst.turn,
        turning_point_exchange=exchange,
        stronger_move=(
            "Anchor on GDPR Art. 28(3), then trade audit cadence only for a defined liability position."
        ),
        next_run_focus="Name the must-have, authority, and reciprocal trade before conceding.",
    )


def turning_point_exchange(state: RoundState, turn: int) -> list[Message]:
    if turn <= 0:
        return []
    start = 1 + ((turn - 1) * 2)
    return state.messages[start : start + 2]


def opponent_reply(move: MoveEvent, persona: Persona, ladder: int) -> str:
    if move.classification == MoveKind.good_move:
        text = (
            "We can accept annual audit evidence plus incident-triggered inspection rights."
            if ladder >= 2
            else "We can discuss a narrower audit cadence, but not open-ended inspection rights."
        )
        return style(persona, text)
    if move.classification == MoveKind.conceded_early:
        return style(persona, "Good. Then we will keep our audit limitation as drafted.")
    if move.classification == MoveKind.overplayed:
        return style(persona, "That does not get you there. Name the clause duty or we stay put.")
    return style(persona, "You have not met the condition for movement. What justifies changing our paper?")


def style(persona: Persona, text: str) -> str:
    if persona == Persona.aggressor:
        return f"{text} Decide whether you have a real point or just a preference."
    if persona == Persona.charmer:
        return f"{text} I am trying to keep this commercially sensible for both sides."
    if persona == Persona.stonewaller:
        return f"{text} Otherwise, no change."
    return f"{text} Please be precise: authority, clause, and concession."


def event(turn: int, classification: MoveKind, points: int, note: str) -> MoveEvent:
    return MoveEvent(turn=turn, classification=classification, points=points, note=note)


def clamp_score(score: int) -> int:
    return max(0, min(100, score))
