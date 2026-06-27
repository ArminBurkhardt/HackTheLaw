"""CrucibleRunner — per-session state + agent orchestration.

Stage 1: full agent pipeline (Opponent + Adjudicator → TurnResult;
         Coach runs at round end → Debrief injected into final TurnResult).
Backwards-compatible: run_turn() still returns a plain str (Stage 0 tests stay green).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from crucible.config import Settings
from crucible.agents.base import ModelClient
from crucible.agents.adjudicator import AdjudicatorAgent
from crucible.agents.coach import CoachAgent
from crucible.agents.opponent import OpponentAgent
from crucible.agents.personas import Persona, get_persona
from crucible.schemas import (
    Debrief, MoveEvent, OpponentPlaybook, Playbook, TurnResult
)
from crucible.scoring import (
    compute_subscores, compute_total_score, find_biggest, find_turning_point
)


@dataclass
class SessionState:
    playbook: Playbook
    opp_playbook: OpponentPlaybook
    persona: Persona
    opponent: OpponentAgent
    adjudicator: AdjudicatorAgent
    coach: CoachAgent
    transcript: list[dict] = field(default_factory=list)
    move_events: list[MoveEvent] = field(default_factory=list)
    current_position: float = 0.0
    score_to_beat: int | None = None
    round_complete: bool = False


class CrucibleRunner:
    def __init__(self, settings: Settings, client: ModelClient) -> None:
        self._settings = settings
        self._client = client
        self._sessions: dict[str, SessionState | list[dict]] = {}

    # ------------------------------------------------------------------
    # Stage 0 backwards-compat: plain run_turn → str
    # ------------------------------------------------------------------

    def run_turn(self, session_id: str, user_msg: str) -> str:
        """Backwards-compatible single-turn call. Returns only the reply string."""
        result = self._run_full(session_id, user_msg)
        if isinstance(result, str):
            return result
        return result.reply

    # ------------------------------------------------------------------
    # Stage 1: full-pipeline turn
    # ------------------------------------------------------------------

    def start_session(
        self,
        session_id: str,
        playbook: Playbook,
        opp_playbook: OpponentPlaybook,
        persona_name: str = "aggressor",
        score_to_beat: int | None = None,
    ) -> None:
        persona = get_persona(persona_name)
        opponent = OpponentAgent(
            client=self._client,
            model=self._settings.fast_model,
            matter_summary=playbook.matter_summary,
            opp_playbook=opp_playbook,
            persona=persona,
        )
        adjudicator = AdjudicatorAgent(
            client=self._client,
            model=self._settings.fast_model,
            playbook=playbook,
        )
        coach = CoachAgent(
            client=self._client,
            model=self._settings.reasoning_model,
        )
        self._sessions[session_id] = SessionState(
            playbook=playbook,
            opp_playbook=opp_playbook,
            persona=persona,
            opponent=opponent,
            adjudicator=adjudicator,
            coach=coach,
            score_to_beat=score_to_beat,
        )

    def run_turn_full(self, session_id: str, user_msg: str) -> TurnResult:
        """Full pipeline: Opponent + Adjudicator → TurnResult (Debrief if round ends)."""
        session = self._sessions.get(session_id)
        if not isinstance(session, SessionState):
            raise ValueError(
                f"Session {session_id!r} not initialised. Call start_session() first."
            )
        if session.round_complete:
            raise ValueError(f"Session {session_id!r} is already complete.")

        turn_number = len(session.move_events) + 1

        # 1. Append user message to transcript
        session.transcript.append({"role": "user", "content": user_msg})

        # 2. Opponent responds
        opp_result = session.opponent.process_turn(session.transcript)
        session.transcript.append({"role": "assistant", "content": opp_result.reply})

        # 3. Adjudicator scores the user's turn (runs on transcript up to opponent reply)
        move_event = session.adjudicator.score_turn(session.transcript, turn=turn_number)
        session.move_events.append(move_event)
        session.current_position += move_event.position_delta

        return TurnResult(
            reply=opp_result.reply,
            move_event=move_event,
            current_position=session.current_position,
            round_complete=False,
        )

    def end_round(self, session_id: str) -> TurnResult:
        """Trigger round end: run the Coach and produce a Debrief."""
        session = self._sessions.get(session_id)
        if not isinstance(session, SessionState):
            raise ValueError(f"Session {session_id!r} not found.")
        if session.round_complete:
            raise ValueError(f"Session {session_id!r} already ended.")

        session.round_complete = True

        subscores = compute_subscores(session.move_events, session.playbook)
        score = compute_total_score(subscores)
        tp_turn, _tp_event = find_turning_point(session.move_events, session.playbook)
        biggest_concession = find_biggest("conceded_early", session.move_events)
        biggest_miss = find_biggest("missed_point", session.move_events)
        biggest_overplay = find_biggest("overplayed", session.move_events)

        # Stronger move authorities come from the turning-point item's playbook entry
        stronger_auths: list = []
        if _tp_event and _tp_event.refs:
            item_map = {item.id: item for item in session.playbook.items}
            for ref in _tp_event.refs:
                if ref in item_map:
                    stronger_auths.extend(item_map[ref].authorities)

        debrief: Debrief = session.coach.produce_debrief(
            transcript=session.transcript,
            move_events=session.move_events,
            playbook=session.playbook,
            opp_playbook=session.opp_playbook,
            persona_name=session.persona.name,
            score=score,
            subscores=subscores,
            turning_point_turn=tp_turn,
            score_to_beat=session.score_to_beat,
            biggest_concession=biggest_concession,
            biggest_miss=biggest_miss,
            biggest_overplay=biggest_overplay,
            stronger_move_authorities=stronger_auths,
        )

        return TurnResult(
            reply="",
            move_event=MoveEvent(
                turn=0, classification="neutral", refs=[],
                position_delta=0.0, note="round ended"
            ),
            current_position=session.current_position,
            round_complete=True,
            debrief=debrief,
        )

    # ------------------------------------------------------------------
    # Internal: legacy path for Stage 0 sessions (raw list[dict])
    # ------------------------------------------------------------------

    _SYSTEM_STUB = "You are a legal opponent in an adversarial training scenario."

    def _run_full(self, session_id: str, user_msg: str) -> TurnResult | str:
        session = self._sessions.get(session_id)

        # Stage 1 session
        if isinstance(session, SessionState):
            return self.run_turn_full(session_id, user_msg)

        # Legacy Stage 0 plain session
        if session is None:
            self._sessions[session_id] = []
        history: list[dict] = self._sessions[session_id]  # type: ignore[assignment]
        history.append({"role": "user", "content": user_msg})
        reply = self._client.generate(
            model=self._settings.fast_model,
            system=self._SYSTEM_STUB,
            messages=list(history),
        )
        history.append({"role": "assistant", "content": reply})
        return reply


def make_runner(settings: Settings, client: ModelClient) -> CrucibleRunner:
    return CrucibleRunner(settings, client)
