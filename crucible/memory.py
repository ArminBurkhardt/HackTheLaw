"""Cross-session user memory — spec §8.

MemoryStore Protocol hides the backend; nothing above this module knows
which implementation is in use. Ship SQLite for the hackathon; swap to
Vertex Agent Engine Memory Bank behind the same interface later.

Gamification DB (rounds/scores/streaks/leaderboard) is a separate concern
handled by the same SQLiteMemoryStore — schema defined here, queries TBD for
the Progress view in Stage 4.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from crucible.schemas import MoveEvent, UserProfile


# ---------------------------------------------------------------------------
# Protocol — the only thing higher layers import
# ---------------------------------------------------------------------------

@runtime_checkable
class MemoryStore(Protocol):
    def get_profile(self, user_id: str) -> UserProfile | None: ...
    def upsert_profile(self, user_id: str, profile: UserProfile) -> None: ...


# ---------------------------------------------------------------------------
# In-memory implementation — for tests and dry runs
# ---------------------------------------------------------------------------

class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._store: dict[str, UserProfile] = {}

    def get_profile(self, user_id: str) -> UserProfile | None:
        return self._store.get(user_id)

    def upsert_profile(self, user_id: str, profile: UserProfile) -> None:
        self._store[user_id] = profile


# ---------------------------------------------------------------------------
# SQLite-backed implementation
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id     TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS round_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    scenario    TEXT NOT NULL,
    persona     TEXT NOT NULL,
    score       INTEGER NOT NULL,
    logged_at   TEXT NOT NULL
);
"""


class SQLiteMemoryStore:
    """Persists UserProfile as JSON in a local SQLite database."""

    def __init__(self, db_path: str | Path = "crucible_memory.db") -> None:
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)

    def get_profile(self, user_id: str) -> UserProfile | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT profile_json FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return UserProfile.model_validate_json(row[0])

    def upsert_profile(self, user_id: str, profile: UserProfile) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profiles (user_id, profile_json, updated_at) "
                "VALUES (?, ?, ?)",
                (user_id, profile.model_dump_json(), now),
            )

    def log_round(
        self,
        user_id: str,
        scenario: str,
        persona: str,
        score: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO round_log (user_id, scenario, persona, score, logged_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, scenario, persona, score, now),
            )


# ---------------------------------------------------------------------------
# Distillation — deterministic, no model call
# ---------------------------------------------------------------------------

def distil(move_events: list[MoveEvent]) -> list[str]:
    """Extract up to 3 durable weakness statements from a round's MoveEvents.

    Returns short, actionable strings suitable for UserProfile.recurring_weaknesses.
    Deterministic — no model call.
    """
    weaknesses: list[str] = []

    # Worst early concession (lowest position_delta)
    concessions = sorted(
        [e for e in move_events if e.classification == "conceded_early"],
        key=lambda e: e.position_delta,
    )
    if concessions:
        worst = concessions[0]
        refs = ", ".join(worst.refs) if worst.refs else "unknown item"
        weaknesses.append(f"concedes {refs} early: {worst.note}")

    # Worst missed opportunity
    misses = sorted(
        [e for e in move_events if e.classification == "missed_point"],
        key=lambda e: e.position_delta,
    )
    if misses:
        worst_miss = misses[0]
        refs = ", ".join(worst_miss.refs) if worst_miss.refs else "unknown item"
        weaknesses.append(f"missed {refs}: {worst_miss.note}")

    # Worst overplay (if under 3 weaknesses so far)
    if len(weaknesses) < 3:
        overplays = sorted(
            [e for e in move_events if e.classification == "overplayed"],
            key=lambda e: e.position_delta,
        )
        if overplays:
            worst_op = overplays[0]
            refs = ", ".join(worst_op.refs) if worst_op.refs else "unknown item"
            weaknesses.append(f"overplayed {refs}: {worst_op.note}")

    return weaknesses[:3]


# ---------------------------------------------------------------------------
# Profile update helper — called by runner after each round
# ---------------------------------------------------------------------------

def update_profile(
    profile: UserProfile | None,
    score: int,
    persona_name: str,
    move_events: list[MoveEvent],
    score_to_beat: int | None,
) -> UserProfile:
    """Merge this round's results into an existing (or new) UserProfile."""
    if profile is None:
        profile = UserProfile(
            recurring_weaknesses=[],
            weak_vs_persona={},
            scores=[],
            streak=0,
        )

    # Weakness score for this persona: 1.0 = totally weak, 0.0 = mastered
    weakness_this_round = max(0.0, 1.0 - score / 100.0)
    prev_weakness = profile.weak_vs_persona.get(persona_name, weakness_this_round)
    # Exponential moving average (0.7 old, 0.3 new)
    new_weakness = round(0.7 * prev_weakness + 0.3 * weakness_this_round, 4)
    updated_persona = {**profile.weak_vs_persona, persona_name: new_weakness}

    # Streak: increment if score beats last round, else reset
    if score_to_beat is not None and score > score_to_beat:
        new_streak = profile.streak + 1
    else:
        new_streak = 0

    # Distil new weaknesses and prepend (dedup, cap at 5)
    new_weaknesses = distil(move_events)
    merged = new_weaknesses + [
        w for w in profile.recurring_weaknesses if w not in new_weaknesses
    ]

    return UserProfile(
        recurring_weaknesses=merged[:5],
        weak_vs_persona=updated_persona,
        scores=[*profile.scores, score],
        streak=new_streak,
    )
