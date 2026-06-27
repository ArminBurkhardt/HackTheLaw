# MEMORY.md — Crucible implementation notes

> Running log of insights, decisions, gotchas, and FYIs **for my future self while building later stages.** Append as I learn; never delete a still-true note. Each stage plan ends with an "Update before moving on" list of what to record here. Keep entries short and concrete (paths, exact strings, numbers, reasons).

---

## How the planning is organised (read this first)

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** = full product/architecture spec, source of truth.
- **[CLAUDE.md](CLAUDE.md)** = my short operational guide (rules, UX north star, read order).
- **[plans/](plans/README.md)** = self-contained per-stage plans. Execute 0 → 1 → 2 → 2.5 → 3 → 4 in order; each is actionable without re-reading the whole spec.
- **This file** = what I learned doing it.

## Cross-cutting decisions (made at planning time)

- **Model-client seam (Stage 0) is load-bearing.** Every agent + the Runner take a `ModelClient` (Protocol) by injection; `FakeModelClient` powers tests and the no-credentials path. Get this right once and every later test is cheap. Same pattern for `MemoryStore` (Stage 3) and the `cellar_*` tools (Stage 2).
- **Define ALL schemas (spec §6) in Stage 0**, not incrementally — avoids churn, since `CitationCheck`/`Debrief`/`MoveEvent` are referenced from Stage 1 onward.
- **App-phase routing (`setup | arena | debrief | progress`) is laid in Stage 0** even though only `arena` is wired, so later stages fill phases without restructuring the frontend.
- **The two MUST tests are written before their features:** `test_opponent_resistance.py` (Stage 1), `test_secv.py` (Stage 2.5). They gate the demo.

## ⚠️ Known traps / gotchas to remember

- **Vector-index dim must equal embedder output dim** (1024 for bge-m3). Mismatch fails *silently* as zero recall. Pin both in `config.py`; assert at index-build time. (Stage 2)
- **Never query live CELLAR SPARQL/REST at runtime** — ingest only. Runtime agents hit Neo4j only. (Stage 2)
- **SECV never runs in a live opponent turn** — debrief + user-citations only; it's `M+|pairs|` Flash calls per citation. Cache by `(sha1(claim), celex, pinpoint)`. (Stage 2.5)
- **Tone is never a concession `unlock_condition`.** The opponent's resistance gate must name a genuinely-satisfied condition before stepping down the ladder. (Stage 1)
- **Persona = style only, never substance.** A persona swap must not soften resistance — keep `test_opponent_resistance.py` green across all four personas. (Stage 3)
- **Entailment oracle is SECV's weak link** — legal entailment is subtle; a wrong NLI verdict flips the whole result. Keep the prompt strict + few-shot with legal pairs; validate on the labelled set before trusting it; treat `weak` as "hedge," not "hide." Fallback = structural resolution + in-force only. (Stage 2.5)
- **Secrets never reach `web/`** (Perplexity key especially).

## To be filled in as stages complete

### Stage 0 — Scaffold ✅
- **Model strings pinned:** `reasoning_model = "gemini-2.5-pro"`, `fast_model = "gemini-2.5-flash"`. `gemini-3.1-pro` was still preview in `europe-west1` as of Jun 2026 — confirmed GA fallback only. Strings live in `crucible/config.py`; never hardcoded in agents.
- **Real model access:** Not wired yet. `use_real_model=False` everywhere; `FakeModelClient` serves all current tests. Wire `GeminiModelClient` in `crucible/agents/gemini_client.py` when credentials exist — the seam is ready.
- **Dep versions (venv, Python 3.14.6):** pytest 9.1.1, anyio 4.14.1, pytest-asyncio 1.4.0, fastapi + starlette (exact versions from `pip freeze`). `httpx` is installed but starlette now warns to use `httpx2` — not blocking, just a warning.
- **`test_settings` gotcha:** pytest collects any function starting with `test_` imported into a test module. Fix: set `test_settings.__test__ = False` in `conftest.py`. Also use `defaults.update(overrides)` pattern instead of `**overrides` splat to avoid duplicate-kwarg errors when callers pass explicit defaults.
- **WebSocket testing:** Use `starlette.testclient.TestClient` (sync) with `client.websocket_connect(...)` context manager. Override `get_runner` dependency via `app.dependency_overrides[get_runner] = lambda: ...` in tests; clear with `app.dependency_overrides.clear()` in teardown.
- **Embed dim:** `text-embedding-004` = 768 dims (max/default); `bge-m3` = 1024. Pinned as `embed_dim` in `Settings`. **Must match Neo4j vector index** — assert at index-build time (Stage 2).

