# Stage 2 — The Standard, Grounded in the Graph (CELLAR → Neo4j + inferred mode)

**Goal:** replace hand-authored authorities with real, structurally-resolvable EU law. Stand up Neo4j with the CELLAR sub-corpus, expose graph tools to agents, add **inferred mode** (Playbook Architect builds the rubric from a pasted case description), and have the Coach cite authorities that *resolve* in the graph and report in-force status.

**Prerequisites:** Stage 1 green. Docker available for Neo4j. Perplexity API key (`PERPLEXITY_API_KEY`). Embedding access (Vertex `text-embedding`, or self-hosted `bge-m3`).

**Estimated size:** ~1.5 days.

---

## 1. Stand up Neo4j

`docker-compose.yml`: Neo4j 5.x Community + **APOC + GDS** plugins, native vector index (5.13+). Expose bolt + http. Set creds via `NEO4J_AUTH`. Add `make neo4j` to bring it up. Pin `NEO4J_URI/USER/PASSWORD` in `.env`.

## 2. Ingest the scenario sub-corpus (NOT the 58k dump)

Scope to the DPA/GDPR reference scenario: GDPR (`32016R0679`) + cited/related acts + their provisions — hundreds of Works (spec §7.1 "Scoping"). Reuse the "Poisoned Fruit" ingestion modules referenced in the spec; create:

```
crucible/grounding/cellar/mtd_stream.py    # stream CELLAR RDF dump (sector 3) → node/edge rows (lxml streaming)
crucible/grounding/cellar/cdm_mapping.py   # CDM predicate → edge type (REPEALS/AMENDS/CITES/... grouped: DESTROYS, dependency)
crucible/grounding/cellar/neo4j_loader.py  # constraints + batched MERGE via apoc.periodic.iterate (batch 10k)
crucible/grounding/cellar/formex_extract.py# FORMEX → :Provision {article_no, heading, text, in_force}
crucible/grounding/cellar/cellar_sparql.py # sector-6 case-law harvest — INGEST ONLY (Phase 2 optional)
crucible/grounding/cellar/kg_build.py      # chunk + embed provisions → :Chunk{embedding}; create vector index (neo4j-graphrag)
crucible/grounding/cellar/retrievers.py    # VectorCypherRetriever + structural retrievers
crucible/grounding/cellar/tools.py         # the four ADK tools below
```

**Graph shape (spec §7.1):**
- Layer 1 (structural): `(:Work {cellar_uuid, celex, eli, title, type, sector, date_*})` with `DESTROYS`-group edges (`REPEALS|IMPLICITLY_REPEALS|AMENDS|CORRECTS|REPLACES|OVERRULES`) and dependency edges (`CITES|BASED_ON|ADOPTS`). Constraints: unique `(:Work).cellar_uuid`; indexes on `celex`, `date_document`.
- Layer 2 (lexical): `(:Work)-[:HAS_PROVISION]->(:Provision)-[:HAS_CHUNK]->(:Chunk {text, embedding})`.
- **Vector index:** `CREATE VECTOR INDEX chunk_vec ... ON c.embedding OPTIONS {indexConfig:{`vector.dimensions`:<DIM>, `vector.similarity_function`:'cosine'}}`. **`<DIM>` must equal the embedder's output dim** (1024 for bge-m3). Mismatch fails silently as zero recall (spec §13) — pin the dim in `config.py` and assert it at index-build time.

`make index-cellar SCENARIO=negotiation` runs the full ingest pipeline.

> **Runtime rule:** SPARQL/REST only at ingest (60s timeout, <5 concurrent, LIMIT/OFFSET, backoff). At runtime agents touch Neo4j **only**, never the live endpoint (spec §7.1, §13).

## 3. The four ADK graph tools (`cellar/tools.py`)

These are the contract the agents and (later) SECV depend on:

