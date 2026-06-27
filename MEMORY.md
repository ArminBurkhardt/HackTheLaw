# MEMORY.md — Crucible implementation notes

> Running log of insights, decisions, gotchas, and FYIs **for my future self while building later stages.** Append as I learn; never delete a still-true note. Each stage plan ends with an "Update before moving on" list of what to record here. Keep entries short and concrete (paths, exact strings, numbers, reasons).

---

## How the planning is organised (read this first)

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** = full product/architecture spec, source of truth.
- **[CLAUDE.md](CLAUDE.md)** = my short operational guide (rules, UX north star, read order).
- **[plans/](plans/README.md)** = self-contained per-stage plans. Execute 0 → 1 → 2 → 2.5 → 3 → 4 in order; each is actionable without re-reading the whole spec.
- **This file** = what I learned doing it.

## Cross-cutting decisions (made at planning time)

- **Model-client seam (Stage 0) is load-bearing.** Every agent + the Runner take a `ModelClient` (Protocol) by injection; `FakeModelClient` powers deterministic tests only. Runtime uses Gemini credentials. Same pattern for `MemoryStore` (Stage 3) and the `cellar_*` tools (Stage 2).
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
- **Real model access:** Runtime always uses `GeminiModelClient` from `crucible/agents/gemini_client.py`; configure `GOOGLE_API_KEY` or `GOOGLE_CLOUD_PROJECT`. `FakeModelClient` is test-only.
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

### Stage 2 — CELLAR grounding ✅
- **Embedding model + dim:** `text-embedding-004` = 768 dims (pinned as `embed_dim=768` in `config.py`). Neo4j vector index `chunk_vec` must be created with this dim — `create_vector_index(driver, dim=768)` asserts at index-build time. `bge-m3` would be 1024 — update `embed_dim` in config.py if you switch.
- **Sub-corpus CELEX list (DPA/negotiation scenario):** `32016R0679` (GDPR), `31995L0046` (Directive 95/46 — repealed), `32002L0058` (ePrivacy), `32016L0680` (LED), `32018R1725` (EU institutions). In `crucible/grounding/cellar/cellar_sparql.py → query_gdpr_subcorpus()`.
- **GraphStore injection seam:** `GraphStore` Protocol in `crucible/grounding/cellar/graph_store.py`. Tests use `InMemoryGraphStore` (no Neo4j driver). Prod uses `Neo4jGraphStore` in `neo4j_store.py`. Agents and SECV import the Protocol only — never the concrete class.
- **Test seeding fixture location:** `tests/test_cellar_graph.py` → `seeded_store` fixture (GDPR + 1995 Directive + repeals edge). Reusable for Stage 2.5 SECV tests.
- **`Authority` fields the resolver populates (SECV deps):** `cellar_resolve()` sets `work_uuid`, `provision_id`, `eli`, and `in_force` (new field added to `Authority` in Stage 2). SECV Step 1 = `cellar_resolve`; SECV Step 2 = `cellar_provision_text`. All four tool functions in `crucible/grounding/cellar/tools.py`.
- **Architect:** `PlaybookArchitect` in `crucible/agents/architect.py`. Two modes: `infer(case_description)` and `normalize(raw_playbook_text)`. Infer = research (cellar_search + perplexity) → synthesise (model) → resolve (cellar_resolve sets work_uuid + in_force). Scripted FakeModelClient JSON response pattern verified in Architect contract tests.
- **Coach grounding:** `CoachAgent.__init__` now accepts optional `graph_store`. `_enrich_authorities()` resolves playbook authorities + falls back to `cellar_search(stronger_move_text, top_k=3)` if list is empty.
- **Perplexity client:** `RealPerplexityClient` uses `https://api.perplexity.ai/chat/completions` with model `sonar-pro` + `return_citations=True`. `FakePerplexityClient` returns empty list (tests). `make_perplexity_client(api_key)` factory returns fake when key is None.
- **Neo4j docker:** `docker-compose.yml` uses `neo4j:5.24-community` with APOC + GDS plugins; creds from `.env` (`NEO4J_USER`/`NEO4J_PASSWORD`); `make neo4j` brings it up. Bolt=7687, Browser=7474.
- **`neo4j` package:** Added to `pyproject.toml` deps; installed in venv via `pip install neo4j>=5.14.0`. Import is lazy in `neo4j_store.py` and `neo4j_loader.py` so tests never need it.
- **Ingest entrypoint:** `python -m crucible.grounding.cellar.ingest --scenario negotiation [--dump /path/to.nt]`. SPARQL/REST used here only — runtime never touches live endpoint.
- **Runtime counts (prod, post-ingest):** _TBD after first real ingest run_ — update here with node/edge/chunk counts and wall-clock time.

