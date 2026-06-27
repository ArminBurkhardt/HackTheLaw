"""Stage 0 gate test — must stay green forever."""
import pytest
from tests.conftest import test_settings
from crucible.agents.base import FakeModelClient
from crucible.runner import make_runner


def test_runner_roundtrips_message():
    settings = test_settings(use_real_model=False)
    client = FakeModelClient(scripted=["pong"])
    runner = make_runner(settings, client)
    reply = runner.run_turn(session_id="s1", user_msg="ping")
    assert reply == "pong"


def test_fake_client_callable():
    calls = []

    def handler(**kw):
        calls.append(kw)
        return "called"

    client = FakeModelClient(scripted=handler)
    result = client.generate(model="m", system="s", messages=[])
    assert result == "called"
    assert calls[0]["model"] == "m"


def test_runner_keeps_history_per_session():
    settings = test_settings()
    client = FakeModelClient(scripted=["r1", "r2"])
    runner = make_runner(settings, client)
    runner.run_turn("s1", "msg1")
    runner.run_turn("s1", "msg2")
    # session s1 should have 4 entries: 2 user + 2 assistant
    assert len(runner._sessions["s1"]) == 4


def test_runner_isolates_sessions():
    settings = test_settings()
    client = FakeModelClient(scripted=["a", "b"])
    runner = make_runner(settings, client)
    runner.run_turn("s1", "hello")
    runner.run_turn("s2", "world")
    assert len(runner._sessions["s1"]) == 2
    assert len(runner._sessions["s2"]) == 2
