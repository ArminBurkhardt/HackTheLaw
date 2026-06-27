import asyncio
import json
from dataclasses import dataclass
from importlib import import_module
from typing import Callable
from uuid import uuid4

from .engine import create_round, end_round, play_turn
from .schemas import ArgumentOption, ArgumentReview, CreateRoundRequest, Debrief, Message, MoveEvent, Role, RoundState
from .settings import Settings


APP_NAME = "crucible-negotiation"
USER_ID = "crucible-user"

OPPONENT_INSTRUCTION = """
You are opposing counsel in a GDPR DPA negotiation training round.
The user is practicing how to negotiate audit rights, processor obligations,
sub-processor controls, confidentiality, and liability language.
Stay in character as a real counterparty on a call: acknowledge the user's move,
keep continuity with the current DPA issue, and avoid abrupt topic changes.
Resist weak legal reasoning, and concede only when the user names concrete
authority plus reciprocal value. Reply as opposing counsel only.
Do not score, coach, criticize tone, or describe the user's performance during
the live conversation. If the user is rude or off-topic, ignore the tone and
state the opposing legal or commercial position.
Never refer to the user's wording, profanity, professionalism, temper, or
whether they have a legitimate or substantive point. Stay on the contract issue.
""".strip()

JUDGE_INSTRUCTION = """
You are a negotiation coach reviewing a GDPR DPA training transcript.
Return strict JSON only. Ground every comment in the actual transcript.
Do not invent facts, legal provisions, or user arguments that are not present.
""".strip()

