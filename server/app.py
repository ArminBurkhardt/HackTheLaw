"""FastAPI backend — Stage 4 wiring.

Endpoints:
  GET  /health
  POST /round/{id}/start   — initialise session with scenario/persona/mode
  POST /round/{id}/opening — generate idempotent opponent opening turn
  WS   /round/{id}/turn    — bidirectional turn loop; sends TurnResult JSON
  POST /round/{id}/end     — trigger Coach debrief; returns TurnResult with Debrief
  GET  /progress/{user_id} — score history, streak, persona breakdown, weaknesses
"""
from __future__ import annotations
import asyncio
import base64
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from crucible.config import Settings, get_settings
from crucible.agents.base import make_client
from crucible.agents.tuner import DifficultyTuner
from crucible.grounding.perplexity import make_perplexity_client
from crucible.grounding.source_policy import load_source_policy
from crucible.memory import SQLiteMemoryStore
from crucible.live_audio import GeminiLiveAudioService, LiveAudioUnavailable
from crucible.runner import CrucibleRunner, make_runner
from crucible.scenarios.fixtures.saas_license_negotiation import OPPONENT_PLAYBOOK, PLAYBOOK
from server.hardness import hardness_directive

app = FastAPI(title="Crucible")

# ---------------------------------------------------------------------------
# Pre-session briefs — static per scenario
# ---------------------------------------------------------------------------

_BRIEFS: dict[str, dict] = {
    "negotiation": {
        "key_authorities": [
            {"title": "BGB Sec. 307", "pinpoint": "Sec. 307", "note": "Unfair standard terms control — useful against one-sided SaaS risk allocation"},
            {"title": "BGB Sec. 309 No. 7", "pinpoint": "Sec. 309 No. 7", "note": "Do not let standard terms exclude liability for injury, intent, or gross negligence"},
            {"title": "BGB Sec. 276(3)", "pinpoint": "Sec. 276(3)", "note": "Intentional liability cannot be waived in advance"},
            {"title": "Market standard", "pinpoint": "SaaS liability caps", "note": "1x annual fees is provider-friendly; higher caps need economic justification"},
            {"title": "Insurance proof", "pinpoint": "Risk pricing", "note": "A lower cap can be acceptable only if backed by extra coverage or price value"},
        ],
        "strategy_tips": [
            "Start with a clear anchor: 1-2x annual fees plus carve-outs for fraud, intent, gross negligence, and security/privacy incidents.",
            "Ask why the provider's 1x cap is enough for business-critical software; force them to justify the risk allocation.",
            "Use trade-offs deliberately: lower SLA, proof of insurance, price reduction, scope limits, or narrower damage categories.",
            "Do not demand unlimited liability across all damages. Keep uncapped treatment for mandatory carve-outs and serious incidents.",
        ],
        "watch_out": [
            "Too-early acceptance of the provider's 1x annual-fee cap without any reciprocal value.",
            "Blanket exclusion language that accidentally covers gross negligence, intent, fraud, or security/privacy failures.",
            "Commercial pressure to close quickly before the liability structure is clear.",
            "Overplaying unlimited liability so hard that the provider credibly walks away.",
        ],
    },
}

_runner: CrucibleRunner | None = None
_memory_store: SQLiteMemoryStore | None = None
_live_audio_service: GeminiLiveAudioService | None = None
_live_opening_cache: dict[str, dict] = {}
_live_opening_locks: dict[str, asyncio.Lock] = {}


def get_memory_store() -> SQLiteMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = SQLiteMemoryStore("crucible_memory.db")
    return _memory_store


def _build_graph_store(settings: Settings):
    """CELLAR graph store for SECV — None if Neo4j isn't configured/reachable."""
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        return None
    try:
        from crucible.grounding.cellar.neo4j_store import make_neo4j_store
        return make_neo4j_store(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    except Exception:
        return None


def _build_source_policy(settings: Settings):
    try:
        return load_source_policy(settings.allowed_sources_path)
    except Exception:
        return None


def get_runner() -> CrucibleRunner:
    global _runner
    if _runner is None:
        settings = get_settings()
        client = make_client(settings)
        _runner = make_runner(
            settings,
            client,
            memory_store=get_memory_store(),
            graph_store=_build_graph_store(settings),
            perplexity_client=make_perplexity_client(settings.perplexity_api_key),
            source_policy=_build_source_policy(settings),
        )
    return _runner


def get_live_audio_service() -> GeminiLiveAudioService:
    global _live_audio_service
    if _live_audio_service is None:
        _live_audio_service = GeminiLiveAudioService(get_settings())
    return _live_audio_service


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
    hardness: str = "standard"
    mode: str = "playbook"
    score_to_beat: int | None = None
    user_id: str = "demo_user"
    language: str = "en"


class LiveOpeningRequest(BaseModel):
    language: str = "en"


class LiveTurnRequest(BaseModel):
    message: str
    language: str = "en"


@app.post("/round/{round_id}/start")
async def start_round(
    round_id: str,
    body: StartRequest,
    runner: CrucibleRunner = Depends(get_runner),
):
    _live_opening_cache.pop(round_id, None)
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
            tuner = DifficultyTuner(client=client, model=settings.session_prep_model)
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
        hardness_directive=hardness_directive(body.hardness),
        response_language=body.language,
    )
    return {"status": "started", "round_id": round_id}


@app.post("/round/{round_id}/opening")
async def opening_turn(
    round_id: str,
    runner: CrucibleRunner = Depends(get_runner),
):
    try:
        reply = runner.opening_turn(round_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"reply": reply}


@app.post("/round/{round_id}/opening/live")
async def opening_live_turn(
    round_id: str,
    body: LiveOpeningRequest,
    runner: CrucibleRunner = Depends(get_runner),
    service: GeminiLiveAudioService = Depends(get_live_audio_service),
):
    if cached := _live_opening_cache.get(round_id):
        return cached

    lock = _live_opening_locks.setdefault(round_id, asyncio.Lock())
    async with lock:
        if cached := _live_opening_cache.get(round_id):
            return cached
        try:
            system, prompt = runner.opening_live_prompt(round_id)
            utterance = await service.generate_utterance(system=system, prompt=prompt, language=body.language)
            runner.commit_opening_turn(round_id, utterance.transcript)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except LiveAudioUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        payload = _live_utterance_response(utterance.transcript, utterance.wav)
        _live_opening_cache[round_id] = payload
        return payload


@app.post("/round/{round_id}/turn/live")
async def round_live_turn(
    round_id: str,
    body: LiveTurnRequest,
    background_tasks: BackgroundTasks,
    runner: CrucibleRunner = Depends(get_runner),
    service: GeminiLiveAudioService = Depends(get_live_audio_service),
):
    try:
        system, prompt = runner.live_turn_prompt(round_id, body.message)
        utterance = await service.generate_utterance(system=system, prompt=prompt, language=body.language)
        runner.commit_live_turn(round_id, body.message, utterance.transcript)
        background_tasks.add_task(runner.score_pending_turns, round_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LiveAudioUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return _live_utterance_response(utterance.transcript, utterance.wav)


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


@app.get("/round/{round_id}/context")
async def get_round_context(
    round_id: str,
    runner: CrucibleRunner = Depends(get_runner),
):
    try:
        return runner.get_round_context(round_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


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


def _live_utterance_response(transcript: str, wav: bytes) -> dict:
    return {
        "reply": transcript,
        "transcript": transcript,
        "audio_base64": base64.b64encode(wav).decode("ascii"),
        "mime_type": "audio/wav",
    }
