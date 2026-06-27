"""FastAPI backend — Stage 4 wiring.

Endpoints:
  GET  /health
  POST /round/{id}/start   — initialise session with scenario/persona/mode
  WS   /round/{id}/turn    — bidirectional turn loop; sends TurnResult JSON
  POST /round/{id}/end     — trigger Coach debrief; returns TurnResult with Debrief
  GET  /progress/{user_id} — score history, streak, persona breakdown, weaknesses
"""
from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from crucible.config import Settings, get_settings
from crucible.agents.base import make_client
from crucible.agents.tuner import DifficultyTuner
from crucible.memory import SQLiteMemoryStore
from crucible.runner import CrucibleRunner, make_runner
from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK, PLAYBOOK

app = FastAPI(title="Crucible")

_runner: CrucibleRunner | None = None
_memory_store: SQLiteMemoryStore | None = None


def get_memory_store() -> SQLiteMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = SQLiteMemoryStore("crucible_memory.db")
    return _memory_store


def get_runner() -> CrucibleRunner:
    global _runner
    if _runner is None:
        settings = get_settings()
        client = make_client(settings)
        _runner = make_runner(settings, client, memory_store=get_memory_store())
    return _runner


# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


class StartRequest(BaseModel):
    scenario: str = "negotiation"
    persona: str = "aggressor"
    mode: str = "playbook"
    score_to_beat: int | None = None
    user_id: str = "demo_user"


@app.post("/round/{round_id}/start")
async def start_round(
    round_id: str,
    body: StartRequest,
    runner: CrucibleRunner = Depends(get_runner),
):
    if body.scenario != "negotiation":
        raise HTTPException(status_code=400, detail=f"Scenario {body.scenario!r} not yet implemented")

    # Adaptive difficulty: tune next round based on user history
    tuner_directive: str | None = None
    memory = get_memory_store()
    profile = memory.get_profile(body.user_id)
    if profile and body.score_to_beat is not None:
        try:
            settings = get_settings()
            client = make_client(settings)
            tuner = DifficultyTuner(client=client, model=settings.fast_model)
            directive = tuner.tune(profile, scenario=body.scenario)
            tuner_directive = directive.pressure_note
        except Exception:
            pass  # tuner failure must never block the round

    runner.start_session(
        session_id=round_id,
        playbook=PLAYBOOK,
        opp_playbook=OPPONENT_PLAYBOOK,
        persona_name=body.persona,
        score_to_beat=body.score_to_beat,
        user_id=body.user_id,
        tuner_directive=tuner_directive,
    )
    return {"status": "started", "round_id": round_id}


@app.post("/round/{round_id}/end")
async def end_round(
    round_id: str,
    runner: CrucibleRunner = Depends(get_runner),
):
    try:
        result = runner.end_round(round_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.model_dump()


@app.get("/progress/{user_id}")
async def get_progress(user_id: str):
    memory = get_memory_store()
    profile = memory.get_profile(user_id)
    history = memory.get_round_history(user_id)
    if profile is None and not history:
        return {"scores": [], "streak": 0, "weak_vs_persona": {}, "recurring_weaknesses": [], "history": []}
    return {
        "scores": profile.scores if profile else [],
        "streak": profile.streak if profile else 0,
        "weak_vs_persona": profile.weak_vs_persona if profile else {},
        "recurring_weaknesses": profile.recurring_weaknesses if profile else [],
        "history": history,
    }


# ---------------------------------------------------------------------------
# WebSocket turn loop
# ---------------------------------------------------------------------------

@app.websocket("/round/{round_id}/turn")
async def round_turn(
    websocket: WebSocket,
    round_id: str,
    runner: CrucibleRunner = Depends(get_runner),
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_msg: str = data.get("message", "")
            result = runner.run_turn_full(session_id=round_id, user_msg=user_msg)
            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        pass
    except ValueError as exc:
        await websocket.close(code=1008, reason=str(exc))
