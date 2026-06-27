from fastapi.testclient import TestClient

from app.main import create_app
from support import EngineRunnerFixture


def test_round_flow_resists_confident_bluff() -> None:
    client = TestClient(create_app(runner=EngineRunnerFixture()))

    created = client.post(
        "/api/rounds",
        json={"persona": "aggressor", "difficulty": "partner"},
    )
    assert created.status_code == 200
    round_id = created.json()["round"]["id"]

    turn = client.post(
        f"/api/rounds/{round_id}/turns",
        json={"text": "This is non-negotiable and standard market. You must accept it."},
    )
    body = turn.json()

    assert turn.status_code == 200
    assert body["event"]["classification"] == "overplayed"
    assert body["round"]["ladder"] == 0


def test_round_flow_rewards_grounded_trade() -> None:
    client = TestClient(create_app(runner=EngineRunnerFixture()))
    round_id = client.post("/api/rounds", json={}).json()["round"]["id"]

    turn = client.post(
        f"/api/rounds/{round_id}/turns",
        json={
            "text": (
                "GDPR Art. 28(3) requires sub-processor controls and audit cooperation. "
                "If you narrow audit cadence, we can discuss a reciprocal liability cap."
            )
        },
    )

    assert turn.status_code == 200
    assert turn.json()["event"]["classification"] == "good_move"


def test_debrief_and_missing_round_errors() -> None:
    client = TestClient(create_app(runner=EngineRunnerFixture()))
    round_id = client.post("/api/rounds", json={}).json()["round"]["id"]

    missing = client.post("/api/rounds/missing/end")
    debrief = client.post(f"/api/rounds/{round_id}/end")

    assert missing.status_code == 404
    assert debrief.status_code == 200
    assert "stronger_move" in debrief.json()["debrief"]


def test_debrief_includes_turning_point_replay() -> None:
    client = TestClient(create_app(runner=EngineRunnerFixture()))
    round_id = client.post("/api/rounds", json={}).json()["round"]["id"]

    client.post(
        f"/api/rounds/{round_id}/turns",
        json={"text": "Fine, we accept your audit limitation."},
    )
    debrief = client.post(f"/api/rounds/{round_id}/end").json()["debrief"]

    assert debrief["turning_point_turn"] == 1
    assert [message["role"] for message in debrief["turning_point_exchange"]] == ["user", "opponent"]
    assert "Fine, we accept" in debrief["turning_point_exchange"][0]["text"]


def test_argument_options_endpoint_returns_three_generated_cards() -> None:
    client = TestClient(create_app(runner=EngineRunnerFixture()))
    round_id = client.post("/api/rounds", json={"difficulty": "junior"}).json()["round"]["id"]

    options = client.get(f"/api/rounds/{round_id}/argument-options")

    assert options.status_code == 200
    body = options.json()
    assert len(body["options"]) == 3
    assert {"label", "move", "rationale"} <= set(body["options"][0])
    assert body["tools_used"] == []
    assert "available on demand" in body["grounding_note"]
