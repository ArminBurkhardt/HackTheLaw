# CLAUDE.md — Crucible

> **Crucible** — an adversarial training ground where a junior lawyer practises real legal work against an AI that fights back, then gets coached on exactly what to fix, and goes again to beat their last run.
> *(Name is a placeholder — "trial by fire", not the Arthur Miller play. Rename freely.)*

This file is the single source of truth for building Crucible. Read it fully before writing code. Keep it updated as decisions change.

---

## 1. Mission & non-negotiables

This is **a training ground, not an assistant**. The user *performs*, the AI *resists*, and at the end the user is told *specifically* how they did and can run it again to improve. We are not building a tool that does legal work for the user or that the user supervises. We are building a sparring partner and a coach.

Three hard requirements (these are the bar — everything else is in service of them):

1. **Realistic adversary.** A convincing, multi-turn opponent that argues its side, makes counter-moves, exploits weak reasoning, and **does not fold just because the user sounds confident.**
2. **A standard to measure against.** "Good" is defined concretely per scenario — a structured playbook / model answer — so feedback is grounded, not vibes.
3. **Specific coaching.** At round end: where the user conceded too early, missed a point, or overplayed a weak hand, plus the stronger move a great lawyer would have made.

Everything below exists to make those three things true and repeatable.

---

## 2. Product shape (what the user does)

```
Pick scenario ──► Pick persona ──► (Upload playbook | paste case) ──► Round 1
                                                                        │
        ┌───────────────────────────────────────────────────────────── ▼
        │  Live arena: user vs. AI opponent, turn by turn, under pressure
        │                              │
        ▼                              ▼ (round ends)
   Run it again  ◄──────────  Debrief card: score, score-to-beat,
   (adaptive next round,                 where you conceded/missed/overplayed,
    targets your weak spots)             the stronger move (cited),
                                         the turning-point replay
```

### Scenarios (pick one per round)
- **The Negotiation Table** — negotiate a contract clause-by-clause against opposing counsel that fights for its side. *Reference build: a GDPR Data Processing Agreement (DPA) negotiation — grounds cleanly in CELLAR via Reg (EU) 2016/679.*
- **The Hot Seat** — defend a legal position while an AI partner grills you for the weak point.
- **The Difficult Client** — deliver hard, correct advice to an AI client who doesn't want to hear it and pushes back.

### Two input modes (this is the "standard to measure against")
- **Playbook mode** — the firm supplies a playbook: a case with a determined outcome, must-haves, fallback ladder, walk-away point, model moves. The user is scored against it.
- **Inferred mode** — the user supplies only a case description (open outcome). The system *infers* a playbook by researching the matter (CELLAR + Perplexity) and synthesising the rubric. Optionally seed from "past cases" pasted/uploaded by the firm.

Both modes produce the same internal artifact: a **Playbook object** (§6) that drives the opponent, the scoring, and the coaching.

### Personas (configurable adversary styles)
Layered on the opponent to find what makes the user uncomfortable. Rotatable + user-selectable + auto-suggested:
- **The Aggressor** — pressure, deadlines, ultimatums, interruption.
- **The Charmer** — flattery, false consensus, buries concessions traps in warmth.
- **The Stonewaller** — flat refusal, repetition, withholds information, waits you out.
- **The Technician** — drowns you in clause detail, exploits any imprecision, demands citations.

---

## 3. Tech stack (verified June 2026 — confirm versions at build time)

| Layer | Choice | Notes |
|---|---|---|
| Agent framework | **Google ADK (Python)** | Code-first, multi-agent, native Gemini/Vertex. `pip install google-adk`. Use `LlmAgent`, `SequentialAgent`, `ParallelAgent`, session state + `output_key`, `Runner`. |
| Reasoning model | **Gemini 3.1 Pro** (`gemini-3.1-pro`) | Opponent reasoning, Playbook Architect, Coach. 1M context, integrated grounding, adaptive thinking. *Preview as of Jun 2026 — confirm GA / model string.* |
| Fast model | **Gemini 3 Flash** / **3.5 Flash** | Cheaper/faster opponent turns where latency matters; Adjudicator. Use `thinking_level` to tune. |
| Voice (stretch) | **Gemini Live API native audio** (`gemini-live-2.5-flash-native-audio`, GA) | Speak arguments instead of typing. |
| Persistence / memory | **Vertex AI Agent Engine — Sessions + Memory Bank** (GA) | Cross-session user profile: recurring weaknesses, scores, streak. Falls back to local DB if Agent Engine is overkill for the hackathon. |
| Legal grounding (authoritative) | **EU CELLAR → Neo4j GraphRAG** | Neo4j 5.x (Community + APOC + GDS) holds CELLAR as a structural + lexical graph. `neo4j-graphrag` for the pipeline + retrievers. Native vector index for chunk embeddings. SPARQL/REST only at ingest. See §7.1. |
| Legal grounding (current/context) | **Perplexity Search API** | `pip install perplexity`; `from perplexity import Perplexity`. See §7.2. |
| Citation verification | **Semantic-Entropy Citation Verifier (SECV)** | Graph-grounded discriminative check: is a generated citation actually correct? See §7.3. |
| Embeddings | **`text-embedding` on Vertex** (or self-hosted `bge-m3`) | bge-m3 is multilingual — EU law is multilingual; pick per deploy. Dim must match the Neo4j vector index. |
| Entailment oracle | **Gemini 3 Flash** (NLI-style judge) or a fine-tuned NLI model | Powers SECV semantic clustering + claim-entailment. Low temp, strict prompt. |
| Backend | **FastAPI (Python)** | Wraps the ADK Runner; streams turns over WebSocket/SSE. |
| Frontend | **React + Vite + Tailwind** (or Next.js) | WebSocket client; debrief cards; progress view; voice via Live API. |
| Gamification DB | **Postgres** (or SQLite for hackathon) | Rounds/scores/streaks/leaderboard only. Vectors and the legal graph live in Neo4j, not here. |
| Deploy | **Cloud Run** + Agent Engine | Single region (EU, e.g. `europe-west1`) to keep EU legal data local. |

