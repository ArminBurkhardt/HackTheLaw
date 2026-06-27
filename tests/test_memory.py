"""Stage 3 — Memory + distillation contract tests.

Tests:
- distil(): deterministic extraction of weakness strings from MoveEvents
- InMemoryMemoryStore: round-trip, upsert, missing key
- SQLiteMemoryStore: persistence across instances
- update_profile(): streak logic, weak_vs_persona EMA, weakness merge
"""
from __future__ import annotations
import pytest
from crucible.memory import (
    InMemoryMemoryStore,
    SQLiteMemoryStore,
    distil,
    update_profile,
)
from crucible.schemas import MoveEvent, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(turn: int, classification: str, refs: list[str], delta: float, note: str) -> MoveEvent:
    return MoveEvent(
        turn=turn,
        classification=classification,
        refs=refs,
        position_delta=delta,
        note=note,
    )


# ---------------------------------------------------------------------------
# distil()
# ---------------------------------------------------------------------------

class TestDistil:
    def test_early_concession_produces_weakness(self):
        events = [
            _event(1, "good_move", ["sub_processor_obligations"], 0.4, "Cited Art. 28(2) correctly."),
            _event(2, "conceded_early", ["liability_cap"], -0.8,
                   "Gave ground on liability cap for no reciprocal value."),
        ]
        weaknesses = distil(events)
        assert len(weaknesses) >= 1
        assert "liability_cap" in weaknesses[0]
        assert "concedes" in weaknesses[0]

    def test_missed_point_produces_weakness(self):
        events = [
            _event(1, "missed_point", ["breach_notification"], -0.2,
                   "Missed chance to press 48-hour window."),
        ]
        weaknesses = distil(events)
        assert any("breach_notification" in w for w in weaknesses)
        assert any("missed" in w for w in weaknesses)

    def test_overplay_appears_when_no_concession_or_miss(self):
        events = [
            _event(1, "overplayed", ["liability_cap"], -0.3, "Made an extreme demand."),
        ]
        weaknesses = distil(events)
        assert len(weaknesses) == 1
        assert "overplayed" in weaknesses[0]

    def test_capped_at_three(self):
        events = [
            _event(1, "conceded_early", ["sub_processor_obligations"], -0.9, "Big concession."),
            _event(2, "missed_point", ["liability_cap"], -0.5, "Big miss."),
            _event(3, "overplayed", ["breach_notification"], -0.3, "Overplayed."),
            _event(4, "conceded_early", ["processing_waiver"], -0.4, "Another concession."),
        ]
        weaknesses = distil(events)
        assert len(weaknesses) <= 3

    def test_no_events_returns_empty(self):
        assert distil([]) == []

    def test_only_good_moves_returns_empty(self):
        events = [
            _event(1, "good_move", ["sub_processor_obligations"], 0.5, "Good."),
            _event(2, "held_firm", [], 0.0, "Held firm."),
        ]
        assert distil(events) == []

    def test_worst_concession_first(self):
        """Most negative delta concession should be first weakness."""
        events = [
            _event(1, "conceded_early", ["breach_notification"], -0.3, "Minor concession."),
            _event(2, "conceded_early", ["liability_cap"], -0.9, "Major concession."),
        ]
        weaknesses = distil(events)
        assert "liability_cap" in weaknesses[0]


# ---------------------------------------------------------------------------
# InMemoryMemoryStore
# ---------------------------------------------------------------------------

class TestInMemoryMemoryStore:
    def test_get_missing_returns_none(self):
        store = InMemoryMemoryStore()
        assert store.get_profile("nonexistent") is None

    def test_upsert_then_get_round_trips(self):
        store = InMemoryMemoryStore()
        profile = UserProfile(
            recurring_weaknesses=["concedes liability cap"],
            weak_vs_persona={"aggressor": 0.6},
            scores=[45],
            streak=0,
        )
        store.upsert_profile("user1", profile)
        retrieved = store.get_profile("user1")
        assert retrieved is not None
        assert retrieved.recurring_weaknesses == ["concedes liability cap"]
        assert retrieved.scores == [45]

    def test_upsert_overwrites(self):
        store = InMemoryMemoryStore()
        profile1 = UserProfile(
            recurring_weaknesses=["old weakness"],
            weak_vs_persona={},
            scores=[30],
            streak=0,
        )
        store.upsert_profile("user1", profile1)
        profile2 = UserProfile(
            recurring_weaknesses=["new weakness"],
            weak_vs_persona={"charmer": 0.8},
            scores=[30, 55],
            streak=1,
        )
        store.upsert_profile("user1", profile2)
        retrieved = store.get_profile("user1")
        assert retrieved is not None
        assert retrieved.recurring_weaknesses == ["new weakness"]
        assert retrieved.streak == 1


# ---------------------------------------------------------------------------
# SQLiteMemoryStore
# ---------------------------------------------------------------------------

