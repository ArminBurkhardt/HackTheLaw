# THEORY_ADDENDUM.md — Mathematically Grounded Approaches

> Add-on to `CLAUDE.md`. Captures the formal framing for Crucible: the learning loops, how to define "good" with an open end, grounded scoring + turning-point detection, and principled LLM self-refinement. Nothing here replaces the build plan — it gives the scoring/adaptivity/verification parts a defensible mathematical backbone and a few genuinely novel angles to pitch.

---

## 1. Two learning loops (frame it correctly)

The app is **not** doing RL *on* the user — you can't gradient-update a human. Instead:

- **Human loop (the real one):** the learner is a policy π acting in a partially-observable **extensive-form game** (negotiation / cross-examination / advice). "Getting better" = the human updating their own π across episodes. The app's job is to make *their* RL sample-efficient.
- **App loop (the ML problem):** treat **teaching itself as the RL problem** — the app's action is the next `(scenario × persona × difficulty)`, the state is the learner's latent skill, the reward is their **learning gain**.

The app solves three surrounding problems that make the human's learning efficient: (a) infer the objective — what "good" is; (b) be a worthy opponent; (c) be a good evaluator/teacher.

---

## 2. Modeling the learner (grounds adaptive difficulty + progress tracking)

- **Latent skill vector θ**, one dimension per rubric component (concession discipline, citation accuracy, composure-vs-aggression, …).
- **Multidimensional Item Response Theory (IRT):** per turn-item, `P(success) = σ(a·(θ − b))`; maintain a Bayesian posterior over θ after each round. This *is* the progress-tracking signal.
- **Computerized Adaptive Testing (CAT):**
  - To **measure** skill fast → pick the next item maximizing **Fisher information** `I(θ) = a²·P·(1−P)`.
  - To **teach** → bias toward maximal **learning progress** `|Δθ|`.
- **Opponent strength via TrueSkill/Glicko** (gives uncertainty, not a point estimate). Match-make to hold the win rate in the **zone of proximal development (~0.7–0.85)**. Keeping `P(success)` at a target is the principled version of "ramps up as the user improves."

---

## 3. The open end — defining "good" with no fixed outcome

Three grounded options, in rough order of ambition:

1. **Max-entropy Inverse RL over the firm's past cases.** Treat expert trajectories as samples from a Boltzmann policy `π ∝ exp(Q_R)` and recover the reward `R̂` the firm's lawyers were implicitly optimizing (Ziebart-style MaxEnt IRL). **`R̂` is the playbook-as-reward-function** — this literally turns "infer the firm's playbook from past cases" into a fitted objective, no predetermined outcome required.
2. **Preference-based reward modeling (RLHF without a gold answer).** If absolute "good" is undefinable, define it *relatively*: fit a **Bradley–Terry** model on pairwise comparisons (expert move ≻ novice move, transcript A ≻ B). The learned reward is the open-ended score.
3. **Game-theoretic reference (outcome-free).** Infer both sides' utilities/BATNAs (inverse bargaining), then score against solution concepts:
   - distance from the **Pareto frontier** = joint value destroyed;
   - surplus split vs. the **Nash bargaining** point = did they capture a fair share given their BATNA.
   Lets you say "inefficient agreement, ~X value left on the table" with **zero predetermined target** — only the utility structure.

---

## 4. Grounded scoring, credit assignment & the turning point

- **Performance = counterfactual regret:** `Regret = U(best response to what the opponent actually did) − U(user's trajectory)`. The decision node with **maximal counterfactual regret IS the turning point** — the replay feature falls out of CFR-style math, not a heuristic.
- **Per-move advantage:** `A(s,a) = Q(s,a) − V(s)`. `A < 0` is precisely "conceded too early / overplayed."
- **Wire in existing SAGE work for `V(s)`:**
  - Model the episode as an **absorbing Markov chain** (states with absorbing ends: deal / walk-away / impasse). The fundamental matrix `N = (I − Q)⁻¹` yields absorption probabilities = `P(good outcome | current state)` = a principled **value function** feeding the advantage calc. → **Adjudicator** computes `V(s)` this way each turn.
  - **DF-QuAD / gradual-semantics argument graph** gives `position_delta` as the change in **acceptability of the user's main claim** — i.e. the tension meter, mathematically.

---

## 5. LLM self-refinement (do it the grounded way)

**Load-bearing fact:** pure self-critique (Self-Refine, Reflexion) does **not** reliably improve reasoning — the critic is as miscalibrated as the generator. It only works with an **external/verifiable signal** or a **generation–verification asymmetry**. So:

- **Verifier-guided refinement = SECV as a reward model.** Best-of-N / rejection sampling: generate citation → SECV scores it → resample/re-retrieve if `misattributed` or high-entropy. Verification against the graph is cheaper + more reliable than generation — the asymmetry that makes refinement sound.
- **Test-time search for the opponent's strategy.** Shallow **MCTS / tree-of-thoughts** scored by the opponent's value function (expected negotiation outcome); take the argmax. A genuinely stronger adversary than single-shot sampling.
- **Semantic entropy as a unified signal**, used three ways at once:
  1. **confidence calibration** on citations (SECV);
  2. **self-consistency selector** — keep the semantically dominant reasoning path;
  3. **adaptive compute** — `refinement budget ∝ semantic entropy` (spend extra samples/search depth only on high-SE outputs).

---

## 6. The novel synthesis (the pitch)

Tie it together as one coherent system:

> Model the human as a policy in an **extensive-form legal game**; infer the firm's reward via **max-ent IRL** (solves the open-ended standard); score by **counterfactual regret** against that reward and the opponent's revealed play (**turning point = max-regret node**); run a **learning-progress curriculum** over the structured difficulty space; and gate every AI output through **verifier-grounded refinement** with **semantic entropy** as the confidence-and-compute signal.

### The new, stack-fitting twist — score epistemic calibration
A great lawyer knows when they're on thin ice. **"Overplaying a weak hand" = high asserted confidence + low grounded support.** Quantify it as the **expected calibration error (ECE)** between the user's stated confidence and the **SECV-verified correctness** of their claims. This operationalizes the most judgment-heavy rubric item — and nobody else is doing it.

---

## 7. Where each piece lands in the build

| Concept | Module in `CLAUDE.md` | Notes |
|---|---|---|
| IRT skill vector θ, CAT next-item | Difficulty Tuner + `memory.py` (UserProfile) | θ posterior persists across sessions |
| TrueSkill/Glicko opponent rating + ZPD matchmaking | Difficulty Tuner | target win rate ~0.7–0.85 |
| MaxEnt IRL / Bradley–Terry / bargaining reference | Playbook Architect (inferred mode) | produces the open-ended `Rubric` / reward |
| Counterfactual regret, advantage `A(s,a)` | Adjudicator + `scoring.py` | turning point = max-regret node |
| Absorbing-Markov `V(s) = N=(I−Q)⁻¹` | Adjudicator | reuse SAGE; feeds advantage |
| DF-QuAD acceptability → `position_delta` | Adjudicator | the tension meter |
| Verifier-guided best-of-N, SE-budgeted compute | SECV (`verify/`) + Coach | refinement gated by graph + entropy |
| Epistemic-calibration ECE | new subscore in `Debrief` | confidence vs. SECV-verified correctness |

> Implementation note: most of this is **opt-in sophistication** — ship the heuristic versions first (per the phase plan), then swap in the grounded estimators where they earn their keep. The absorbing-Markov `V(s)`, SECV-as-reward-model, and the calibration ECE are the three highest-ROI upgrades to do first; full IRL is the stretch.