> **Model strings are moving fast.** Gemini 3.x is in preview on Vertex (rebranded "Gemini Enterprise Agent Platform"). Before coding, run a Model Garden check and pin exact strings in `config.py`. Do **not** hardcode model names in agents — read from config.

---

## 4. High-level architecture (multi-agent, ADK)

Five specialised agents. Separation matters: the **opponent must never break character to give feedback**, and the **scorer must be neutral**, so adjudication and coaching are their own agents.

```
                         ┌────────────────────────┐
   setup (once/round)    │  Playbook Architect     │  in: firm playbook OR case desc
   ───────────────────►  │  (Gemini 3.1 Pro)       │  tools: cellar_search/fetch, perplexity_search
                         │  → builds Playbook obj   │  out: Playbook (user side + opponent side)
                         └───────────┬─────────────┘
                                     │ writes Playbook to session.state
        ┌────────────────────────────┼────────────────────────────────────┐
        │  LIVE LOOP (per user turn, driven by frontend via Runner)        │
        │                            │                                     │
        │   user message ──►  ┌──────▼───────┐   ┌──────────────────┐      │
        │                     │  Opponent     │   │  Adjudicator      │     │
        │                     │  (3.1 Pro /   │   │  (3 Flash, silent)│     │
        │                     │   3 Flash)    │   │  scores each turn │     │
        │                     │  persona +    │   │  vs Playbook →     │     │
        │                     │  opp-side     │   │  MoveEvent[]       │     │
        │                     │  playbook +   │   └────────┬──────────┘     │
        │                     │  concession   │            │ append to       │
        │                     │  ladder       │            │ session.state   │
        │                     └──────┬────────┘            │                 │
        │   opponent reply ◄─────────┘                     │                 │
        └──────────────────────────────────────────────────┼────────────────┘
                                     (round ends)           │
                         ┌───────────────────────┐          │
                         │  Coach (3.1 Pro)        │ ◄────────┘ + transcript + memory
                         │  tools: cellar/pplx     │  out: Debrief (score, turning point,
                         │  → Debrief + citations  │       concede/miss/overplay, stronger move)
                         └───────────┬─────────────┘
                                     │
                         ┌───────────▼─────────────┐
                         │  Difficulty Tuner        │  reads progress + weaknesses from Memory Bank
                         │  (3 Flash)               │  → params for next round (aggression, scaffolding,
                         │  between rounds          │     targeted weak-spot pressure)
                         └─────────────────────────┘
```

### Agent responsibilities

**1. Playbook Architect** — runs once when a scenario starts.
- Playbook mode: parse/normalise the firm's playbook into the `Playbook` schema; derive the *opponent's* side (objectives, BATNA, concession ladder) from it.
- Inferred mode: research the matter — `cellar_search`/`cellar_provision_text` over the Neo4j legal graph for authoritative EU law, `perplexity_search` for current market/commentary — then synthesise both sides' playbooks and a scoring rubric. Capture legal authorities as `{celex, eli, title, pinpoint}` and resolve each against the graph.
- Output: `Playbook` (user side) + `OpponentPlaybook` (hidden) + `Rubric`, written to `session.state["playbook"]`.

**2. Opponent** — runs every turn. *This is the make-or-break agent.* See §5 for the "doesn't fold" mechanism.

**3. Adjudicator** — runs every turn, **silently**, in parallel with (or right after) the opponent. Neutral analyst. Emits a `MoveEvent` per user turn: did they concede? hit/miss a must-have? overplay? what's the position delta? This is what powers the score and the turning-point replay. Keeping it separate from the opponent is what makes scoring trustworthy. **When the user cites law (especially the Hot Seat), the Adjudicator calls SECV (§7.3) to check whether the user's citation actually supports their proposition** — a misattributed citation is a `MoveEvent(classification="overplayed"/"missed_point")` and a hit on the legal-grounding rubric.

**4. Coach** — runs at round end. Consumes transcript + `MoveEvent[]` + `Playbook` + cross-session memory. Produces the `Debrief`: score breakdown, the single biggest concede/miss/overplay, the **turning point**, and the **stronger move** (grounded in the Neo4j legal graph). **Every authority in the stronger move is verified through SECV (§7.3) before it is shown** — only `verified`/`weak`(hedged) citations survive; `misattributed`/`fabricated` ones are dropped or re-retrieved. This is what makes the coaching grounded rather than hand-wavy. The Coach also uses the graph's `REPEALS/AMENDS` edges to warn when a cited provision is no longer in force.

**5. Difficulty Tuner** — runs between rounds. Reads the user's history (scores, which weaknesses recur, which persona they fold to) and outputs the next round's parameters: opponent aggression, how much scaffolding to remove, and **which known weak spot to pressure**. This is the engine behind "remember what the user did badly and leverage it next run."