### Stage 2.5 — SECV ✅
- **Module layout:** `crucible/verify/entropy.py` (pure: UnionFind + discrete_semantic_entropy + cluster_by_bidirectional_entailment), `crucible/verify/entailment.py` (EntailmentOracle Protocol + ModelEntailmentOracle), `crucible/verify/secv.py` (6-step `verify_citation`), `crucible/verify/calibration/{examples,eval}.py`.
- **Injection seam:** `entailment_oracle: EntailmentOracle | None` — pass None to get `ModelEntailmentOracle(client, model)`. Tests inject `_AlwaysTrueOracle` / `_ExcludeClaimOracle` (callable-based). Same seam makes live tests trivial.
- **Default θ_high = 0.7** (in `verify_citation` signature). Tuned θ_high on live model TBD — update here after `make secv-eval` run.
- **Achieved AUROC (unit mocked): 1.0** (perfectly discriminating mock). Live AUROC TBD.
- **Entailment-oracle prompt:** strict few-shot in `crucible/verify/entailment.py → _SYSTEM`. 3 examples: (correct processor contract → YES), (processor contract ≠ breach duty → NO), (Directive repealed → YES). Reply parsed as `reply.strip().upper().startswith("YES")`.
- **"contradicts" not implemented** — `_check_support` only returns "supports" | "neutral". Verdict rule maps neutral → "misattributed" which satisfies test assertion `support ∈ {neutral, contradicts}`. Implement "contradicts" detection as future enhancement if needed.
- **Perplexity path:** `celex=None` + `provision_text_override=<snippet>` → skips Step 1, caps `citation_score` at 0.7 (commentary, not black-letter law).
- **Cache key format:** `sha1("{claim}|{celex}|{pinpoint}")` hex string. Pass `cache={}` dict to `verify_citation` to activate.
- **Flash-call budget per citation (M=5):** 5 sampling calls + up to 20 entailment calls (O(M²) pairs × 2 directions) + 2 support checks = ≤ 27 Flash calls. With M=5 and typical clustering into 1-2 groups, budget is ~12 calls in practice.
- **seeded_store fixture** moved from `test_cellar_graph.py` to `tests/conftest.py` so it's shared. `test_cellar_graph.py` dropped the local import of `InMemoryGraphStore` (now it comes from conftest).
- **Calibration set:** `crucible/verify/calibration/examples.py` — 9 examples: 3 correct, 3 misattributed, 2 fabricated, 1 repealed. Real CELEXes used so live Neo4j swap requires no changes.
- **`make secv-eval`:** `python -m crucible.verify.calibration.eval --theta-high 0.7 --M 5`. Prints AUROC + confusion matrix. Run before demo to confirm live AUROC ≥ 0.9 and tune θ_high if needed.

### Stage 3 — Memory + breadth ✅
- **Memory backend shipped:** SQLite (`SQLiteMemoryStore`) behind `MemoryStore` Protocol in `crucible/memory.py`. `InMemoryMemoryStore` for tests. Swap to Vertex Agent Engine Memory Bank by implementing `MemoryStore` and passing it to `CrucibleRunner(memory_store=...)`.
- **Distillation:** `distil(move_events)` in `crucible/memory.py` — deterministic, no model call. Extracts up to 3 weakness strings from worst `conceded_early`, `missed_point`, `overplayed` events in order. `update_profile()` also handles streak, EMA for `weak_vs_persona`, and dedup/capping at 5 weaknesses.
- **TunerDirective schema:** in `crucible/schemas.py`. `DifficultyTuner` in `crucible/agents/tuner.py` — calls model, produces `TunerDirective(target_weakness, aggression_delta, pressure_note)`. `aggression_delta` clamped to `[-0.3, +0.3]`. Pass `tuner_directive=directive.pressure_note` to `runner.start_session()` → injected into Opponent system prompt.
- **Per-scenario rubric weights:**
  - `negotiation.yaml`: outcome=35, must_haves=25, concession_discipline=20, legal_grounding=15, composure=5
  - `hot_seat.yaml`: outcome=20, must_haves=20, legal_grounding=35, concession_discipline=15, composure=10 (citation accuracy is the primary metric)
  - `difficult_client.yaml`: outcome=15, must_haves=30, legal_grounding=25, concession_discipline=20, composure=10 (advice delivery is the primary metric)
