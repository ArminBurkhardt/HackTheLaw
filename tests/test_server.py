"""FastAPI server tests — gate: WS /round/{id}/turn sends full TurnResult."""
import json
from starlette.testclient import TestClient
from server.app import app, get_runner
from crucible.agents.base import FakeModelClient
from crucible.runner import make_runner
from crucible.scenarios.fixtures.dpa_negotiation import PLAYBOOK, OPPONENT_PLAYBOOK
from tests.conftest import test_settings


def _opp_json(reply: str, rung: int = 0) -> str:
    return json.dumps({
        "resistance_check": {"rung_index": None, "condition_met": None, "conceded": False},
        "current_rung": rung,
        "reply": reply,
    })


def _adj_json(turn: int = 1) -> str:
    return json.dumps({
        "turn": turn,
        "classification": "neutral",
        "refs": [],
        "position_delta": 0.0,
        "note": "test turn",
    })


def _override_runner(scripted: list[str], round_id: str):
    settings = test_settings()
    client = FakeModelClient(scripted=scripted)
    runner = make_runner(settings, client)
    runner.start_session(
        session_id=round_id,
        playbook=PLAYBOOK,
        opp_playbook=OPPONENT_PLAYBOOK,
        persona_name="aggressor",
    )
    app.dependency_overrides[get_runner] = lambda: runner
    return runner


def teardown_function():
    app.dependency_overrides.clear()


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ws_echoes_model_reply():
    _override_runner([_opp_json("pong"), _adj_json(1)], round_id="r1")
    with TestClient(app) as client:
        with client.websocket_connect("/round/r1/turn") as ws:
            ws.send_json({"message": "ping"})
            data = ws.receive_json()
    assert data["reply"] == "pong"


def test_ws_multiple_turns():
    _override_runner(
        [_opp_json("first"), _adj_json(1), _opp_json("second"), _adj_json(2)],
        round_id="r2",
    )
    with TestClient(app) as client:
        with client.websocket_connect("/round/r2/turn") as ws:
            ws.send_json({"message": "one"})
            r1 = ws.receive_json()
            ws.send_json({"message": "two"})
            r2 = ws.receive_json()
    assert r1["reply"] == "first"
    assert r2["reply"] == "second"
