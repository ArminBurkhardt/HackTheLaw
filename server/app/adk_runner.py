import asyncio
from dataclasses import dataclass
from importlib import import_module
from typing import Callable
from uuid import uuid4

from .engine import create_round, end_round, play_turn
from .schemas import CreateRoundRequest, Debrief, Message, MoveEvent, Role, RoundState
from .settings import Settings


APP_NAME = "crucible-negotiation"
USER_ID = "crucible-user"

OPPONENT_INSTRUCTION = """
You are opposing counsel in a GDPR DPA negotiation training round.
Stay in character, resist weak legal reasoning, and concede only when the user
names concrete authority plus reciprocal value. Reply as opposing counsel only.
""".strip()


class RunnerUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AdkModules:
    agent: type
    runner: type
    session_service: type
    content: type
    part: type


def load_adk_modules(importer: Callable[[str], object] = import_module) -> AdkModules:
    try:
        agents = importer("google.adk.agents")
        runners = importer("google.adk.runners")
        sessions = importer("google.adk.sessions")
        genai_types = importer("google.genai.types")
    except ModuleNotFoundError as error:
        raise RunnerUnavailable(
            "Google ADK is not installed. Install server/requirements-adk.txt for CRUCIBLE_RUNNER=adk."
        ) from error

    return AdkModules(
        agent=getattr(agents, "Agent"),
        runner=getattr(runners, "Runner"),
        session_service=getattr(sessions, "InMemorySessionService"),
        content=getattr(genai_types, "Content"),
        part=getattr(genai_types, "Part"),
    )


class GoogleAdkOpponentRunner:
    runtime_name = "google_adk"

    def __init__(self, settings: Settings) -> None:
        if not settings.adk_model:
            raise RunnerUnavailable("CRUCIBLE_ADK_MODEL must be set when CRUCIBLE_RUNNER=adk.")
        if not settings.google_configured:
            raise RunnerUnavailable(
                "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT/GOOGLE_CLOUD_LOCATION must be set for CRUCIBLE_RUNNER=adk."
            )

        modules = load_adk_modules()
        self._settings = settings
        self._rounds: dict[str, RoundState] = {}
        self._modules = modules
        self._session_service = modules.session_service()
        self._agent = modules.agent(
            name="crucible_opponent",
            model=settings.adk_model,
            instruction=OPPONENT_INSTRUCTION,
        )
        self._runner = modules.runner(
            agent=self._agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )

    def start_round(self, request: CreateRoundRequest) -> RoundState:
        round_id = uuid4().hex
        state = create_round(round_id, request.persona, request.difficulty).model_copy(
            update={"runtime": self.runtime_name}
        )
        self._rounds[round_id] = state
        asyncio.run(self._session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=round_id,
        ))
        return state

    def play_turn(self, round_id: str, text: str) -> tuple[RoundState, MoveEvent]:
        state = self._rounds[round_id]
        scored_state, move = play_turn(state, text)
        reply = asyncio.run(self._opponent_reply(scored_state, move, text))
        messages = [*scored_state.messages[:-1], Message(role=Role.opponent, text=reply)]
        next_state = scored_state.model_copy(
            update={"messages": messages, "runtime": self.runtime_name}
        )
        self._rounds[round_id] = next_state
        return next_state, move

    def end_round(self, round_id: str) -> Debrief:
        return end_round(self._rounds[round_id])

    def get_round(self, round_id: str) -> RoundState | None:
        return self._rounds.get(round_id)

    async def _opponent_reply(self, state: RoundState, move: MoveEvent, text: str) -> str:
        content = self._modules.content(
            role="user",
            parts=[self._modules.part(text=prompt_for_turn(state, move, text))],
        )

        async for event in self._runner.run_async(
            user_id=USER_ID,
            session_id=state.id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response = event.content.parts[0].text
                    if response:
                        return response
                if event.actions and event.actions.escalate:
                    raise RunnerUnavailable(event.error_message or "Google ADK escalated the turn.")

        raise RunnerUnavailable("Google ADK produced no final opponent response.")


def prompt_for_turn(state: RoundState, move: MoveEvent, text: str) -> str:
    return "\n".join(
        [
            f"Persona: {state.persona.value}",
            f"Difficulty: {state.difficulty.value}",
            f"Concession ladder rung: {state.ladder}",
            f"Latest user move: {text}",
            f"Adjudicator classification: {move.classification.value}",
            f"Adjudicator note: {move.note}",
            "Respond in 1-3 sentences as opposing counsel. Do not coach the user.",
        ]
    )