### Stage 1 — Vertical slice ✅
- **Concession-ladder prompt pattern (crown jewel):** A mandatory "RESISTANCE GATE" section in the opponent system prompt forces a two-step output: first name *which rung's `unlock_condition` was genuinely satisfied and how* (`resistance_check`), then emit the visible `reply`. If no rung can be named, `conceded=false` — structural, not relying on model self-discipline. The prompt enumerates exactly what CAN and CANNOT satisfy a condition (tone, confidence, and vague GDPR references are explicitly excluded).
- **Opponent structured output format:** `{"resistance_check": {"rung_index": <int|null>, "condition_met": <str|null>, "conceded": <bool>}, "current_rung": <int>, "reply": "<str>"}`. JSON only — the `_extract_json` helper strips markdown fences and finds the outermost `{…}` as a last resort. Safety clamp: `current_rung` can only advance if `conceded=True`, and is capped at `len(ladder) - 1`.
- **Rubric weights as shipped:** outcome=35, must_haves=25, concession_discipline=20, legal_grounding=15, composure=5. Stored in `crucible/scenarios/negotiation.yaml`; loaded by `scoring.py`; passed explicitly in tests (no YAML I/O in unit tests).
- **Adjudicator:** same `_extract_json` pattern; unknown `classification` values fall back to `"neutral"` (guard against hallucination). No temperature control available via `FakeModelClient`; real-model call should use low temperature — set in `GeminiModelClient` when wired (Stage credentials path).
- **Live-test skip pattern:** `pytest_addoption(--live)` + `pytest_collection_modifyitems` in `conftest.py`. Without `--live`, all `@pytest.mark.live` tests are skipped at collection time (before any model call).
- **`SessionState` vs. legacy sessions:** `CrucibleRunner._sessions` now holds either a `SessionState` (Stage 1, after `start_session()`) or `list[dict]` (Stage 0 legacy path). `run_turn()` dispatches on type; Stage 0 tests stay green without changes.
- **DPA fixture location:** `crucible/scenarios/fixtures/dpa_negotiation.py` — exports `PLAYBOOK` (user side) and `OPPONENT_PLAYBOOK` (hidden, processor side). 3-rung concession ladder; unlock conditions are legally specific (cite Art. 28(2) vs. 28(3)(d) distinction, reciprocal commercial value, shared regulatory risk framing).

### Stage 2 — CELLAR grounding
- Embedding model + dimension (and that index dim matches): _TBD_
- CELEX list actually ingested for the sub-corpus: _TBD_
- Ingestion runtime / row counts; FORMEX/RDF parsing quirks: _TBD_
- Test-Neo4j seeding fixture location: _TBD_
- `Authority` fields the resolver populates (SECV depends on these): _TBD_

### Stage 2.5 — SECV
- Tuned `θ_high`; achieved AUROC + confusion matrix: _TBD_
- Entailment-oracle prompt that worked + failure modes: _TBD_
- Calibration-set location/size: _TBD_
- Cache key format; Flash-call budget per debrief: _TBD_

### Stage 3 — Memory + breadth
- Memory backend shipped (SQLite/Postgres vs Memory Bank) + `MemoryStore` interface: _TBD_
- Distillation prompt: _TBD_
- Per-scenario rubric weights (hot_seat, difficult_client): _TBD_
- Persona param tables: _TBD_
- How Hot Seat / Difficult Client adapt the concession-ladder mechanic: _TBD_

### Stage 4 — Bonuses & polish
- Which bonuses shipped: _TBD_
- Live API / audio gotchas: _TBD_
- Demo run-through notes + any manual workarounds to fix later: _TBD_