- **`scoring.py` change:** `compute_subscores` now uses `_load_weights(playbook.scenario)` (no longer hardcoded to "negotiation"). All tests pass.
- **Persona param tables (fully fleshed out):**
  - `AGGRESSOR`: aggression=0.9, flexibility=0.2, verbosity=0.6 — hard-charging, ultimatums, time pressure
  - `CHARMER`: aggression=0.3, flexibility=0.5, verbosity=0.8 — warmth as distraction, false consensus, flattery
  - `STONEWALLER`: aggression=0.5, flexibility=0.1, verbosity=0.3 — minimal vocabulary, tactical silence, tactical delay
  - `TECHNICIAN`: aggression=0.4, flexibility=0.4, verbosity=0.9 — clause-detail floods, definitional traps, demands chapter-and-verse
  - All personas: resistance is INVARIANT — style only. `test_opponent_resistance.py` green across all 4.
- **Hot Seat mechanic:** "concession ladder" = partner's scepticism level; starts very sceptical, steps down as associate makes legally precise arguments. Same structural resistance gate as negotiation. Fixture: `crucible/scenarios/fixtures/hot_seat.py` — GDPR data retention defence (7-year payroll retention, Art. 5(1)(e) + Art. 6(1)(c) analysis).
- **Difficult Client mechanic:** "ladder" = client's resistance to accepting advice. Starts at "just do it", accepts compliance path only when legal exposure and a concrete route are both presented. Fixture: `crucible/scenarios/fixtures/difficult_client.py` — AI training data repurposing (Art. 5(1)(b) purpose limitation + Art. 35 DPIA + Art. 83(5) fine quantum).
- **`suggest_persona(weak_vs_persona)`** in `crucible/agents/personas.py` — returns persona with highest weakness score; fallback "aggressor" if empty.
- **Coach memory wiring:** `CoachAgent.produce_debrief(user_profile=...)` — if profile has `recurring_weaknesses`, injects "PRIOR COACHING MEMORY" section into prompt and instructs Coach to note recurrence/improvement.
- **Runner wiring:** `CrucibleRunner(memory_store=...)` — after `end_round`, auto-reads profile, passes to Coach, distils+upserts updated profile. `get_user_profile(user_id)` helper for persona auto-suggestion upstream.

### SECV runtime wiring (post-Stage-4)
- **SECV is now wired into the debrief**, not just tests. `crucible/verify/citations.py` is the glue: `extract_user_citations(transcript, playbook)` + `verify_authority(...)` + `verify_debrief_citations(debrief, ...)`. `runner.end_round()` calls it after the Coach, wrapped in try/except so it can never block a round.
- **Source order = CELLAR then Perplexity.** `verify_authority`: CELEX + graph store → `verify_citation` CELLAR path; if that returns `weak` with "no provision text" and Perplexity is live, retry via `provision_text_override`. Non-CELEX authorities (e.g. the shipped BGB ones) go straight to Perplexity (score capped at 0.7 by SECV). Perplexity text is filtered through the `SourcePolicy` allowlist.
- **Graceful gating:** `verify_debrief_citations` no-ops entirely if `store is None and not _has_perplexity(perplexity)` — keeps an unconfigured demo clean (no badges) instead of "unverifiable" everywhere. `_has_perplexity` treats `FakePerplexityClient` as "not available".
- **Runner/server seam:** `CrucibleRunner(..., graph_store, perplexity_client, source_policy)` (all optional, default None). Server `get_runner` builds them: `_build_graph_store` returns None unless Neo4j env is set AND reachable; perplexity via `make_perplexity_client(key)`; policy via `load_source_policy`. Uses `settings.get_entailment_model()` (Flash) for SECV calls.
- **Citation extraction gotcha:** do NOT sentence-split before regex — "Sec.", "Art.", "No." periods break a citation across sentences. Match `_CITATION_RE` over the whole user message; claim context = whole message. Matches playbook authorities by numeric pinpoint signature (`_authority_numbers`); unmatched cites become bare `Authority` objects so misattributed/fabricated cites still get flagged.
- **Schema:** `Debrief.user_citations: list[Authority]` added (each carries `Authority.check`). Frontend `Debrief.tsx` renders `AuthorityChip` with a SECV status dot (verified/weak/misattributed/not found/repealed) on both recommended authorities and a new "Your citations" block.
- **Known limitation:** the shipped `saas_license_negotiation` fixture is BGB-only (no CELEX), so without a Perplexity key SECV degrades to "weak" for it. CELLAR path is fully exercised by the GDPR `dpa_negotiation` fixture + seeded Neo4j. Tests: `tests/test_citation_wiring.py`.

