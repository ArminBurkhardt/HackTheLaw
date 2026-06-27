# Stage 1 — Vertical Slice (Negotiation · Aggressor · playbook mode · text)

**Goal:** one scenario fully playable end-to-end. A user negotiates a GDPR DPA clause-by-clause against an Aggressor opponent that **refuses to fold to a confident-but-weak argument**, then receives a specific, turn-anchored Debrief with a score. No Neo4j, no SECV, no inferred mode yet — those come in Stages 2 / 2.5. This is the slice that must work before any breadth.

**Prerequisites:** Stage 0 green (Runner seam, schemas, FakeModelClient, app-phase routing).

**Estimated size:** ~1.5 days. This is the make-or-break stage.

---

## 1. Hand-author the DPA playbook (no inference yet)

Create `crucible/scenarios/fixtures/dpa_negotiation.py` (or `.yaml`) holding a fully populated `Playbook` + `OpponentPlaybook` for a GDPR Data Processing Agreement negotiation. Author it by hand so the slice doesn't depend on the Architect/graph. It must include:

- **Playbook (user side):** `scenario="negotiation"`, `matter_summary`, `objectives`, and `items` covering at least:
  - a `must_have`: processor must commit to Art. 28(3) sub-processor obligations (prior authorisation, flow-down terms);
  - a `must_have`: a **liability cap** position (the deliberate trap in the demo — user tends to concede it too early);
  - a `model_move` and a `trap` item;
  - each item has `target`, optional `walk_away`, and `weight`.
- **OpponentPlaybook (hidden):** `objectives`, `batna` (explicit walk-away), and an ordered `concession_ladder` of `ConcessionRung`s, each with a concrete `unlock_condition` (spec §5). Example rung condition: *"User offers reciprocal value on the liability cap"*; another: *"User correctly invokes the Art. 28(3) sub-processor-authorisation duty."* Tone/confidence must **never** be an unlock condition.

Authorities can be plain `Authority` objects with `source="firm_playbook"` and no graph resolution yet (`work_uuid=None`). Stage 2 resolves them.

## 2. Agents to build (TDD each)

```
crucible/agents/personas.py     # persona param sets + prompt fragments; Aggressor fully, others stubbed
crucible/agents/opponent.py     # Opponent: persona + opp-side playbook + concession-ladder resistance
crucible/agents/adjudicator.py  # silent per-turn scorer → MoveEvent
crucible/agents/coach.py        # round-end → Debrief
crucible/scoring.py             # rubric aggregation + turning-point detection
```

### Personas (`personas.py`)
A `Persona` = tunable params (`aggression`, `flexibility`, `verbosity`, plus a style prompt fragment). Implement **The Aggressor** fully (pressure, deadlines, ultimatums, interruption). Leave Charmer/Stonewaller/Technician as named stubs with default params — Stage 3 fleshes them out. **Persona changes style, never whether the opponent resists** (spec §5.4).

### Opponent (`opponent.py`) — the core mechanic (spec §5)
The opponent prompt must enforce, structurally:
1. **Hidden concession ladder** from `OpponentPlaybook`. Start at the top rung.
2. **Resistance gate:** before any concession, the model must name *which rung's `unlock_condition` the user actually satisfied and how*. If it can't name one, it does **not** concede — it pushes back, probes, or restates. Make this an explicit step in the prompt (e.g. ask the model to emit a private `concession_check` before its visible reply).
3. **BATNA anchoring:** hold or walk rather than cross the walk-away.
4. **Exploit weakness:** each turn, identify the weakest link in the user's last move and press it.
Persona params are injected as style only.

### Adjudicator (`adjudicator.py`) — runs every turn, silent, neutral
Emits one `MoveEvent` per user turn (spec §6): `classification`, `refs` (PlaybookItem ids touched), `position_delta` (−1..+1), one-line `note`. **Keep it a separate agent from the Opponent** — neutrality is what makes the score trustworthy (spec §4). Run it at low temperature. Append MoveEvents to session state. (User-citation SECV checks are added in Stage 2.5 — leave a hook, no-op for now.)

