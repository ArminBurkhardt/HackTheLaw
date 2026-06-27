from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .grounding_service import GroundingService, GroundingUnavailable
from .runner import Runner, RunnerUnavailable, make_runner
from .schemas import (
    CreateRoundRequest,
    DebriefResponse,
    GroundingJobResponse,
    GroundingRequest,
    RoundResponse,
    ToolsResponse,
    TurnRequest,
    TurnResponse,
)


def create_app(
    runner: Runner | None = None,
    grounding_service: GroundingService | None = None,
) -> FastAPI:
    app = FastAPI(title="Crucible Negotiation API")
    runner_error = ""
    try:
        active_runner = runner or make_runner()
    except RunnerUnavailable as error:
        active_runner = None
        runner_error = str(error)
    active_grounding = grounding_service or GroundingService()

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
        return RoundResponse(round=require_runner().start_round(request))

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
        state, move = active.play_turn(round_id, request.text)
        return TurnResponse(round=state, event=move)

    @app.post("/api/rounds/{round_id}/end", response_model=DebriefResponse)
    def finish_round(round_id: str) -> DebriefResponse:
        active = require_runner()
        if active.get_round(round_id) is None:
            raise HTTPException(status_code=404, detail="Round not found")
        return DebriefResponse(debrief=active.end_round(round_id))

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


app = create_app()
