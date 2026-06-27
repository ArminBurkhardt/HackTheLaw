# mike t-AI-son — Whitepaper

## 1. Shared data model
- Each user turn produces a `MoveEvent`: state features, move features, binary rubric item responses, and a `position_delta` — the shared record that feeds every downstream component.

## 2. Learner model
- The user's skill is a latent vector `θ` (one dim per rubric component), estimated online via a Gaussian posterior updated each round with Laplace approximation.
- Next-round config is chosen to maximise either Fisher information (measure fast) or expected skill gain `|Δθ|` (teach) — blended at `λ≈0.3` toward teaching.

## 3. Opponent rating
- User and difficulty tiers are rated with Glicko-2; the opponent tier is selected so `P(user wins) ≈ 0.75` — the zone of proximal development.

## 4. Scoring & turning point
- Per-move advantage `A(s,a) = Q(s,a) − V(s)` classifies each move; the turn with maximum counterfactual regret is the turning point the Debrief rewinds to.
- Final score is a weighted sum of `MoveEvent` classifications per the scenario rubric, normalised to 0–100.

## 5. Value function (absorbing Markov chain)
- The episode is modelled as an absorbing Markov chain over macro-states; the fundamental matrix `N = (I−Q)⁻¹` gives absorption probabilities `B`, yielding `V(s)` = expected outcome utility from any state.
- Recomputed cheaply each turn; powers the live tension meter and the advantage calculation.

## 6. LLM self-refinement (Vector search + semantic entropy)
- Citations are refined via best-of-N rejection sampling scored by SECV; sample budget scales with semantic entropy of the first draft.
- Semantic entropy serves three roles simultaneously: SECV confidence, self-consistency selector, and adaptive compute trigger.

## 7. Epistemic calibration (novel subscore)
- The overconfidence component of ECE — high asserted confidence against low SECV-verified correctness — is reported as a standalone subscore, operationalising "overplaying a weak hand" with a number.

## 8. Pipeline & compute budget
- SECV never runs in the live turn loop; it runs at round-end (Coach) and on user citations (Hot Seat only). IRT calibration and Glicko updates are offline/nightly.