**Shared service — SECV (Semantic-Entropy Citation Verifier).** Not an ADK agent in the live loop; a graph-grounded verification module (§7.3) called by the Coach and Adjudicator. It answers one discriminative question — *is this generated citation correct?* — and never runs inside an opponent turn (too expensive; see cost control in §7.3).

### Orchestration notes
- **Setup** = `SequentialAgent`(research → synthesise → validate Playbook).
- **Live loop** is interactive and frontend-driven (waits on user input), so it is **not** a pure `LoopAgent`. Each user turn the backend invokes Opponent + Adjudicator via the `Runner`; ADK `session.state` holds the running transcript and `MoveEvent[]`.
- **Round end** = `SequentialAgent`(aggregate moves → score → find turning point → ground stronger-move citations → write Debrief).
- Use `output_key` to pass state between agents; never re-prompt the user for state an agent already has.

---

## 5. The opponent must not fold (core mechanic)

A confident tone is **not** a valid reason to concede. Enforce this structurally, not just by asking nicely in the prompt:

1. **Hidden concession ladder.** `OpponentPlaybook.concession_ladder` is an ordered list of rungs, each with an explicit `unlock_condition` (e.g. *"User offers reciprocal value on liability cap"* or *"User correctly invokes Art. 28(3) GDPR sub-processor obligation"*). The opponent starts at the top rung and may only step down when a condition is genuinely met.
2. **Resistance gate.** Before any concession, the opponent must internally check: *which rung condition did the user actually satisfy, and how?* If it can't name one, it does **not** concede — it pushes back, probes, or restates. Tone, confidence, and politeness never satisfy a condition.
3. **BATNA anchoring.** The opponent knows its walk-away. It will hold or walk rather than cross it, even under pressure.
4. **Persona modulates style, not substance.** Personas change *how* it resists (aggressive vs. charming vs. stonewalling), never *whether* it resists. Aggression/flexibility/verbosity are tunable params; the ladder is invariant.
5. **Exploit weakness actively.** Each turn, the opponent is told to look for the weakest link in the user's last move (unsupported assertion, conceded-too-much, missed leverage) and press it.

> Anti-pattern to avoid: an opponent that mirrors the user's confidence and gives ground to keep the conversation pleasant. Test explicitly against "user bluffs hard with a legally weak argument" — the opponent must call it.

---

## 6. Data models (define in `crucible/schemas.py`, Pydantic)

```python
class Authority(BaseModel):       # a legal citation
    celex: str | None             # e.g. "32016R0679" (GDPR)
    eli: str | None               # ELI URI
    title: str
    pinpoint: str | None          # "Art. 28(3)"
    source: Literal["cellar", "perplexity", "firm_playbook"]
    url: str | None
    work_uuid: str | None         # Neo4j (:Work) cellar_uuid, set on structural resolution
    provision_id: str | None      # Neo4j (:Provision) id for the pinpoint, if resolved
    check: "CitationCheck | None" = None   # filled by SECV (§7.3)

class CitationCheck(BaseModel):    # output of the Semantic-Entropy Citation Verifier
    status: Literal["verified", "weak", "misattributed",
                    "fabricated_identifier", "not_in_force"]
    support: Literal["supports", "neutral", "contradicts"]  # claim-entailment direction
    semantic_entropy: float        # discrete SE over grounded re-derivations
    confidence: float              # 1 - normalised SE  ∈ [0,1]
    citation_score: float          # f(support, confidence) ∈ [0,1], for ranking
    n_clusters: int                # number of distinct meanings sampled
    samples: int                   # M
    note: str                      # human-readable, e.g. "Art. 28(3) governs sub-processors, not the claimed breach-notification duty"

class PlaybookItem(BaseModel):
    id: str
    label: str
    kind: Literal["must_have", "nice_to_have", "trap", "model_move"]
    target: str                   # the desired position / what "good" looks like
    walk_away: str | None         # the line that must not be crossed
    authorities: list[Authority] = []
    weight: float = 1.0

class Playbook(BaseModel):         # the user's side = the standard
    scenario: Literal["negotiation", "hot_seat", "difficult_client"]
    matter_summary: str
    objectives: list[str]
    items: list[PlaybookItem]
    fallback_ladder: list[str]     # ordered acceptable retreats
    walk_away_conditions: list[str]
    authorities: list[Authority]

class ConcessionRung(BaseModel):
    position: str
    unlock_condition: str          # what the user must genuinely do
class OpponentPlaybook(BaseModel): # hidden from user
    objectives: list[str]
    batna: str
    concession_ladder: list[ConcessionRung]

class MoveEvent(BaseModel):         # one per user turn, from Adjudicator
    turn: int
    classification: Literal["good_move","conceded_early","missed_point",
                            "overplayed","held_firm","neutral"]
    refs: list[str]                # PlaybookItem ids touched
    position_delta: float          # -1.0..+1.0  (how much their position improved/worsened)
    note: str                      # one-line, specific

class Debrief(BaseModel):
    score: int                     # 0..100
    subscores: dict[str, int]      # rubric components
    score_to_beat: int | None      # last round
    turning_point_turn: int
    turning_point_explainer: str   # what happened + what should have happened
    stronger_move: str             # the great-lawyer move, grounded
    stronger_move_authorities: list[Authority]
    biggest_concession: MoveEvent | None
    biggest_miss: MoveEvent | None
    biggest_overplay: MoveEvent | None
    persona_note: str              # how they fared vs this persona

class UserProfile(BaseModel):       # persisted in Memory Bank
    recurring_weaknesses: list[str] # e.g. "concedes price before securing must-haves"
    weak_vs_persona: dict[str, float]
    scores: list[int]
    streak: int
```

