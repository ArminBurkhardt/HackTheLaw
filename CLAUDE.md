For running code, use the venv in `.\venv\Scripts\python.exe`

# CLAUDE.md — Crucible (working guide for the implementing agent)

This is **my operational guide** for building Crucible. It is deliberately short. The detailed product/architecture spec is the source of truth and lives in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); the executable, self-contained per-stage plans live in [plans/](plans/README.md); running insights I must not forget live in [MEMORY.md](MEMORY.md).

> **Read order before writing any code:** this file → the current stage plan in [plans/](plans/README.md) → [MEMORY.md](MEMORY.md). Consult [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) when a stage plan points to it or a detail conflicts.

---

## What Crucible is (in one breath)

An adversarial training ground where a junior lawyer practises real legal work against an AI that **fights back and does not fold to confidence**, then gets **specific, grounded coaching** measured against a concrete standard, and **runs it again** to beat their last score. It is a sparring partner and a coach — **not** an assistant that does legal work for the user. Hold that framing in every decision.

The three non-negotiables (everything serves these):
1. **Realistic adversary** that resists multi-turn and exploits weak reasoning.
2. **A standard to measure against** (a structured playbook / rubric, not vibes).
3. **Specific coaching** at round end + a stronger, cited move.

## Where I am / how I work

- **Execute stages in order** from [plans/](plans/README.md): 0 → 1 → 2 → 2.5 → 3 → 4. Do not start a stage until the previous stage's `✅ Done when` test is green.
- The two tests that gate the whole project: `tests/test_opponent_resistance.py` (Stage 1) and `tests/test_secv.py` (Stage 2.5). Once written they must never go red.
- After each stage, **update [MEMORY.md](MEMORY.md)** with what was non-obvious (pinned model strings, API quirks, fixture paths, tuned thresholds, decisions). Future stages depend on it.

## Hard rules (do not violate)

- **TDD is non-negotiable.** Failing test → minimal code → green → refactor. No production module before its test exists. Test the *contract* (Pydantic fields, classifications, verdicts, AUROC), **never** the prose of LLM output. Mock the model/Perplexity/Neo4j boundaries; keep an opt-in `@pytest.mark.live` suite for pre-demo.
- **Modular code.** Dependency-inject the model client, the memory store, and the graph tools behind interfaces (Protocols). No globals, no model strings hardcoded in agents — read from `config.py`. Pure, deterministic logic (scoring, entropy, graph resolution) lives in side-effect-free functions and is exhaustively unit-tested.
- **The opponent must not fold to tone** (spec §5). Resistance is structural: a hidden concession ladder with explicit `unlock_condition`s, a resistance gate that names which condition was actually met, BATNA anchoring. Personas change *style*, never *whether* it resists.
- **Keep agents separated.** Opponent never breaks character to coach; Adjudicator is neutral and silent; Coach is the only one that gives feedback. This separation is what makes the score trustworthy.
- **Grounding discipline.** Neo4j/CELLAR = authoritative + structural; Perplexity = current context, flagged as commentary not black-letter law. SPARQL/REST only at ingest — runtime touches Neo4j only, never the live endpoint. The vector-index dimension MUST equal the embedder's output dim.
- **SECV cost control.** Run only at debrief and on user citations — **never** inside a live opponent turn. Cache by `(sha1(claim), celex, pinpoint)`.
- **Secrets server-side only.** Never ship `PERPLEXITY_API_KEY` or any key to `web/`.

## UX north star (every stage, every screen)

The product is **one cohesive app**, not a pile of screens. The flow is a ring: **Setup → Arena → Debrief → "Run it again" → …**

- **Lots of selection, guided flow.** Setup is a single obvious wizard: scenario (3) → persona (4) → mode (2) → playbook/case, with sensible defaults and an auto-suggested persona. Never drop the user on a blank screen.
- **Progressive disclosure — hide the noise.** Show only what the moment needs. The Arena is the conversation + a tension meter; scores, MoveEvents, citation internals, and SECV mechanics live behind expanders/drawers, not on the main canvas.
- **But nothing is hidden forever.** Every artifact the system produces — per-turn MoveEvents, full transcript, all citations with SECV status + notes, rubric breakdown, prior-round history — must be reachable somewhere (details drawer, Debrief, or Progress view). The only things hidden *during play* are hidden by design (opponent's concession ladder, BATNA) — and even those are revealed in the Debrief as coaching.
- **Adaptivity is visible.** "Run it again" always carries context forward and announces what it's targeting this round.

## Repo map (target — see spec §9 for the full tree)

```
crucible/   config.py · schemas.py · agents/ · grounding/{cellar,perplexity} · verify/ (SECV) · scenarios/ · memory.py · scoring.py · runner.py
server/     app.py (FastAPI, WS /round/{id}/turn) · voice.py (stretch)
web/        Arena · Debrief · Progress · ScenarioPicker (React + Vite + Tailwind)
tests/      test_opponent_resistance (MUST) · test_secv (MUST) · test_scoring · test_cellar_graph
plans/      per-stage executable plans (this is where I look to know what to build next)
```

## Commands (fill in as stages scaffold them)

`make dev` · `make neo4j` · `make agents` · `make test` (mocked, gates merge) · `make test-live` (pre-demo) · `make index-cellar SCENARIO=…` · `make secv-eval` (AUROC + confusion matrix).

## Stack pins

Python 3.12, pyright, Pydantic at every boundary. Google ADK (Python) for agents; Gemini reasoning + Flash models (**pin exact strings in `config.py` after a Model Garden check** — Gemini 2.5 Pro is the GA fallback). Neo4j 5.x (APOC+GDS) for CELLAR GraphRAG; Perplexity for current context; FastAPI backend; React/Vite/Tailwind frontend; SQLite/Postgres for gamification, Memory Bank (or SQLite-backed) for coaching memory. Region `europe-west1` to keep EU legal data local.
