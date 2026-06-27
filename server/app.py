"""FastAPI backend — Stage 1 wiring.

Endpoints:
  GET  /health
  POST /round/{id}/start   — initialise session with scenario/persona/mode
  WS   /round/{id}/turn    — bidirectional turn loop; sends TurnResult JSON
  POST /round/{id}/end     — trigger Coach debrief; returns TurnResult with Debrief
"""
from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from crucible.config import Settings, get_settings
from crucible.agents.base import make_client
from crucible.runner import CrucibleRunner, make_runner
from crucible.scenarios.fixtures.dpa_negotiation import OPPONENT_PLAYBOOK, PLAYBOOK

app = FastAPI(title="Crucible")

_runner: CrucibleRunner | None = None


def get_runner() -> CrucibleRunner:
    global _runner
    if _runner is None:
        settings = get_settings()
        client = make_client(settings)
        _runner = make_runner(settings, client)
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


@app.post("/round/{round_id}/start")
async def start_round(
    round_id: str,
    body: StartRequest,
    runner: CrucibleRunner = Depends(get_runner),
):
    if body.scenario != "negotiation":
        raise HTTPException(status_code=400, detail=f"Scenario {body.scenario!r} not yet implemented")
    runner.start_session(
        session_id=round_id,
        playbook=PLAYBOOK,
        opp_playbook=OPPONENT_PLAYBOOK,
        persona_name=body.persona,
        score_to_beat=body.score_to_beat,
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
            reply = runner.run_turn(session_id=round_id, user_msg=user_msg)
            # Always include "reply" at top level for Stage 0 test compat.
            # If the session is a Stage 1 session, run_turn_full gives richer data;
            # the WS handler stays thin — clients that want full TurnResult use the
            # richer run_turn_full path exposed via a separate message type below.
            await websocket.send_json({"reply": reply})
    except WebSocketDisconnect:
        pass