### Scoring rubric (per scenario — define concrete weights)
Negotiation example, 0–100:
- **Outcome vs. target zone** (35) — landed inside target, above walk-away.
- **Must-haves protected** (25) — checklist, binary per item.
- **Concession discipline** (20) — conceded only for reciprocal value, not too early.
- **Legal grounding** (15) — citations correct and on-point.
- **Composure under persona** (5).

Hot Seat and Difficult Client get their own weightings (defence robustness / killer-counter handling / citation accuracy; and held-the-line on correct advice / relationship management / documented risk). Store rubrics in `crucible/scenarios/*.yaml`.

### Turning point detection
The turn with the largest negative `position_delta`, OR the highest-`weight` missed opportunity. The Coach rewinds to that exact exchange and shows the model move.

---

## 7. Grounding integrations

### 7.1 CELLAR → Neo4j GraphRAG (authoritative EU law) — `crucible/grounding/cellar/`

We do **not** treat CELLAR as a flat vector store. We build a **two-layer Neo4j graph** so that (a) citations can be *resolved structurally* (does this CELEX / article actually exist?), (b) the Coach can retrieve the *exact provision text* behind a citation, and (c) the Coach can see whether a cited authority has been **repealed/amended** and is therefore stale. This reuses the proven "Poisoned Fruit" GraphRAG ingestion, scoped to the scenario's sub-corpus.

**Stack:** Neo4j 5.x Community + APOC + GDS (Docker), native vector index (5.13+), `neo4j-graphrag` (official) for the build pipeline + retrievers, `lxml` streaming for RDF/FORMEX.

**Layer 1 — metadata graph (structural).** From the local CELLAR legislation dump (RDF/XML, sector 3) + on-demand SPARQL for case-law (sector 6):
```
(:Work {cellar_uuid, celex, eli, title, type, sector, date_document, date_entry, date_end})
(:Work)-[:REPEALS|IMPLICITLY_REPEALS|AMENDS|CORRECTS|REPLACES|OVERRULES]->(:Work)  // group as DESTROYS
(:Work)-[:CITES|BASED_ON|ADOPTS]->(:Work)                                          // dependency
(:Work {sector:"6"})-[:INTERPRETS|OVERRULES]->(:Work)                              // case-law (Phase 2)
```
CDM-predicate → edge mapping and the streaming loader (`apoc.periodic.iterate`, batch 10k) are exactly as in the Poisoned Fruit plan; reuse `mtd_stream.py` + `cdm_mapping.py` + `neo4j_loader.py`. Constraints: unique `(:Work).cellar_uuid`, indexes on `celex`, `date_document`.

**Layer 2 — lexical / RAG graph.** From FORMEX (and CELLAR REST HTML for judgments):
```
(:Work)-[:HAS_PROVISION]->(:Provision {article_no, heading, text, in_force})
(:Provision)-[:HAS_CHUNK]->(:Chunk {text, embedding})
(:Entity)-[:IN_COMMUNITY]->(:Community {summary})   // optional GDS Leiden summaries
```
Vector index:
```cypher
CREATE VECTOR INDEX chunk_vec IF NOT EXISTS FOR (c:Chunk) ON c.embedding
  OPTIONS {indexConfig:{`vector.dimensions`:1024,`vector.similarity_function`:'cosine'}};
```
(Dim 1024 = `bge-m3`; change to match your embedder. If using Vertex `text-embedding`, set its dim.)

**Scoping (hackathon):** ingest only the scenario's sub-corpus. For the DPA/GDPR reference scenario that's GDPR (`32016R0679`) + cited/related acts + their provisions — hundreds of Works, not 58k. Same `--limit`/candidate-scoped code path scales to the full dump later.

**Tools exposed to agents (ADK tools in `crucible/grounding/cellar/tools.py`):**
- `cellar_search(query) -> [Authority + provision snippet]` — `VectorCypherRetriever`: semantic hit on a `:Chunk`, then traverse to its `:Provision`/`:Work` and any `DESTROYS` edges, so results arrive with structural context + in-force status.
- `cellar_resolve(celex, pinpoint) -> Authority` — structural lookup: does the `:Work` and the pinpointed `:Provision` exist? Returns `work_uuid`/`provision_id` or `None`. **This is SECV Step 1 (§7.3).**
- `cellar_provision_text(celex, pinpoint) -> str` — fetch the exact provision text for grounding (SECV Step 2).
- `cellar_in_force(celex) -> bool` — follow `REPEALS/AMENDS` edges to flag stale authorities (the Coach surfaces "you relied on a repealed provision").

SPARQL/REST are used **only at ingest time** (60s timeout, <5 concurrent, `LIMIT`/`OFFSET`, backoff). At runtime the agents touch Neo4j, never the live endpoint.

