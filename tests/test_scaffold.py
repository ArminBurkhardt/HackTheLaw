"""Stage 0 gate test — must stay green forever."""
import pytest
from tests.conftest import test_settings
from crucible.agents.base import FakeModelClient, ModelClientError
from crucible.runner import make_runner
from crucible.scenarios.fixtures.dpa_negotiation import PLAYBOOK, OPPONENT_PLAYBOOK


def test_runner_roundtrips_message():
    settings = test_settings()
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


def test_runner_uses_fast_model_for_debrief_coach():
    settings = test_settings()
    client = FakeModelClient(scripted=["unused"])
    runner = make_runner(settings, client)
    runner.start_session("debrief-model", PLAYBOOK, OPPONENT_PLAYBOOK)

    assert runner._sessions["debrief-model"].coach._model == settings.fast_model


def test_end_round_attaches_rl_insights():
    """A finished round must carry the grounded RL bundle on its Debrief."""
    settings = test_settings()

    def handler(*, model, system, messages, **kw):
        if "senior legal training coach" in system:
            return (
                '{"turning_point_explainer": "x", "stronger_move": "y", '
                '"persona_note": "z"}'
            )
        # Opponent / adjudicator / opening — any structured reply is fine here.
        return '{"classification": "conceded_early", "refs": [], "position_delta": -0.8, "note": "n"}'

    runner = make_runner(settings, FakeModelClient(scripted=handler))
    runner.start_session("rl-round", PLAYBOOK, OPPONENT_PLAYBOOK)
    runner.opening_turn("rl-round")

    turn = runner.run_turn_full("rl-round", "We accept the 1x cap.")
    assert turn.win_probability is not None
    assert 0.0 <= turn.win_probability <= 1.0

    result = runner.end_round("rl-round")
    rl = result.debrief.rl
    assert rl is not None
    assert len(rl.win_prob_trajectory) == len(runner._sessions["rl-round"].move_events)
    assert rl.max_regret_turn >= 1
    assert -0.3 <= rl.recommended_aggression_delta <= 0.3


def test_end_round_failure_does_not_complete_session():
    settings = test_settings()

    def handler(*, model, system, messages, **kw):
        if "senior legal training coach" in system:
            raise ModelClientError("quota exhausted", status_code=429)
        return "unused"

    runner = make_runner(settings, FakeModelClient(scripted=handler))
    runner.start_session("debrief-fails", PLAYBOOK, OPPONENT_PLAYBOOK)

    with pytest.raises(ModelClientError):
        runner.end_round("debrief-fails")

    assert runner._sessions["debrief-fails"].round_complete is False
