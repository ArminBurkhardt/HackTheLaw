# Stage 3 — Memory + Adaptivity + Breadth

**Goal:** make the loop *learn*. Persist a cross-session `UserProfile`, add the Difficulty Tuner so round 2 pressures round 1's weakness, have the Coach reference prior weaknesses, and add the remaining breadth: all **3 scenarios** (Negotiation, Hot Seat, Difficult Client) and all **4 personas** (Aggressor, Charmer, Stonewaller, Technician) playable, with persona auto-suggestion.

**Prerequisites:** Stages 1, 2, 2.5 green. The negotiation slice resists, scores, grounds, and verifies citations.

**Estimated size:** ~1 day.

---

## 1. Memory (`crucible/memory.py`)

Persist `UserProfile` (spec §6): `recurring_weaknesses`, `weak_vs_persona`, `scores`, `streak`.
- **Interface hides the backend** (spec §13): a `MemoryStore` Protocol with `get_profile(user_id)` / `upsert_profile(...)`. Ship a **Postgres/SQLite-backed** implementation first (simplest for the hackathon); leave a Vertex Agent Engine Memory Bank implementation behind the same interface as a later swap. Nothing above `memory.py` knows which is in use.
- After each Debrief, **distil 1–3 durable weakness statements** and upsert them — store *lessons*, not raw transcripts (spec §8). E.g. "concedes the liability cap before securing the sub-processor must-have."
- **Guardrail (spec §8):** memory targets weaknesses, it never softens feedback to flatter the user.

**Gamification DB stays separate** (spec §8): rounds/scores/streaks/leaderboard for the Progress view live in Postgres/SQLite, distinct from coaching memory. Define both schemas here even though the Progress *view* is Stage 4.

## 2. Difficulty Tuner (`crucible/agents/tuner.py`) — runs between rounds

Reads the user's history (scores, recurring weaknesses, which persona they fold to) → outputs next-round params (spec §4, §8): opponent `aggression`, how much scaffolding to remove, and **which known weak spot to pressure**. It feeds the Opponent a directive (e.g. "probe their tendency to concede price before locking must-haves"). This is the engine behind "Run it again" doing something *different*.

Wire it into the "Run it again" path: round N+1's Opponent receives the Tuner directive + `score_to_beat`.

## 3. Coach references memory

The Coach now explicitly notes whether a known weakness **recurred or improved** (spec §8): "you fixed last round's early-concession problem; new gap is X." This requires the Coach to read the `UserProfile` alongside transcript + MoveEvents + Playbook.

## 4. Breadth: scenarios

Add configs + rubrics in `crucible/scenarios/`:
- `hot_seat.yaml` — defend a legal position while an AI partner grills you for the weak point. Rubric: defence robustness / killer-counter handling / **citation accuracy** (this scenario leans hard on SECV — user citations get checked every turn). Same `Playbook`/`MoveEvent`/`Debrief` artifacts.
- `difficult_client.yaml` — deliver hard, correct advice to an AI client who pushes back. Rubric: held-the-line on correct advice / relationship management / documented risk.

Each scenario gets its own rubric weights (spec §6) and system-prompt defaults, but reuses the same agents and orchestration. The **concession-ladder / resistance mechanic generalises**: Hot Seat's "ladder" is the partner's line of attack; Difficult Client's is the client's resistance to accepting advice — same structural "don't fold to tone" rule (spec §5).

## 5. Breadth: personas (`crucible/agents/personas.py`)

Flesh out the three stubbed in Stage 1: **Charmer** (flattery, false consensus, warmth-buried concession traps), **Stonewaller** (flat refusal, repetition, withholding, waits you out), **Technician** (clause-detail flood, exploits imprecision, demands citations). Each is style params + prompt fragment only — **substance/resistance is invariant** (spec §5.4).

**Persona auto-suggestion:** suggest the persona the user is currently weakest against, read from `weak_vs_persona`. Surface it as a recommended default in the picker (still user-overridable).

## 6. Frontend

- The setup wizard now offers all 3 scenarios × 4 personas × 2 modes as real, selectable, explained options, with the auto-suggested persona pre-highlighted (UX north star: lots of selection, guided flow).
- "Run it again" shows *what* it's targeting this round ("This round pressures: conceding the liability cap early") so the adaptivity is visible, not silent.
- The Coach's "recurred/improved" note is rendered prominently in the Debrief.

## 7. Tests

- **Adaptivity test:** given a `UserProfile` with a known weakness, the Tuner emits a directive naming that weakness and the next Opponent prompt contains the pressure directive. Assert on the structured directive, not prose.
- **Memory distillation test:** a Debrief with a clear early-concession → `memory.distil()` produces a weakness statement; upsert+get round-trips; streak increments correctly. Deterministic.
- **Per-scenario contract tests:** Hot Seat and Difficult Client each produce valid `Playbook`/`MoveEvent`/`Debrief`; Hot Seat routes user citations through SECV (verify the Adjudicator hook fires).
- Resistance test (`test_opponent_resistance.py`) still green across personas — confirm a persona change doesn't soften resistance.

## ✅ Done when

Round 2 **visibly targets round 1's weakness** (the Tuner directive shows up in the Opponent's behaviour and the UI announces what's being pressured), and all **3 scenarios + 4 personas** are playable end-to-end with grounded, SECV-verified coaching.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): which memory backend shipped (SQLite/Postgres vs Memory Bank) and the `MemoryStore` interface, the distillation prompt, per-scenario rubric weights as shipped, persona param tables, and how Hot Seat / Difficult Client adapt the concession-ladder mechanic.