### 7.2 Perplexity Search API (current context) — `crucible/grounding/perplexity.py`
- `pip install perplexity`; `from perplexity import Perplexity`; key in `PERPLEXITY_API_KEY`. **Server-side only — never expose the key to the client.**
- Core call: `client.search.create(query=..., max_results=5)` → ranked `results[]` with `title, url, snippet, date`.
- Supports **multi-query (up to 5)**, domain allow/deny (up to 20), recency filters. Base URL `https://api.perplexity.ai`; Sonar models are OpenAI-compatible if you want grounded synthesis instead of raw results.
- **Use it for** what the graph can't give: current market-standard clause language, recent regulatory guidance, commentary, anything post-dating the static dump. Persist `{title,url,snippet,date}` as provenance. Perplexity-sourced authorities are **`source="perplexity"` and are NOT structurally resolvable in the graph** → SECV treats them differently (§7.3).

> **Division of labour:** Neo4j/CELLAR = authoritative + structural (what the law *is*, and how acts destroy/depend on each other). Perplexity = current + contextual (what the market/guidance *says now*). The Coach prefers the graph for legal claims; legal claims surfaced from Perplexity are flagged as commentary, not black-letter law.

### 7.3 Semantic-Entropy Citation Verifier (SECV) — `crucible/verify/secv.py`

**The problem it solves.** Structural resolution (§7.1 `cellar_resolve`) tells you a CELEX and an article *exist*. It does **not** tell you whether *"Art. 28(3) GDPR requires breach notification within 72 hours"* is a faithful reading of that article (it isn't — that's Art. 33). LLMs confabulate the *proposition attributed to a real provision*, and that error is invisible to graph resolution alone. SECV is a **discriminative** check — *is this generated citation correct?* — that adapts your semantic-entropy work to the citation-generation setting, grounded in the graph instead of in free-form QA. It separates two axes the original single SE score conflates: **confidence** (entropy) and **correctness** (entailment direction).

**Inputs (per claim↔citation pair an agent emits):** `claim` (the NL legal proposition), `authority` (`{celex, pinpoint}`), and `provision_text` retrieved from Neo4j.

**Pipeline:**

1. **Structural gate (graph oracle).** `cellar_resolve(celex, pinpoint)`. If the `:Work` or pinpointed `:Provision` doesn't exist → `status="fabricated_identifier"`, stop. Also run `cellar_in_force`; if repealed/amended at the pinpoint → `status="not_in_force"` (still report, but flagged). Cheapest tier, catches the grossest hallucinations for free.

2. **Grounded re-derivation sampling (adapted-for-generation).** Prompt the entailment-tier model (Gemini Flash) **M times** (M = 5–10, temperature τ ≈ 0.7) with *only* the retrieved `provision_text`: *"Based solely on this provision, state the legal proposition it establishes regarding {topic}."* This yields M propositions `{g₁…g_M}` that the **authority actually supports** — derived from the text, not from parametric memory. Grounding the sampling in the provision text is what makes this "more robust" than black-box SE: the entropy reflects the *provision's* determinacy, not the model's free-association.

3. **Semantic clustering by bidirectional entailment.** Cluster `{gᵢ}` into meaning classes with the entailment oracle E: `gᵢ, gⱼ` co-cluster iff `E(gᵢ⊨gⱼ) ∧ E(gⱼ⊨gᵢ)`. Yields clusters with frequencies `n₁…n_k` (this is the Kuhn/Farquhar semantic-equivalence step, applied to legal propositions).