- `cellar_search(query) -> [Authority + provision snippet]` — `VectorCypherRetriever`: semantic hit on a `:Chunk`, traverse to its `:Provision`/`:Work` and any `DESTROYS` edges, so results carry structural context + in-force status.
- `cellar_resolve(celex, pinpoint) -> Authority | None` — structural lookup: does the `:Work` and pinpointed `:Provision` exist? Returns `work_uuid`/`provision_id` or `None`. **This is SECV Step 1.**
- `cellar_provision_text(celex, pinpoint) -> str` — exact provision text for grounding. **This is SECV Step 2.**
- `cellar_in_force(celex) -> bool` — follow `REPEALS/AMENDS` edges to flag stale authorities.

## 4. Perplexity tool (`crucible/grounding/perplexity.py`)

`from perplexity import Perplexity`; key from `PERPLEXITY_API_KEY` (**server-side only, never to `web/`**). Core call `client.search.create(query=..., max_results=5)` → `results[]` of `{title,url,snippet,date}`. Supports multi-query (≤5), domain allow/deny, recency. Use it for what the graph can't give: current market-standard clause language, recent guidance, commentary. Persist provenance. Perplexity authorities are `source="perplexity"` and **not** structurally resolvable → flagged as commentary, not black-letter law (spec §7.2). The Coach prefers the graph for legal claims.

## 5. Playbook Architect + inferred mode (`crucible/agents/architect.py`)

Runs once when a scenario starts; a `SequentialAgent`(research → synthesise → validate) (spec §4).
- **Playbook mode:** parse/normalise a firm playbook into the `Playbook` schema; derive the hidden `OpponentPlaybook` (objectives, BATNA, concession ladder) from it. (This formalises what Stage 1 hand-authored.)
- **Inferred mode (new):** from a pasted case description, research via `cellar_search`/`cellar_provision_text` (authoritative) + `perplexity_search` (current), then synthesise both sides' playbooks + a scoring `Rubric`. Capture each authority as `{celex, eli, title, pinpoint}` and **resolve it via `cellar_resolve`** (set `work_uuid`/`provision_id`).
- Output `Playbook` + hidden `OpponentPlaybook` + `Rubric` to `session.state["playbook"]`.

## 6. Wire grounding into the Coach

The Coach's `stronger_move` now cites real authorities pulled from `cellar_search`, each resolved via `cellar_resolve` and checked with `cellar_in_force` (surface "you relied on a repealed provision" via `DESTROYS` edges). SECV verification of these authorities is added in Stage 2.5 — for now, attach resolution + in-force status. Prefer graph authorities for legal claims; mark Perplexity-sourced ones as commentary.

## 7. Frontend additions

- Setup wizard gains a **mode selector**: *Playbook mode* (upload/paste a firm playbook) vs *Inferred mode* (paste a case description; optionally seed with past cases). Both are first-class, richly explained choices (UX north star).
- Coaching citations in the Debrief now render with resolution + in-force status (the SECV badge slot stays, filled in Stage 2.5). Provide a way to expand a citation to see its provision text and CELEX/ELI — all info accessible.

## 8. Tests

### `tests/test_cellar_graph.py`
Deterministic graph logic against a **seeded test Neo4j** (or an in-memory stub) (spec §11): `cellar_resolve` returns a node for a known CELEX+pinpoint and `None` for a fabricated one; `cellar_in_force` correctly follows `REPEALS/AMENDS` edges; `cellar_provision_text` returns the seeded text. These are ordinary exhaustive unit tests — no model calls.

### Architect contract test
With mocked `cellar_*` + `perplexity` tools, the inferred-mode Architect produces a `Playbook` + `Rubric` that parse-validate, and every legal `Authority` it emits has a non-null `work_uuid` (i.e. it resolved). Assert on structure, not prose.

## ✅ Done when

In **inferred mode**, a pasted case description yields a generated rubric, and the Coach's `stronger_move` carries a **CELEX/ELI pinpoint that structurally resolves against Neo4j** and reports in-force status. `tests/test_cellar_graph.py` green. Runtime never hits the live SPARQL endpoint.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): exact embedding model + **its dimension** (and that the vector index dim matches), which CELEX list the sub-corpus actually ingested, ingestion runtime/row counts, any FORMEX/RDF parsing quirks, how the test Neo4j is seeded (fixture location), and the `Authority` fields the resolver populates (so SECV Stage 2.5 can rely on them).
