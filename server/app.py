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

# ---------------------------------------------------------------------------
# Pre-session briefs — static per scenario
# ---------------------------------------------------------------------------

_BRIEFS: dict[str, dict] = {
    "negotiation": {
        "key_authorities": [
            {"title": "GDPR Art. 28", "pinpoint": "Art. 28", "note": "Controller-Processor requirements — your primary anchor"},
            {"title": "GDPR Art. 28(2)", "pinpoint": "Art. 28(2)", "note": "Written authorisation required before sub-processors are engaged"},
            {"title": "GDPR Art. 28(3)(d)", "pinpoint": "Art. 28(3)(d)", "note": "Sub-processor must face identical obligations — cite both (2) and (3)(d) together"},
            {"title": "GDPR Art. 28(3)(h)", "pinpoint": "Art. 28(3)(h)", "note": "Audit rights — never sacrifice these to unlock a commercial concession"},
            {"title": "GDPR Art. 83(4)", "pinpoint": "Art. 83(4)", "note": "ICO fines up to €10M / 2% global turnover — quantify the shared exposure"},
        ],
        "strategy_tips": [
            "Cite Art. 28(2) and Art. 28(3)(d) together: prior written authorisation plus flow-down obligations form a complete shield.",
            "Lock must-haves before any concession. Art. 28(3)(h) audit rights are non-negotiable — do not soften them to unlock anything.",
            "Vague GDPR references will not satisfy any unlock condition. The opponent's ladder demands chapter-and-verse precision.",
            "Quantify the shared exposure: Art. 83(4) fines are not just your problem — use them as commercial leverage.",
        ],
        "watch_out": [
            "Commercial pressure before data protection clauses are agreed — resist the order inversion.",
            "'Reasonable endeavours' language replacing specific GDPR obligations — reject every instance with the precise article text.",
            "The opponent's BATNA is real: they have other controller clients and can walk away. Know when a win is a win.",
            "Accepting general written authorisation under Art. 28(2) when your opening position is prior specific authorisation.",
        ],
    },
}

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


@app.get("/brief/{scenario}")
async def get_brief(scenario: str):
    brief = _BRIEFS.get(scenario)
    if brief is None:
        raise HTTPException(status_code=404, detail=f"No brief for scenario {scenario!r}")
    return {"scenario": scenario, **brief}


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
        return {"scores": [], "streak": 0, "weak_vs_persona": {}, "recurring_weaknesses": [], "history": [], "latest_subscores": {}}
    return {
        "scores": profile.scores if profile else [],
        "streak": profile.streak if profile else 0,
        "weak_vs_persona": profile.weak_vs_persona if profile else {},
        "recurring_weaknesses": profile.recurring_weaknesses if profile else [],
        "history": history,
        "latest_subscores": profile.latest_subscores if profile else {},
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