4. **Discrete semantic entropy.** `p(Cᵢ)=nᵢ/M`; `SE = −Σ p(Cᵢ) log p(Cᵢ)`; `SE_norm = SE / log M ∈ [0,1]`; `confidence = 1 − SE_norm`. High SE ⇒ the provision yields scattered meanings under sampling ⇒ low-trust grounding (ambiguous provision, or the model can't pin it down). Discrete (frequency-based) SE is used deliberately — Gemini via Vertex is effectively black-box for clean sequence log-probs, and the discrete variant is the robust one.

5. **Claim-entailment direction (correctness).** Take the dominant cluster C\* and test `E(C*⊨claim)` and `E(claim⊨C*)`:
   - C\* entails claim → `support="supports"`.
   - neutral → `support="neutral"`; contradicts → `support="contradicts"`.
   This is the axis structural resolution can't see: a citation can *resolve* yet be *misattributed*.

6. **Verdict.**
   ```
   supports & confidence≥θ_high            → status="verified"
   supports & confidence<θ_high            → status="weak"          (surface with a hedge / downrank)
   neutral|contradicts (any confidence)    → status="misattributed" (drop or re-retrieve)
   citation_score = w·𝟙[supports] · confidence       # ∈[0,1], for ranking
   ```

**Perplexity-sourced authorities** (no graph node): skip Step 1; run Steps 2–6 against the retrieved web snippet text instead of provision text, and cap `citation_score` (commentary, not black-letter law).

**Where it runs (and where it must not):**
- **Coach (debrief):** verify every authority in `stronger_move`; only `verified`/`weak`(hedged) are shown. Turns "here's the better move, trust me" into "here's the better move, and the citation behind it survived a hallucination check."
- **Adjudicator (Hot Seat & any user citation):** verify the *user's* citations. `misattributed` → ding the legal-grounding rubric and show the user exactly which citation didn't hold. This is a high-value coaching signal you cannot get from string-matching.
- **Opponent:** off by default (cost). Config flag `opponent.spot_the_bad_citation` can instead *let* the opponent cite weakly and reward the user for catching it via SECV — a deliberate training mechanic.

**Cost control (mandatory).** SECV is `M + |entailment pairs|` Flash calls per citation. Therefore: run **only at debrief and on user citations**, never inside a live opponent turn; cache by `(sha1(claim), celex, pinpoint)`; pre-fetch provision text from Neo4j in one batched query; M=5 for the hackathon, 10 for the final. Entailment pairwise comparisons are `O(M²)` worst case — use union-find with early-exit and a single batched Flash call per candidate pair-set.

**Calibration & the demo metric.** Hand-label 30–50 `(claim, citation, correct?)` examples from the demo scenarios (include known traps like Art. 28 vs 33 GDPR). Tune `θ_high` and the entailment prompt to maximise separation, and **report AUROC of the SE-based discriminator** — exactly how the semantic-entropy literature evaluates hallucination detection. "Our citation checker catches misattributed law at AUROC 0.9" is a strong, defensible judge-facing claim, and it's the natural bridge to your SAGE work.

```python
def verify_citation(claim: str, celex: str, pinpoint: str | None, *, M=7) -> CitationCheck:
    node = cellar_resolve(celex, pinpoint)
    if node is None:
        return CitationCheck(status="fabricated_identifier", support="neutral",
                             semantic_entropy=0.0, confidence=0.0, citation_score=0.0,
                             n_clusters=0, samples=0, note=f"{celex} {pinpoint} not in graph")
    text = cellar_provision_text(celex, pinpoint)
    gens = [derive_proposition(text, topic_of(claim), temperature=0.7) for _ in range(M)]
    clusters = cluster_by_bidirectional_entailment(gens, oracle=flash_nli)   # union-find
    se = discrete_semantic_entropy(clusters, M)                              # normalised
    support = entailment_direction(dominant(clusters), claim, oracle=flash_nli)
    return decide(node, support, confidence=1 - se, clusters=clusters, M=M)
```

---

## 8. Memory & progress (the "learn from last time" engine)

- **Vertex AI Agent Engine Memory Bank** stores `UserProfile` across sessions: recurring weaknesses, per-persona performance, score history, streak.
- After each Debrief, distil 1–3 durable weakness statements and upsert them (don't store raw transcripts as "memory" — store *lessons*).
- **Next round leverages this two ways:** (a) the **Difficulty Tuner** picks a weak spot to pressure and feeds the Opponent a directive ("probe their tendency to concede price before locking must-haves"); (b) the **Coach** explicitly notes whether a known weakness recurred or improved ("you fixed last round's early-concession problem; new gap is X").
- **Gamification DB** (Postgres/SQLite) holds rounds, scores, streaks, leaderboard for the progress view. Keep this separate from Memory Bank (one is UX state, the other is coaching memory).

> Guardrail: memory must never reduce challenge to flatter the user. We store weaknesses to *target* them, never to soften feedback. Honest, specific coaching is the product.

---

## 9. Repo structure

```
crucible/
  config.py                 # model strings, region, endpoints, flags
  schemas.py                # Pydantic models (§6)
  agents/
    architect.py            # Playbook Architect
    opponent.py             # Opponent + persona loading + concession ladder
    adjudicator.py          # silent per-turn scorer
    coach.py                # debrief + turning point + stronger move
    tuner.py                # adaptive difficulty
    personas.py             # persona param sets + prompt fragments
  grounding/
    cellar/
      mtd_stream.py         # stream CELLAR RDF dump → node/edge rows (reused from Poisoned Fruit)
      cdm_mapping.py        # CDM predicate → graph edge type
      neo4j_loader.py       # constraints + batched MERGE (apoc.periodic.iterate)
      formex_extract.py     # FORMEX → :Provision text
      cellar_sparql.py      # sector-6 case-law harvest (ingest only)
      kg_build.py           # chunk + embed + vector index (neo4j-graphrag)
      retrievers.py         # VectorCypherRetriever + structural retrievers
      tools.py              # ADK tools: cellar_search, cellar_resolve, cellar_provision_text, cellar_in_force
    perplexity.py           # search wrapper (current-context grounding)
  verify/
    secv.py                 # Semantic-Entropy Citation Verifier (§7.3)
    entailment.py           # bidirectional-entailment oracle (Gemini Flash / NLI)
    entropy.py              # discrete semantic entropy + clustering (union-find)
    calibration/            # labelled (claim,citation,correct?) set + AUROC report
  scenarios/
    negotiation.yaml        # rubric weights, system prompts, defaults
    hot_seat.yaml
    difficult_client.yaml
  memory.py                 # Memory Bank read/write + UserProfile distillation
  scoring.py                # rubric aggregation, turning-point detection
  runner.py                 # ADK Runner + session orchestration
docker-compose.yml          # Neo4j 5.x (APOC + GDS), optional self-hosted embedder
server/
  app.py                    # FastAPI; WS endpoint /round/{id}/turn; REST for setup/debrief/progress
  voice.py                  # Gemini Live API bridge (stretch)
web/                        # React + Vite + Tailwind
  src/
    Arena.tsx               # live chat, tension meter
    Debrief.tsx             # score card, concede/miss/overplay, turning-point replay, "Run again"
                            #   citations rendered with SECV status badges (verified/weak/misattributed)
    Progress.tsx            # score trend, streak, per-persona breakdown, weaknesses
    ScenarioPicker.tsx
tests/
  test_opponent_resistance.py   # MUST: opponent doesn't fold to confident-but-weak
  test_secv.py                  # MUST: misattributed citation (Art 28 vs 33 GDPR) flagged; AUROC on label set
  test_scoring.py
  test_cellar_graph.py          # structural resolution + in-force checks against Neo4j
.env.example
README.md
CLAUDE.md                   # this file
```

---

## 10. Build phases (execute in order; ship the slice first)

> Hackathon strategy: get one scenario fully working end-to-end before breadth. A thin vertical slice that *resists, scores, and coaches* beats three half-built scenarios.
>
> **Every phase is TDD (see §11):** the `✅ Done when` line *is* the test. Write it as a failing test first, then build until it's green. Don't advance phases on a red gate.

**Phase 0 — Scaffold**
- Repo, `config.py` (pin model strings via Model Garden check), `.env.example`, FastAPI + React skeleton, ADK Runner hello-world hitting Gemini.
- ✅ Done when: a stub agent round-trips a message through the Runner into the React arena.

**Phase 1 — Vertical slice: Negotiation, Aggressor, playbook mode, text only**
- Hand-author one `Playbook` + `OpponentPlaybook` (DPA negotiation) so we skip inference for now.
- Opponent with concession ladder + Aggressor persona. Adjudicator emitting `MoveEvent`s. Coach producing a `Debrief`.
- Arena UI + Debrief card + "Run it again".
- ✅ Done when: a user can play a multi-turn negotiation, the opponent **refuses to fold to a confident-but-weak argument** (`test_opponent_resistance.py` passes), and gets a specific, turn-anchored debrief with a score.

**Phase 2 — The standard, grounded in the graph**
- Stand up Neo4j (docker-compose, APOC+GDS). Ingest the scenario sub-corpus (GDPR + related) → Layer 1 structural graph + Layer 2 chunks/vector index (`make index-cellar`). Reuse the Poisoned Fruit ingestion modules.
- Wire `cellar_search`/`cellar_resolve`/`cellar_provision_text`/`cellar_in_force` as ADK tools; Perplexity tool for current context. Coach cites real authorities (with in-force status) in `stronger_move`.
- **Inferred mode**: Playbook Architect builds the Playbook from a pasted case description using the graph + Perplexity.
- ✅ Done when: in inferred mode the rubric is generated and the stronger move carries a CELEX/ELI pinpoint that *structurally resolves* against Neo4j and reports in-force status.

**Phase 2.5 — SECV citation verifier — the differentiator**
- Implement `verify/` (sampling → entailment clustering → discrete SE → claim-entailment → verdict). Entailment oracle = Gemini Flash; M=5.
- Hook into Coach (verify `stronger_move` authorities) and Adjudicator (verify user citations in Hot Seat).
- Build the labelled calibration set (incl. the Art. 28 vs 33 GDPR trap); tune `θ_high`; report AUROC.
- ✅ Done when: `test_secv.py` passes — a deliberately misattributed citation is caught as `misattributed`, a correct one as `verified`, and the discriminator clears the AUROC target on the label set. Debrief renders SECV status badges.

**Phase 3 — Memory + adaptivity + breadth**
- Memory Bank wiring; Difficulty Tuner; Coach references prior weaknesses; opponent pressures known weak spots next round.
- Add Hot Seat + Difficult Client scenarios (configs + rubrics). Hot Seat especially leans on SECV (user citations get checked).
- Add remaining personas (Charmer, Stonewaller, Technician) + persona auto-suggestion.
- ✅ Done when: round 2 visibly targets round 1's weakness, and all 3 scenarios + 4 personas are playable.

**Phase 4 — Bonuses & polish (remaining time, pick by ROI)**
- **Progress view** (score-to-beat, streak, per-persona breakdown) — high ROI, do first.
- **Replay the turning point** — likely already have the data; just present it well.
- **Adaptive difficulty ramp** — extend the Tuner.
- **Voice mode** — Gemini Live API; highest wow, highest risk, do last.
- Leaderboard.

> The challenge says pick 1–2 bonuses. Recommended cut for impact: **Progress tracking + Turning-point replay** as locked-in, **Voice mode** as the demo showstopper if time allows.

---

## 11. Conventions & commands

- **Test-driven development is required — non-negotiable.** Write the test first, watch it fail, then write the minimum code to make it pass, then refactor. No production module is written before its test exists. This applies to every phase, and the phase-exit `✅ Done when` criteria are written as the tests that must go green.
  - **Order of work per unit:** failing test → implementation → green → refactor (red/green/refactor). Commit the failing test and the fix together so the diff shows the contract before the code.
  - **The two `MUST` tests gate everything:** `test_opponent_resistance.py` (opponent never folds to confident-but-weak) and `test_secv.py` (misattributed citation caught, AUROC target met) are written *before* their features and block the demo if red.
  - **Testing LLM behaviour (the hard part — do not skip):** deterministic assertions don't work on free-form generation, so test the *contract*, not the wording. Patterns to use:
    - **Structured outputs are unit-testable directly** — Pydantic schemas (`MoveEvent`, `Debrief`, `CitationCheck`) parse-validate; assert on fields (`classification`, `status`, `support`), never on prose.
    - **Behavioural tests use fixed scenarios + scripted user turns** and assert on the *classification* the Adjudicator/SECV emits (e.g. "given this bluff transcript, the opponent's reply does NOT step down the concession ladder").
    - **Stochastic components (SECV sampling, τ≈0.7)** are tested on the *verdict* and on **AUROC over the labelled set**, run with a fixed seed where the SDK allows and a tolerance band otherwise — never on a single SE float.
    - **Mock the boundaries** (Gemini, Perplexity, Neo4j) in unit tests with recorded fixtures; keep a small, opt-in `@pytest.mark.live` suite that hits the real services, run before the demo only.
    - **Graph logic is fully deterministic** — `cellar_resolve`/`cellar_in_force`/scoring aggregation get ordinary exhaustive unit tests against a seeded test Neo4j (or an in-memory stub).
  - **CI gate:** `make test` must be green before merge; the mocked suite runs on every commit, the `live` suite before each demo build. Track coverage but optimise for the two `MUST` tests over raw %.
- **Python** 3.12, `uv` or `poetry`. **Type-check** with pyright; Pydantic everywhere at boundaries.
- **Secrets** in env / GCP Secret Manager. `PERPLEXITY_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=europe-west1`, `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`, `EMBED_MODEL`, `ENTAILMENT_MODEL`. Never ship keys to `web/`.
- **Models read from `config.py`**, never hardcoded in agents.
- **Determinism for tests:** Adjudicator + scoring run at low temperature; resistance tests assert on classification, not exact wording. SECV sampling is intentionally stochastic (τ≈0.7) — `test_secv.py` asserts on the *verdict* and on AUROC over the label set, not on a single SE value.
- Commands (fill in once scaffolded):
  - `make dev` — run FastAPI + Vite together
  - `make neo4j` — bring up Neo4j (APOC+GDS) via docker-compose
  - `make agents` — ADK dev UI for inspecting agents
  - `make test` — pytest, mocked suite (resistance + SECV + scoring must be green before any merge)
  - `make test-live` — opt-in `@pytest.mark.live` suite against real Gemini/Perplexity/Neo4j (pre-demo)
  - `make index-cellar SCENARIO=negotiation` — ingest the scenario sub-corpus into Neo4j (structural + chunks + vector index)
  - `make secv-eval` — run the calibration set, print AUROC + the confusion matrix

---

## 12. Demo script (what we show the judges)

1. Pick **Negotiation Table**, **Aggressor**, upload a DPA playbook. Play 3–4 turns; deliberately make a confident-but-weak argument → **opponent calls it and holds the line.**
2. End round → **Debrief**: score, "you conceded the liability cap on turn 3 before securing the sub-processor must-have", the **stronger move** with a GDPR Art. 28 citation that shows a green **SECV `verified`** badge — and call out that an earlier draft's Art. 33 citation was caught as **`misattributed`** and dropped. This is the "grounded, not hand-wavy" proof.
3. Switch to **Hot Seat**: the user cites Art. 28(3) for a 72-hour breach duty → Adjudicator's SECV flags it `misattributed` and the debrief shows *exactly* which citation didn't hold. (Optional: show the AUROC slide — "the checker catches this class of error at 0.9.")
4. Hit **Run it again** → opponent now **pressures that exact weakness**; user does better; score beats the last run; **streak +1** on the progress view.
5. (If voice shipped) replay one exchange in **voice mode** to show it works spoken, like a real hot seat.

The story: *the user got measurably sharper in two rounds, against genuine resistance, with grounded feedback.* That is the whole brief.

---

## 13. Open decisions / risks

- **Model strings & GA status** — Gemini 3.x is preview on Vertex; confirm exact strings + quota in the target region before Phase 0. Have Gemini 2.5 Pro (`gemini-2.5-pro`, GA until Oct 2026) as fallback.
- **Agent Engine vs. local memory** — Memory Bank is GA but adds setup. If time-pressed, ship Phase 3 with a Postgres-backed `UserProfile` and swap to Memory Bank later; the interface in `memory.py` should hide which.
- **CELLAR / Neo4j** — never query the live SPARQL endpoint inside a turn; all SPARQL/REST happens at ingest. At runtime agents hit Neo4j only. Scope ingestion to the scenario sub-corpus (hundreds of Works), not the 58k dump — GDS Leiden and the vector index stay bounded.
- **SECV is the risk-and-reward item.** It's the differentiator but it has moving parts: the entailment oracle is the weak link (legal entailment is subtle — a wrong NLI verdict flips the whole verdict). Mitigate: keep the oracle prompt strict and few-shot it with legal pairs; validate on the labelled set before trusting it; treat `weak` as "hedge," not "hide." If SECV underperforms by demo time, fall back to structural resolution + in-force only (still better than nothing) and present SE as the stretch result.
- **SECV cost** — M·(1+entailment) Flash calls per citation. Cache aggressively; run only at debrief and on user citations; cap citations-per-debrief. Never in the live loop.
- **Embedding-dim mismatch** — the Neo4j vector index dimension must equal the embedder's output dim. Pin both in `config.py`; a mismatch fails silently as zero recall.
- **Scoring trust** — keep Adjudicator strictly separate from Opponent; if scores feel arbitrary in testing, tighten the rubric YAML and lower temperature before touching prompts.
- **Scope creep** — three scenarios × four personas × two modes × SECV × bonuses is large. The phase order protects a working slice; do not start Phase 2 until `test_opponent_resistance.py` is green, and treat SECV (Phase 2.5) as the one "wow" investment rather than spreading effort across all bonuses.
```
