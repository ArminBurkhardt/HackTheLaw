# Crucible — Stage Plans Index

This folder breaks the full spec ([../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)) into **self-contained stage plans**. Each stage file is executable on its own: it names every file to create, the schemas/snippets needed, the UX it must deliver, and the exact test that closes it (`✅ Done when`). You should never need to re-read the whole spec to execute a stage — but the spec remains the source of truth if a detail conflicts.

## How to use these

- Execute stages **in order**. Do not start a stage until the previous stage's `✅ Done when` test is green.
- Every stage is **TDD**: write the failing test first, then the minimum code, then refactor.
- After finishing a stage, update [../MEMORY.md](../MEMORY.md) with anything non-obvious you learned (pinned model strings, API quirks, fixture locations, decisions).
- Two tests gate the whole project and must never go red once written: `tests/test_opponent_resistance.py` (Stage 1) and `tests/test_secv.py` (Stage 2.5).

## Stages

| Stage | File | Outcome | Hard gate |
|---|---|---|---|
| 0 | [stage-0-scaffold.md](stage-0-scaffold.md) | Repo, config, FastAPI+React skeleton, ADK hello-world | Message round-trips through Runner into the Arena |
| 1 | [stage-1-vertical-slice.md](stage-1-vertical-slice.md) | Playable Negotiation (Aggressor, playbook mode, text) + Debrief | `test_opponent_resistance.py` green; turn-anchored debrief |
| 2 | [stage-2-cellar-grounding.md](stage-2-cellar-grounding.md) | Neo4j CELLAR graph + tools; inferred mode; grounded coaching | Inferred rubric + stronger move resolves a CELEX in Neo4j |
| 2.5 | [stage-2.5-secv.md](stage-2.5-secv.md) | Semantic-Entropy Citation Verifier (the differentiator) | `test_secv.py` green; AUROC target met; badges render |
| 3 | [stage-3-memory-breadth.md](stage-3-memory-breadth.md) | Memory + Difficulty Tuner; all 3 scenarios + 4 personas | Round 2 targets round 1's weakness; full breadth playable |
| 4 | [stage-4-bonuses-polish.md](stage-4-bonuses-polish.md) | Progress view, turning-point replay, voice (stretch), leaderboard | Progress + replay shipped; voice if time |

## The UX north star (applies to every stage)

The product is **one cohesive app**, not a pile of screens. Hold to these across all stages:

- **Lots of selection, guided flow.** Scenario → persona → mode → playbook/case is a single, obvious wizard with rich choices (3 scenarios, 4 personas, 2 modes), sensible defaults, and an auto-suggested persona. The user is never dropped onto a blank screen.
- **Progressive disclosure.** Show only what the moment needs. The Arena is the conversation + a tension meter — nothing else competes for attention. Scores, MoveEvents, citation internals, and SECV mechanics live behind taps/expanders, not on the main canvas.
- **Nothing is hidden forever.** Every artifact the system produces (per-turn MoveEvents, full transcript, all citations with SECV status, rubric breakdown, prior-round history, opponent's *visible* reasoning) must be reachable somewhere — a details drawer, the Debrief, or the Progress view. Hidden-by-design data (opponent's concession ladder, BATNA) stays hidden during play but is revealed in the Debrief as part of coaching.
- **One continuous loop.** Setup → Arena → Debrief → "Run it again" is a ring, not a dead end. "Run it again" always carries context forward (score-to-beat, targeted weakness).