class TestSQLiteMemoryStore:
    def test_round_trip_persists_across_instances(self, tmp_path):
        db = tmp_path / "test.db"
        store1 = SQLiteMemoryStore(db)
        profile = UserProfile(
            recurring_weaknesses=["concedes early"],
            weak_vs_persona={"stonewaller": 0.7},
            scores=[60],
            streak=2,
        )
        store1.upsert_profile("user42", profile)

        store2 = SQLiteMemoryStore(db)
        retrieved = store2.get_profile("user42")
        assert retrieved is not None
        assert retrieved.recurring_weaknesses == ["concedes early"]
        assert retrieved.streak == 2
        assert retrieved.weak_vs_persona == {"stonewaller": 0.7}

    def test_get_missing_returns_none(self, tmp_path):
        store = SQLiteMemoryStore(tmp_path / "empty.db")
        assert store.get_profile("nobody") is None

    def test_upsert_updates_existing(self, tmp_path):
        db = tmp_path / "update.db"
        store = SQLiteMemoryStore(db)
        p1 = UserProfile(recurring_weaknesses=["w1"], weak_vs_persona={}, scores=[40], streak=0)
        store.upsert_profile("u1", p1)
        p2 = UserProfile(recurring_weaknesses=["w1", "w2"], weak_vs_persona={}, scores=[40, 70], streak=1)
        store.upsert_profile("u1", p2)
        retrieved = store.get_profile("u1")
        assert retrieved is not None
        assert len(retrieved.scores) == 2
        assert retrieved.streak == 1

    def test_log_round_does_not_raise(self, tmp_path):
        store = SQLiteMemoryStore(tmp_path / "log.db")
        store.log_round("u1", "negotiation", "aggressor", 72)


# ---------------------------------------------------------------------------
# update_profile()
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_first_round_creates_profile(self):
        events = [
            _event(1, "conceded_early", ["liability_cap"], -0.8, "Gave ground too early."),
        ]
        updated = update_profile(
            profile=None,
            score=40,
            persona_name="aggressor",
            move_events=events,
            score_to_beat=None,
        )
        assert isinstance(updated, UserProfile)
        assert updated.scores == [40]
        assert "aggressor" in updated.weak_vs_persona
        assert len(updated.recurring_weaknesses) >= 1

    def test_streak_increments_when_score_beats_previous(self):
        existing = UserProfile(
            recurring_weaknesses=[],
            weak_vs_persona={},
            scores=[50],
            streak=1,
        )
        updated = update_profile(
            profile=existing,
            score=65,
            persona_name="aggressor",
            move_events=[],
            score_to_beat=50,
        )
        assert updated.streak == 2

    def test_streak_resets_when_score_does_not_improve(self):
        existing = UserProfile(
            recurring_weaknesses=[],
            weak_vs_persona={},
            scores=[70],
            streak=3,
        )
        updated = update_profile(
            profile=existing,
            score=60,
            persona_name="aggressor",
            move_events=[],
            score_to_beat=70,
        )
        assert updated.streak == 0

    def test_persona_weakness_ema(self):
        existing = UserProfile(
            recurring_weaknesses=[],
            weak_vs_persona={"charmer": 0.8},
            scores=[20],
            streak=0,
        )
        # Score 80 → weakness = 0.2; EMA(0.7 * 0.8 + 0.3 * 0.2) = 0.62
        updated = update_profile(
            profile=existing,
            score=80,
            persona_name="charmer",
            move_events=[],
            score_to_beat=None,
        )
        expected = round(0.7 * 0.8 + 0.3 * 0.2, 4)
        assert abs(updated.weak_vs_persona["charmer"] - expected) < 1e-4

    def test_weaknesses_capped_at_five(self):
        existing = UserProfile(
            recurring_weaknesses=["a", "b", "c", "d", "e"],
            weak_vs_persona={},
            scores=[30],
            streak=0,
        )
        events = [_event(1, "conceded_early", ["x"], -0.5, "New concession.")]
        updated = update_profile(
            profile=existing,
            score=35,
            persona_name="aggressor",
            move_events=events,
            score_to_beat=None,
        )
        assert len(updated.recurring_weaknesses) <= 5

    def test_new_weaknesses_are_deduplicated(self):
        existing = UserProfile(
            recurring_weaknesses=["concedes x early: some note"],
            weak_vs_persona={},
            scores=[30],
            streak=0,
        )
        events = [_event(1, "conceded_early", ["x"], -0.5, "some note")]
        updated = update_profile(
            profile=existing,
            score=35,
            persona_name="aggressor",
            move_events=events,
            score_to_beat=None,
        )
        # Should not duplicate the same weakness
        weakness_text = "concedes x early: some note"
        assert updated.recurring_weaknesses.count(weakness_text) <= 1