### RL / grounded-estimators layer (THEORY_ADDENDUM.md) ✅
- **All math lives in one pure module: `crucible/rl.py`** — no model calls, no I/O, no numpy (the project pins deps, so the fundamental matrix is solved with a ~25-line pure-Python Gaussian-elimination `_solve`). Fully unit-tested in `tests/test_rl.py` (17 property tests: bounds/monotonicity, turning-point=max-regret, ECE behaviour, posterior shrinkage, ZPD direction).
- **Absorbing-Markov V(s):** `value_function(position, move_events, k=5)`. States −k..+k with absorbing barriers (WIN at +k, LOSS at −k); birth-death step probs `(p_up, p_down)` estimated from the round's actual `position_delta`s (Laplace-smoothed) so a round of concessions values the same standing lower. V is `B=N·R` for transient states, linearly interpolated for fractional position. Barriers pinned: V(−5)=0, V(+5)=1, V(0)≈0.5.
- **Turning point is now CFR-grounded, not heuristic.** `runner.end_round` calls `regret_trajectory(move_events)` (regret_t = max(0, V_before−V_after)) and uses its argmax as `turning_point_turn`, falling back to `find_turning_point` only when there are no events. The coach prose + `_tp_event` (stronger_auths) key off this turn.
- **ECE (epistemic calibration):** `calibration_from_citations(debrief.user_citations)` maps SECV status→correctness (verified=1, weak=0.5, else 0) vs `check.confidence`. Runs AFTER `verify_debrief_citations` so it can read the verified citations. Returns None (not 0) when there are no cited authorities — UI shows "No citations to calibrate".
- **IRT skill θ:** per-rubric Gaussian/Kalman update in logit space (`update_skill`); diffuse prior var=4.0 on round 1, variance shrinks each round. Persisted on `UserProfile.skill_theta_mean` / `skill_theta_var` (new fields). `update_profile` carries them through (new optional kwargs; passing None preserves prior).
- **ZPD matchmaking refines the Tuner (the app-loop RL).** `DifficultyTuner.tune` now blends `recommend_difficulty(skill_scalar(profile.skill_theta_mean))` (target win-rate 0.78) into `aggression_delta = clamp(0.5*llm_delta + zpd_delta)` and appends the ZPD sentence to `pressure_note`. Previously `aggression_delta` was computed but unused; the LLM still names the weakness, the math sets the dial.
- **Schema additions (all backwards-compatible/optional):** `SkillDimension`, `RLInsights` (in schemas.py); `Debrief.rl`, `TurnResult.win_probability`, `UserProfile.skill_theta_{mean,var}`. `RLInsights.skill_scalar` field exists — keep when constructing.
- **UI surfaces (clean, where it fits):** Arena `StandingBar` shows "· N% win" (V(s) from `build_round_context.win_probability`); Debrief right column renders `web/src/RLInsights.tsx` (V-curve with amber max-regret marker, ECE gauge, θ bars w/ deltas, ZPD next-round note); Progress shows a θ panel. Backend `/progress` returns `skill` via `_skill_view` (server app.py).
- **Gotcha:** `runner.py` imports the private `_load_weights` from `scoring.py` to feed `compute_rl_insights` weights — fine intra-package. RL block in `end_round` is wrapped in try/except so it can never block a round (same discipline as SECV).

### Stage 4 — Bonuses & polish
- **Shipped:** Progress view (A), Turning-point replay (B), Adaptive difficulty via Tuner (C). Voice mode (D) skipped.
- **WS handler** now uses `run_turn_full()` → sends full `TurnResult` JSON (reply + move_event + current_position). Test_server updated accordingly: `_override_runner` now calls `start_session()` and provides scripted opponent+adjudicator JSON.
- **Turning-point replay:** `TurningPointExchange` schema (user_message, opponent_reply) added to `Debrief`; extracted from `session.transcript` in `runner.end_round()` by index `[(tp_turn-1)*2 : tp_turn*2]`. Set on `debrief` after Coach produces it. "Film study" toggle in Debrief.tsx shows exchange + overlays `stronger_move`.
- **Progress view:** `SQLiteMemoryStore.get_round_history(user_id)` added; `runner.end_round()` calls `log_round()` (isinstance check on SQLiteMemoryStore). GET `/progress/{user_id}` endpoint returns scores, streak, weak_vs_persona, recurring_weaknesses, history. `Progress.tsx` has MiniSparkline (SVG), PersonaBar, round history table.
- **Adaptive difficulty:** `DifficultyTuner.tune()` called in server `start_round` when `score_to_beat is not None` and user profile exists. Failure silently swallowed so it never blocks a round.
- **SQLiteMemoryStore** initialized as singleton in server/app.py (`get_memory_store()`); passed to runner. `user_id` added to `StartRequest` (default `"demo_user"`).
- **No node_modules** — `web/` deps not installed at dev time; `npm install` + `npm run dev` needed before the UI type-checks or serves.
- **Demo notes:** `/progress/demo_user` returns empty if no rounds logged yet — Progress shows "Complete a round to see your progress." gracefully. "Film study" button only appears if `turning_point_exchange` is non-null (old sessions without exchange stay clean).
