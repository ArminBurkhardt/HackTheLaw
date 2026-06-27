from uuid import uuid4

from app.engine import create_round, end_round, generate_argument_options, play_turn
from app.schemas import (
    ArgumentOptionsResponse,
    CreateRoundRequest,
    Debrief,
    MoveEvent,
    RoundState,
    TurnDeltaEvent,
    TurnFinalEvent,
)


class EngineRunnerFixture:
    runtime_name = "test_engine"

    def __init__(self) -> None:
        self._rounds: dict[str, RoundState] = {}

    def start_round(self, request: CreateRoundRequest) -> RoundState:
        round_id = uuid4().hex
        state = create_round(round_id, request.persona, request.difficulty, request.language).model_copy(
            update={"runtime": self.runtime_name}
        )
        self._rounds[round_id] = state
        return state

    def play_turn(self, round_id: str, text: str) -> tuple[RoundState, MoveEvent]:
        state = self._rounds[round_id]
        next_state, move = play_turn(state, text)
        self._rounds[round_id] = next_state.model_copy(update={"runtime": self.runtime_name})
        return self._rounds[round_id], move

    async def stream_turn(self, round_id: str, text: str):
        state, move = self.play_turn(round_id, text)
        yield TurnDeltaEvent(text=state.messages[-1].text)
        yield TurnFinalEvent(round=state, event=move)

    def end_round(self, round_id: str) -> Debrief:
        return end_round(self._rounds[round_id])

    def argument_options(self, round_id: str) -> ArgumentOptionsResponse:
        return ArgumentOptionsResponse(options=generate_argument_options(self._rounds[round_id]))

    def get_round(self, round_id: str) -> RoundState | None:
        return self._rounds.get(round_id)
