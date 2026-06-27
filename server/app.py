"""FastAPI backend — GET /health, WS /round/{id}/turn."""
from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from crucible.config import Settings, get_settings
from crucible.agents.base import make_client
from crucible.runner import CrucibleRunner, make_runner

app = FastAPI(title="Crucible")

# Module-level runner singleton (replaced via dependency override in tests).
_runner: CrucibleRunner | None = None


def get_runner() -> CrucibleRunner:
    global _runner
    if _runner is None:
        settings = get_settings()
        client = make_client(settings)
        _runner = make_runner(settings, client)
    return _runner


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/round/{round_id}/turn")
async def round_turn(websocket: WebSocket, round_id: str, runner: CrucibleRunner = Depends(get_runner)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_msg: str = data.get("message", "")
            reply = runner.run_turn(session_id=round_id, user_msg=user_msg)
            await websocket.send_json({"reply": reply})
    except WebSocketDisconnect:
        pass
