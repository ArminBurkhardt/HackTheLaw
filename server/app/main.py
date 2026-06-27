import json
from collections.abc import Callable
from typing import TypeVar

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .grounding_service import GroundingService, GroundingUnavailable
from .live_audio import GeminiLiveAudioService, LiveAudioUnavailable
from .runner import Runner, RunnerUnavailable, make_runner
from .schemas import (
    ArgumentOptionsResponse,
    CreateRoundRequest,
    DebriefResponse,
    GroundingJobResponse,
    GroundingRequest,
    LiveAudioRequest,
    RoundResponse,
    ToolsResponse,
    TurnRequest,
    TurnResponse,
)


def create_app(
    runner: Runner | None = None,
    grounding_service: GroundingService | None = None,
    live_audio_service: GeminiLiveAudioService | None = None,
) -> FastAPI:
    app = FastAPI(title="Crucible Negotiation API")
    runner_error = ""
    try:
        active_runner = runner or make_runner()
    except RunnerUnavailable as error:
        active_runner = None
        runner_error = str(error)
    active_grounding = grounding_service or GroundingService()
    active_live_audio = live_audio_service or GeminiLiveAudioService()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        if active_runner is None:
            return {
                "status": "error",
                "configured": False,
                "runtime": "unconfigured",
                "detail": runner_error,
            }
        return {"status": "ok", "configured": True, "runtime": active_runner.runtime_name}

    @app.get("/api/tools", response_model=ToolsResponse)
    def tools() -> ToolsResponse:
        return ToolsResponse(tools=active_grounding.tool_statuses())

    @app.post("/api/rounds", response_model=RoundResponse)
    def start_round(request: CreateRoundRequest) -> RoundResponse:
        return RoundResponse(round=runner_call(lambda: require_runner().start_round(request)))

    @app.get("/api/rounds/{round_id}", response_model=RoundResponse)
    def get_round(round_id: str) -> RoundResponse:
        state = require_runner().get_round(round_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Round not found")
        return RoundResponse(round=state)

    @app.post("/api/rounds/{round_id}/turns", response_model=TurnResponse)
    def submit_turn(round_id: str, request: TurnRequest) -> TurnResponse:
        active = require_runner()
        if active.get_round(round_id) is None:
            raise HTTPException(status_code=404, detail="Round not found")
        state, move = runner_call(lambda: active.play_turn(round_id, request.text))
        return TurnResponse(round=state, event=move)

    @app.post("/api/rounds/{round_id}/turns/stream")
    def submit_turn_stream(round_id: str, request: TurnRequest) -> StreamingResponse:
        active = require_runner()
        if active.get_round(round_id) is None:
            raise HTTPException(status_code=404, detail="Round not found")

        async def stream_events():
            async for event in active.stream_turn(round_id, request.text):
                yield f"{json.dumps(event.model_dump(mode='json'))}\n"

        return StreamingResponse(stream_events(), media_type="application/x-ndjson")

    @app.post("/api/rounds/{round_id}/end", response_model=DebriefResponse)
    def finish_round(round_id: str) -> DebriefResponse:
        active = require_runner()
        if active.get_round(round_id) is None:
            raise HTTPException(status_code=404, detail="Round not found")
        return DebriefResponse(debrief=runner_call(lambda: active.end_round(round_id)))

    @app.get("/api/rounds/{round_id}/argument-options", response_model=ArgumentOptionsResponse)
    def argument_options(round_id: str) -> ArgumentOptionsResponse:
        active = require_runner()
        if active.get_round(round_id) is None:
            raise HTTPException(status_code=404, detail="Round not found")
        return runner_call(lambda: active.argument_options(round_id))

    @app.post("/api/live-audio")
    async def live_audio(request: LiveAudioRequest) -> Response:
        try:
            audio = await active_live_audio.synthesize(request.text, request.language)
        except LiveAudioUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return Response(content=audio, media_type="audio/wav")

    @app.post("/api/grounding/jobs", response_model=GroundingJobResponse, status_code=202)
    def create_grounding_job(
        request: GroundingRequest,
        background_tasks: BackgroundTasks,
    ) -> GroundingJobResponse:
        try:
            job = active_grounding.create_job(request)
        except GroundingUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        background_tasks.add_task(active_grounding.run_job, job.id)
        return GroundingJobResponse(job=job)

    @app.get("/api/grounding/jobs/{job_id}", response_model=GroundingJobResponse)
    def get_grounding_job(job_id: str) -> GroundingJobResponse:
        job = active_grounding.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Grounding job not found")
        return GroundingJobResponse(job=job)

    def require_runner() -> Runner:
        if active_runner is None:
            raise HTTPException(status_code=503, detail=runner_error)
        return active_runner

    return app


T = TypeVar("T")


def runner_call(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except RunnerUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        if is_rate_limit_error(error):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Google ADK/Gemini rate limit exceeded while generating the round. "
                    "Wait before retrying or use a project/API key with more quota."
                ),
            ) from error
        raise


def is_rate_limit_error(error: BaseException) -> bool:
    message = f"{type(error).__name__}: {error}"
    return "RESOURCE_EXHAUSTED" in message or "rate limit" in message.lower() or "429" in message


app = create_app()