ARGUMENT_OPTIONS_INSTRUCTION = """
You generate concise candidate arguments for a legal negotiation training UI.
Return strict JSON only. Use the current transcript and difficulty.
For warmup difficulty, give three concrete draft moves. For harder modes, still
give usable drafts, but make them shorter and less complete so the user must
think and edit. Do not invent facts outside the transcript and DPA context.
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
        self._judge_agent = modules.agent(
            name="crucible_judge",
            model=settings.adk_model,
            instruction=JUDGE_INSTRUCTION,
        )
        self._argument_agent = modules.agent(
            name="crucible_argument_options",
            model=settings.adk_model,
            instruction=ARGUMENT_OPTIONS_INSTRUCTION,
        )
        self._runner = modules.runner(
            agent=self._agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )
        self._judge_runner = modules.runner(
            agent=self._judge_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )
        self._argument_runner = modules.runner(
            agent=self._argument_agent,
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
        state = self._rounds[round_id]
        base = end_round(state)
        if not state.events:
            return base
        return asyncio.run(self._judge_debrief(state, base))

    def argument_options(self, round_id: str) -> list[ArgumentOption]:
        state = self._rounds[round_id]
        return asyncio.run(self._argument_options(state))

    def get_round(self, round_id: str) -> RoundState | None:
        return self._rounds.get(round_id)

    async def _opponent_reply(self, state: RoundState, move: MoveEvent, text: str) -> str:
        return await self._run_agent(self._runner, state.id, prompt_for_turn(state, move, text))

    async def _judge_debrief(self, state: RoundState, base: Debrief) -> Debrief:
        session_id = f"{state.id}-judge"
        await self._session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        response = await self._run_agent(self._judge_runner, session_id, prompt_for_judge(state, base))
        return judge_debrief_from_response(response, base)

    async def _argument_options(self, state: RoundState) -> list[ArgumentOption]:
        session_id = f"{state.id}-argument-options-{state.turn}"
        await self._session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        response = await self._run_agent(self._argument_runner, session_id, prompt_for_argument_options(state))
        return argument_options_from_response(response)

    async def _run_agent(self, runner: object, session_id: str, prompt: str) -> str:
        content = self._modules.content(
            role="user",
            parts=[self._modules.part(text=prompt)],
        )

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response = event.content.parts[0].text
                    if response:
                        return response
                if event.actions and event.actions.escalate:
                    raise RunnerUnavailable(event.error_message or "Google ADK escalated the turn.")

        raise RunnerUnavailable("Google ADK produced no final response.")


def prompt_for_turn(state: RoundState, move: MoveEvent, text: str) -> str:
    return "\n".join(
        [
            "Scenario: You are on a live call negotiating a GDPR data processing agreement.",
            "Current issue: audit rights, processor controls, sub-processors, confidentiality, and liability.",
            f"Persona: {state.persona.value}",
            f"Difficulty: {state.difficulty.value}",
            f"Concession ladder rung: {state.ladder}",
            f"Last opponent message: {previous_opponent_message(state)}",
            f"Baseline response direction: {state.messages[-1].text}",
            f"Latest user move: {text}",
            f"Internal response signal: {move.classification.value}",
            (
                "Respond in 1-3 natural sentences as opposing counsel. Start from the user's latest "
                "sentence, do not introduce a new scenario, and do not coach, score, critique tone, "
                "or mention profanity/professionalism."
            ),
        ]
    )


def previous_opponent_message(state: RoundState) -> str:
    prior_messages = state.messages[:-2] if len(state.messages) >= 2 else state.messages
    for message in reversed(prior_messages):
        if message.role == Role.opponent:
            return message.text
    return state.messages[0].text


def prompt_for_judge(state: RoundState, base: Debrief) -> str:
    return "\n".join(
        [
            "Review this GDPR DPA negotiation transcript.",
            "Return JSON with keys: score, headline, turning_point, stronger_move, next_run_focus, argument_reviews.",
            "argument_reviews must be an array with one item per user turn.",
            "Each argument review needs: turn, verdict, quote, feedback.",
            "Use short exact quotes from the user's move. Be specific about what worked or was missing.",
            "Do not include markdown fences.",
            f"Rule score: {base.score}",
            f"Rule turning point: {base.turning_point}",
            "Transcript:",
            transcript_for_judge(state),
            "Rule adjudicator events:",
            events_for_judge(state),
        ]
    )


def prompt_for_argument_options(state: RoundState) -> str:
    return "\n".join(
        [
            "Generate argument option cards for the user's next move.",
            "Return JSON with key options.",
            "options must contain exactly 3 items.",
            "Each option needs: label, move, rationale.",
            "The move must be a draft the user could send after editing.",
            "Keep each rationale under 18 words.",
            f"Difficulty: {state.difficulty.value}",
            f"Turn: {state.turn}",
            "Transcript:",
            transcript_for_judge(state),
        ]
    )


def transcript_for_judge(state: RoundState) -> str:
    return "\n".join(f"{index + 1}. {message.role.value}: {message.text}" for index, message in enumerate(state.messages))


def events_for_judge(state: RoundState) -> str:
    return "\n".join(
        f"Turn {event.turn}: {event.classification.value}, {event.points} points, {event.note}"
        for event in state.events
    )


def judge_debrief_from_response(response: str, base: Debrief) -> Debrief:
    try:
        payload = json.loads(extract_json_object(response))
    except json.JSONDecodeError as error:
        raise RunnerUnavailable("Google ADK judge returned invalid JSON.") from error

    return Debrief(
        score=int(payload["score"]),
        headline=str(payload["headline"]),
        turning_point=str(payload["turning_point"]),
        turning_point_turn=base.turning_point_turn,
        turning_point_exchange=base.turning_point_exchange,
        stronger_move=str(payload["stronger_move"]),
        next_run_focus=str(payload["next_run_focus"]),
        argument_reviews=[
            ArgumentReview(
                turn=int(item["turn"]),
                verdict=str(item["verdict"]),
                quote=str(item["quote"]),
                feedback=str(item["feedback"]),
            )
            for item in payload["argument_reviews"]
        ],
    )


def argument_options_from_response(response: str) -> list[ArgumentOption]:
    try:
        payload = json.loads(extract_json_object(response))
    except json.JSONDecodeError as error:
        raise RunnerUnavailable("Google ADK argument option generator returned invalid JSON.") from error

    options = payload["options"]
    if not isinstance(options, list) or len(options) != 3:
        raise RunnerUnavailable("Google ADK argument option generator must return exactly 3 options.")

    return [
        ArgumentOption(
            label=str(item["label"]),
            move=str(item["move"]),
            rationale=str(item["rationale"]),
        )
        for item in options
    ]


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    return text[start : end + 1]
