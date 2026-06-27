from collections.abc import AsyncIterator
from typing import Protocol

from .adk_runner import GoogleAdkOpponentRunner, RunnerUnavailable
from .schemas import ArgumentOptionsResponse, CreateRoundRequest, Debrief, MoveEvent, RoundState, TurnDeltaEvent, TurnFinalEvent
from .settings import Settings, load_settings


class Runner(Protocol):
    runtime_name: str

    def start_round(self, request: CreateRoundRequest) -> RoundState: ...
    def play_turn(self, round_id: str, text: str) -> tuple[RoundState, MoveEvent]: ...
    def stream_turn(self, round_id: str, text: str) -> AsyncIterator[TurnDeltaEvent | TurnFinalEvent]: ...
    def end_round(self, round_id: str) -> Debrief: ...
    def argument_options(self, round_id: str) -> ArgumentOptionsResponse: ...
    def get_round(self, round_id: str) -> RoundState | None: ...


def make_runner(settings: Settings | None = None) -> Runner:
    active_settings = settings or load_settings()
    if active_settings.runner_backend == "adk":
        return GoogleAdkOpponentRunner(active_settings)
    if active_settings.runner_backend == "local":
        raise RunnerUnavailable(
            "Local deterministic runner has been removed. Set CRUCIBLE_RUNNER=adk with Google credentials."
        )
    raise RunnerUnavailable(f"Unsupported CRUCIBLE_RUNNER: {active_settings.runner_backend}.")
