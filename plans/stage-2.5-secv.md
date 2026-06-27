# Stage 2.5 — SECV: Semantic-Entropy Citation Verifier (the differentiator)

**Goal:** answer one discriminative question — *is this generated citation actually correct?* — for both the Coach's `stronger_move` authorities and the user's own citations. This is the project's "wow." It catches the error structural resolution can't: a citation that *resolves* (the article exists) but is *misattributed* (the proposition isn't what the article says — e.g. "Art. 28(3) GDPR requires 72-hour breach notification" → that's Art. 33).

**Prerequisites:** Stage 2 green — specifically `cellar_resolve`, `cellar_provision_text`, `cellar_in_force` working against Neo4j, and a working Gemini Flash client for the entailment oracle.

**Estimated size:** ~1 day. Highest risk/reward (spec §13) — the entailment oracle is the weak link.

---

## 1. Modules to build (`crucible/verify/`)

```
crucible/verify/secv.py         # orchestrates the 6-step pipeline → CitationCheck
crucible/verify/entailment.py   # bidirectional-entailment oracle (Gemini Flash, strict few-shot prompt)
crucible/verify/entropy.py      # discrete semantic entropy + union-find clustering
crucible/verify/calibration/    # labelled (claim, citation, correct?) set + AUROC report script
```

Output is the `CitationCheck` schema (already defined in Stage 0, spec §6): `status`, `support`, `semantic_entropy`, `confidence`, `citation_score`, `n_clusters`, `samples`, `note`.

## 2. The pipeline (spec §7.3) — `verify_citation(claim, celex, pinpoint, *, M=5)`

1. **Structural gate.** `cellar_resolve(celex, pinpoint)`. If the Work/Provision doesn't exist → `status="fabricated_identifier"`, stop (free, catches gross hallucinations). Run `cellar_in_force`; if repealed/amended at the pinpoint → `status="not_in_force"` (report, flagged).
2. **Grounded re-derivation sampling.** Prompt the entailment-tier model **M times** (M=5 hackathon, 10 final) at τ≈0.7 with *only* the retrieved `provision_text`: *"Based solely on this provision, state the legal proposition it establishes regarding {topic}."* Yields `{g₁…g_M}` — propositions the authority **actually supports**, derived from text not parametric memory. Grounding in provision text is what makes this robust vs black-box SE.
3. **Semantic clustering by bidirectional entailment.** `gᵢ,gⱼ` co-cluster iff `E(gᵢ⊨gⱼ) ∧ E(gⱼ⊨gᵢ)`. Use **union-find with early-exit** and a single batched Flash call per candidate pair-set (O(M²) worst case — control it).
4. **Discrete semantic entropy.** `p(Cᵢ)=nᵢ/M`; `SE=−Σ p log p`; `SE_norm=SE/log M ∈[0,1]`; `confidence=1−SE_norm`. Use the **discrete (frequency-based)** variant deliberately — Gemini via Vertex is black-box for clean sequence log-probs.
5. **Claim-entailment direction (correctness).** Dominant cluster C\*; test `E(C*⊨claim)` & `E(claim⊨C*)` → `support` ∈ {supports, neutral, contradicts}. **This is the axis structural resolution can't see.**
6. **Verdict.**
   ```
   supports & confidence≥θ_high          → "verified"
   supports & confidence<θ_high          → "weak"          (surface hedged / downrank)
   neutral|contradicts (any confidence)  → "misattributed" (drop or re-retrieve)
   citation_score = w·𝟙[supports]·confidence
   ```

**Perplexity-sourced authorities** (no graph node): skip Step 1; run Steps 2–6 against the web snippet text; **cap `citation_score`** (commentary, not black-letter law).

## 3. Where it runs — and where it must NOT (spec §7.3, §13)

- **Coach (debrief):** verify every authority in `stronger_move`. Only `verified` / `weak`(hedged) survive into the shown debrief; `misattributed` / `fabricated_identifier` are dropped or re-retrieved.
- **Adjudicator (Hot Seat & any user citation):** verify the *user's* citations. `misattributed` → ding the legal-grounding rubric and show exactly which citation didn't hold. (Hook the no-op left in Stage 1's Adjudicator.)
- **Opponent: OFF by default** (cost). Optional config flag `opponent.spot_the_bad_citation` lets the opponent cite weakly so the user can catch it via SECV — a deliberate training mechanic.

## 4. Cost control (mandatory — spec §7.3)

SECV is `M + |entailment pairs|` Flash calls per citation. Therefore:
- Run **only at debrief and on user citations** — never inside a live opponent turn.
- **Cache** by `(sha1(claim), celex, pinpoint)`.
- Pre-fetch provision text from Neo4j in one **batched** query.
- M=5 hackathon, 10 final. Union-find + early-exit + single batched pair-set call.
- Cap citations-per-debrief.

## 5. Calibration + the demo metric (spec §7.3)

Hand-label **30–50** `(claim, citation, correct?)` examples drawn from the demo scenarios, **including known traps** (Art. 28 vs 33 GDPR; a fabricated CELEX; a repealed provision; a correct citation). Store in `crucible/verify/calibration/`. Tune `θ_high` and the entailment prompt to maximise separation. `make secv-eval` runs the set and prints **AUROC + confusion matrix**. Target AUROC ≈ 0.9 — this is the judge-facing claim.

## 6. Frontend

The Debrief renders **SECV status badges** on every citation: `verified` (green) / `weak` (amber, hedged) / `misattributed` (red, with the `note` explaining *why* — e.g. "Art. 28(3) governs sub-processors, not breach notification"). The `note` is the coaching payload — make it readable, not buried. Keep the SE/entropy internals behind an expander (progressive disclosure) but **accessible** (UX north star). In Hot Seat, when a user's citation is flagged, show it inline in the debrief at the turn it occurred.

## 7. Test — `tests/test_secv.py` — MUST (write FIRST, gates the demo)

Stochastic component → assert on **verdict and AUROC, never a single SE float** (spec §11):
- A deliberately **misattributed** citation (Art. 28(3) → 72-hour breach duty) is caught as `status="misattributed"` with `support` ∈ {neutral, contradicts}.
- A **correct** citation is `status="verified"` (`support="supports"`, confidence ≥ θ_high).
- A **fabricated** CELEX/pinpoint short-circuits to `fabricated_identifier` at Step 1.
- A **repealed** provision flags `not_in_force`.
- The SE-based discriminator **clears the AUROC target** on the labelled set.
- Mock the entailment oracle with recorded fixtures for unit speed; keep a `@pytest.mark.live` variant. Use a fixed seed where the SDK allows and a tolerance band otherwise.

## Fallback (spec §13)

If SECV underperforms by demo time, fall back to **structural resolution + in-force only** (Stage 2's capability) — still better than nothing — and present semantic entropy as the stretch result. Treat `weak` as "hedge," not "hide." Keep the entailment oracle prompt strict and few-shot it with legal pairs.

## ✅ Done when

`tests/test_secv.py` is green: a deliberately misattributed citation is caught as `misattributed`, a correct one as `verified`, fabricated/repealed are flagged, and the discriminator clears the AUROC target on the label set. The Debrief renders SECV status badges with readable notes.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): the tuned `θ_high`, the achieved AUROC + confusion matrix, the exact entailment-oracle prompt that worked (and failure modes seen), the calibration-set location/size, cache key format, and any Flash-call budget numbers per debrief.
