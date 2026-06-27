from app.adk_runner import (
    argument_options_from_response,
    judge_debrief_from_response,
    prompt_for_argument_options,
    prompt_for_judge,
    prompt_for_turn,
)
from app.engine import create_round, end_round, play_turn
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
    assert "Tool policy: call grounding tools only when uncertain" in prompt
    assert "Adjudicator note" not in prompt


def test_live_opponent_prompt_separates_argument_from_feedback() -> None:
    state = create_round("round-1", Persona.aggressor, Difficulty.associate)
    next_state, move = play_turn(state, "I will tell you to shut up.")

    prompt = prompt_for_turn(next_state, move, "I will tell you to shut up.")

    assert "do not coach, score, critique tone" in prompt
    assert "profanity/professionalism" in prompt
    assert "You missed" not in prompt
    assert "Our position remains" in prompt


def test_engine_debrief_includes_argument_specific_review() -> None:
    state = create_round("round-1", Persona.technician, Difficulty.associate)
    next_state, _move = play_turn(state, "We need GDPR Art. 28 audit rights.")

    debrief = end_round(next_state)

    assert debrief.argument_reviews[0].turn == 1
    assert "GDPR Art. 28" in debrief.argument_reviews[0].quote
    assert debrief.argument_reviews[0].feedback


def test_judge_prompt_contains_transcript_and_events() -> None:
    state = create_round("round-1", Persona.technician, Difficulty.associate)
    next_state, _move = play_turn(state, "We need GDPR Art. 28 audit rights.")
    base = end_round(next_state)

    prompt = prompt_for_judge(next_state, base)

    assert "Transcript:" in prompt
    assert "Rule adjudicator events:" in prompt
    assert "We need GDPR Art. 28 audit rights." in prompt


def test_judge_response_maps_to_debrief_reviews() -> None:
    state = create_round("round-1", Persona.technician, Difficulty.associate)
    next_state, _move = play_turn(state, "We need GDPR Art. 28 audit rights.")
    base = end_round(next_state)
    response = """
    {
      "score": 68,
      "headline": "You found the right legal hook.",
      "turning_point": "Turn 1: Article 28 was useful but the trade was thin.",
      "stronger_move": "Pair Article 28 with a concrete audit trigger and a reciprocal concession.",
      "next_run_focus": "Name authority, operational limit, and trade in one sentence.",
      "argument_reviews": [
        {
          "turn": 1,
          "verdict": "good legal hook, missing trade",
          "quote": "GDPR Art. 28 audit rights",
          "feedback": "This names relevant authority, but it does not yet offer reciprocal value."
        }
      ]
    }
    """

    debrief = judge_debrief_from_response(response, base)

    assert debrief.score == 68
    assert debrief.turning_point_turn == base.turning_point_turn
    assert debrief.argument_reviews[0].quote == "GDPR Art. 28 audit rights"


def test_argument_options_prompt_and_parser_require_three_cards() -> None:
    state = create_round("round-1", Persona.technician, Difficulty.junior)
    prompt = prompt_for_argument_options(state)
    response = """
    {
      "options": [
        {"label": "Hook", "move": "Anchor this in Article 28.", "rationale": "Names authority."},
        {"label": "Limit", "move": "Offer annual evidence review.", "rationale": "Limits burden."},
        {"label": "Trade", "move": "Ask for records in exchange.", "rationale": "Keeps leverage."}
      ]
    }
    """

    options = argument_options_from_response(response)

    assert "exactly 3 items" in prompt
    assert "Do not invent citations" in prompt
    assert options[0].label == "Hook"
    assert options[2].move == "Ask for records in exchange."
