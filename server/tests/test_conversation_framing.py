from app.adk_runner import prompt_for_turn
from app.engine import create_round, play_turn
from app.schemas import Difficulty, Persona


def test_round_opener_starts_with_context() -> None:
    state = create_round("round-1", Persona.aggressor, Difficulty.associate)

    opener = state.messages[0].text

    assert "DPA" in opener
    assert "Tell me what change you need" in opener


def test_adk_prompt_keeps_turn_in_same_negotiation_context() -> None:
    state = create_round("round-1", Persona.technician, Difficulty.associate)
    next_state, move = play_turn(state, "We need Article 28 audit rights.")

    prompt = prompt_for_turn(next_state, move, "We need Article 28 audit rights.")

    assert "Scenario: You are on a live call negotiating a GDPR data processing agreement." in prompt
    assert "Last opponent message:" in prompt
    assert "do not introduce a new scenario" in prompt
