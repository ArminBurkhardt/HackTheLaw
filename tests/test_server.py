"""FastAPI server tests — gate: WS /round/{id}/turn echoes the model reply."""
from starlette.testclient import TestClient
from server.app import app, get_runner
from crucible.agents.base import FakeModelClient
from crucible.runner import make_runner
from tests.conftest import test_settings


def _override_runner(scripted: list[str]):
    settings = test_settings()
    client = FakeModelClient(scripted=scripted)
    runner = make_runner(settings, client)
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
    _override_runner(["pong"])
    with TestClient(app) as client:
        with client.websocket_connect("/round/r1/turn") as ws:
            ws.send_json({"message": "ping"})
            data = ws.receive_json()
    assert data["reply"] == "pong"


def test_ws_multiple_turns():
    _override_runner(["first", "second"])
    with TestClient(app) as client:
        with client.websocket_connect("/round/r2/turn") as ws:
            ws.send_json({"message": "one"})
            r1 = ws.receive_json()
            ws.send_json({"message": "two"})
            r2 = ws.receive_json()
    assert r1["reply"] == "first"
    assert r2["reply"] == "second"