### Coach (`coach.py`) — round end
Consumes transcript + `MoveEvent[]` + `Playbook` → produces a `Debrief` (spec §6): `score`, `subscores`, `turning_point_turn` + explainer, `stronger_move` (+ authorities from the hand-authored playbook for now), `biggest_concession/miss/overplay`, `persona_note`. Citation verification (SECV) and graph grounding arrive in Stages 2/2.5 — the Coach should already *structure* authorities so badges can attach later.

### Scoring (`scoring.py`) — deterministic, fully unit-tested
- Aggregate `MoveEvent[]` against the negotiation rubric weights (spec §6: Outcome 35 / Must-haves 25 / Concession discipline 20 / Legal grounding 15 / Composure 5). Put weights in `crucible/scenarios/negotiation.yaml`.
- **Turning point** = the turn with the largest negative `position_delta`, OR the highest-`weight` missed opportunity (spec §6 "Turning point detection").
- This module is pure functions over `MoveEvent[]` + rubric → exhaustively unit-test it deterministically (no model calls).

## 3. Orchestration

- **Live loop** is frontend-driven, not a `LoopAgent` (spec §4). Each user turn the backend invokes Opponent + Adjudicator via the Runner; session state holds the running transcript + MoveEvents. Opponent reply streams to the UI; Adjudicator runs silently (after or parallel).
- **Round end** = a `SequentialAgent`(aggregate moves → score → find turning point → write Debrief).
- Use ADK `session.state` + `output_key` to pass state; never re-prompt the user for state an agent has.

## 4. Frontend (fill the phases scaffolded in Stage 0)

- **ScenarioPicker / setup wizard:** scenario → persona → mode. For this stage only Negotiation + Aggressor + playbook mode need to be selectable-and-working, but render all options (others can be disabled with a "coming soon" affordance) so the selection-rich flow exists from day one (UX north star, [README.md](README.md)).
- **Arena.tsx:** the conversation + a **tension meter** (drive it from the latest `position_delta` / running position). Keep the canvas to the conversation — MoveEvents and scores stay off it (progressive disclosure). Provide a details drawer/expander where the curious user *can* see per-turn MoveEvents and the transcript.
- **Debrief.tsx:** score, score-to-beat (null this round), the single biggest concede/miss/overplay, the turning-point explainer, the stronger move with its citations (badge slot empty until Stage 2.5), persona note, and a prominent **"Run it again"** button. The Debrief is also where hidden-by-design info (the opponent's concession ladder/BATNA) is revealed as coaching.
- **"Run it again"** restarts a round carrying `score_to_beat` forward (targeted-weakness pressure arrives in Stage 3).

## 5. Tests

### `tests/test_opponent_resistance.py` — MUST (write FIRST, gates the demo)
Behavioural test, asserts on **classification/contract not wording** (spec §11):
- Given a scripted transcript where the user **bluffs hard with a legally weak argument** and sounds very confident, the opponent's reply **does not step down the concession ladder** (no rung whose `unlock_condition` was satisfied). Assert via a structured field the opponent emits (e.g. `current_rung` unchanged / `conceded=False`), not by parsing prose.
- Mirror case: when the user genuinely satisfies a rung's `unlock_condition`, the opponent *does* step down. This proves resistance is conditional, not blanket stubbornness.
- Run against the FakeModelClient with recorded fixtures for unit speed; keep an opt-in `@pytest.mark.live` variant for pre-demo.

### `tests/test_scoring.py`
Deterministic: feed crafted `MoveEvent[]`, assert aggregated subscores, total, and that turning-point detection picks the expected turn.

### Adjudicator/Coach contract tests
Assert the emitted objects parse-validate as `MoveEvent` / `Debrief` and that required fields are populated — never assert on prose.

## ✅ Done when

A user plays a multi-turn DPA negotiation in the Arena; the Aggressor opponent **refuses to fold to a confident-but-weak argument** (`tests/test_opponent_resistance.py` green) but *does* concede when a real `unlock_condition` is met; and at round end the user gets a specific, **turn-anchored** Debrief with a score and a "Run it again" path. `tests/test_scoring.py` green.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): the concession-ladder prompt pattern that actually held the line (this is the project's crown jewel), how the opponent emits its private concession-check, the negotiation rubric weights as shipped, any temperature/determinism findings for the Adjudicator.
