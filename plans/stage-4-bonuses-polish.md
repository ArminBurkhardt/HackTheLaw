# Stage 4 — Bonuses & Polish

**Goal:** add the high-ROI bonuses and tighten the experience for the demo. Pick by ROI; do not spread thin (spec §13 — scope creep is the main risk). Recommended cut: **Progress tracking + Turning-point replay locked in; Voice mode as the showstopper if time allows.**

**Prerequisites:** Stages 0–3 green. The full loop works across scenarios/personas with grounded, verified coaching and adaptivity.

**Estimated size:** remaining time. Order below is by ROI — do them top-down, stop when time runs out.

---

## A. Progress view (do first — high ROI, low risk)

`web/src/Progress.tsx`, backed by the gamification DB (rounds/scores/streaks from Stage 3).
- **Score trend** over rounds with the **score-to-beat** line.
- **Streak** counter.
- **Per-persona breakdown** (which persona the user folds to — same data the auto-suggester uses).
- **Recurring weaknesses** list (from `UserProfile`), with "improved/recurred" history.
- This is where all the longitudinal data the system has been collecting becomes **accessible** (UX north star: nothing hidden forever). Keep the default view clean; details behind expanders.

## B. Replay the turning point (do second — data already exists)

The Debrief already computes `turning_point_turn` + explainer (Stage 1 scoring) and has the full transcript. Present it well:
- A **rewind** UI that jumps to the exact exchange, shows what the user said, what the opponent did, and overlays the **model move** (the Coach's `stronger_move`) at that point with its SECV-verified citation.
- Make it feel like film study. This is mostly presentation of data you already have.

## C. Adaptive difficulty ramp (extend the Tuner)

Extend `crucible/agents/tuner.py`: as the user's score climbs across rounds, progressively raise opponent aggression and **remove scaffolding** (less hand-holding, fewer hints). Show a difficulty indicator so the ramp is legible. Keep the resistance mechanic invariant — difficulty changes pressure, never whether the opponent folds.

## D. Voice mode (do LAST — highest wow, highest risk)

`server/voice.py` — Gemini Live API native audio bridge (`gemini-live-2.5-flash-native-audio`, spec §3). Let the user **speak** arguments instead of typing, especially in Hot Seat (feels like a real grilling). Wire the Arena to stream audio in/out. This is the demo showstopper but the riskiest integration — only start it once A/B are solid, and keep text mode as the guaranteed fallback for the live demo.

## E. Leaderboard (lowest priority)

Simple ranking from the gamification DB. Nice-to-have; ship only if A–D are done and stable.

## Demo-readiness checklist (spec §12)

Before the demo, walk the exact script and confirm each beat works live:
1. Negotiation + Aggressor + uploaded DPA playbook; a confident-but-weak argument → **opponent calls it and holds the line**.
2. Debrief: score + the specific early-concession callout + a `stronger_move` with a **green SECV `verified`** GDPR Art. 28 badge, and an earlier draft's Art. 33 citation shown as caught-and-dropped `misattributed`.
3. Hot Seat: user cites Art. 28(3) for a 72-hour breach duty → SECV flags `misattributed`, debrief shows exactly which citation didn't hold (optional AUROC slide).
4. **Run it again** → opponent pressures that exact weakness; user does better; score beats last run; **streak +1** on Progress.
5. (If voice shipped) replay one exchange spoken.

Run `make test` (mocked) and `make test-live` (real services) before the demo build. Both MUST tests green.

## ✅ Done when

Progress view + turning-point replay are shipped and demo-ready; the full demo script (spec §12) runs end-to-end without manual fixups; voice mode works if time allowed, with text as a guaranteed fallback.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): which bonuses shipped, any Live API/audio gotchas, the final demo run-through notes, and anything that needed a manual workaround during the demo (so it can be fixed properly later).
