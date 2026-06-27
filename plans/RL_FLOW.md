# RL Flow — where the grounded estimators run

Implements `THEORY_ADDENDUM.md`. All math is pure/deterministic in [`crucible/rl.py`](../crucible/rl.py);
it is wired into the round lifecycle by [`crucible/runner.py`](../crucible/runner.py) and surfaced in the UI.

## 1. End-to-end flow of the RL model

Two loops run around a round: the **live loop** (a value readout every turn) and the
**debrief loop** (the full estimator bundle + the app-loop curriculum update).

```mermaid
flowchart TD
    subgraph LIVE["🟢 Live loop — every user turn"]
        U["User message"] --> ADJ["Adjudicator<br/>→ MoveEvent (position_delta)"]
        ADJ --> POS["current_position += delta"]
        POS --> VF["rl.value_function(position, move_events)<br/><i>absorbing-Markov V(s) = P(good outcome)</i>"]
        VF --> WP["TurnResult.win_probability<br/>+ RoundContext.win_probability"]
        WP --> METER["Arena tension meter<br/>'· N% win'"]
    end

    LIVE -->|"round ends"| END

    subgraph END["🟥 Debrief loop — runner.end_round()"]
        SUB["scoring.compute_subscores<br/>→ subscores + total score"]
        SUB --> REG["rl.regret_trajectory(move_events)<br/>regret_t = max(0, V_before − V_after)"]
        REG --> TP["turning_point_turn = argmax regret<br/><i>CFR turning point, not a heuristic</i>"]
        TP --> COACH["Coach → Debrief prose<br/>(keys off turning_point_turn)"]
        COACH --> SECV["verify_debrief_citations (SECV)<br/>→ debrief.user_citations"]
        SECV --> RLI["rl.compute_rl_insights(...)"]

        subgraph RLI_BOX["rl.compute_rl_insights"]
            T1["win_prob_trajectory → V-curve"]
            T2["regret_by_turn + max_regret_turn"]
            T3["calibration_from_citations<br/>→ ECE (confidence vs SECV correctness)"]
            T4["update_skill_vector<br/>→ θ posterior + SkillDimension[]"]
            T5["recommend_difficulty(skill_scalar)<br/>→ ZPD aggression_delta + note"]
        end
        RLI --> RLI_BOX

        RLI_BOX --> DBR["Debrief.rl = RLInsights"]
        RLI_BOX --> PROF["UserProfile.skill_theta_{mean,var}<br/>persisted via update_profile"]
    end

    DBR --> DUI["Debrief UI · RLInsights.tsx<br/>V-curve ◆ turning point · ECE gauge · θ bars · ZPD"]
    PROF --> PUI["Progress UI · θ panel"]

    subgraph APP["🔵 App-loop RL — next round (curriculum)"]
        PROF --> TUNE["DifficultyTuner.tune()<br/>aggression_delta = clamp(0.5·llm + zpd)<br/>pressure_note += ZPD sentence"]
        TUNE --> OPP["Opponent system prompt<br/>(harder where you're weak,<br/>win-rate held ≈ 0.78)"]
        OPP -.->|"'Run it again'"| U
    end

    classDef pure fill:#0f2a1a,stroke:#34d399,color:#d1fae5;
    classDef ui fill:#1e1b4b,stroke:#818cf8,color:#e0e7ff;
    class VF,REG,TP,RLI,RLI_BOX,T1,T2,T3,T4,T5,TUNE pure;
    class METER,DUI,PUI ui;
```

**Reading it:** green nodes are the pure `rl.py` estimators; indigo nodes are UI surfaces.
The live loop only computes `V(s)` (cheap, per turn). The expensive bundle runs once at debrief,
*after* SECV so calibration can read verified citations. The app-loop closes the ring: the
updated skill posterior θ drives the next opponent's difficulty.

---

## 2. The (θ, Bayesian) skill update — IRT detail

One Gaussian (Kalman) step per rubric dimension, in logit space. Variance shrinks every round,
so the estimate gets more confident as evidence accumulates. This is the engine behind the
Progress θ panel and the ZPD curriculum.

```mermaid
flowchart TD
    START["Round ends → subscores{outcome, must_haves,<br/>concession_discipline, legal_grounding, composure}"]

    START --> LOOP{"for each rubric<br/>dimension d"}

    LOOP --> OBS["Observation<br/>p_obs = subscore_d / weight_d ∈ [0,1]<br/>y = logit(p_obs)"]
    LOOP --> PRIOR["Prior posterior<br/>mean m₀ = profile.skill_theta_mean[d]<br/>var v₀ = profile.skill_theta_var[d]<br/>(diffuse v₀ = 4.0 on round 1)"]

    OBS --> KALMAN
    PRIOR --> KALMAN

    subgraph KALMAN["update_skill — Kalman step (obs_var r = 1.0)"]
        G["gain = v₀ / (v₀ + r)"]
        M1["m₁ = m₀ + gain·(y − m₀)"]
        V1["v₁ = (1 − gain)·v₀   ⟵ variance shrinks"]
        G --> M1
        G --> V1
    end

    KALMAN --> POST["Posterior (m₁, v₁)"]

    POST --> VIEW["SkillDimension<br/>θ = σ(m₁)  (mastery 0..1)<br/>Δ = σ(m₁) − σ(m₀)<br/>uncertainty = √v₁"]
    POST --> PERSIST["UserProfile.skill_theta_mean[d] = m₁<br/>UserProfile.skill_theta_var[d]  = v₁"]

    PERSIST --> SCALAR["skill_scalar = mean_d σ(m_d)"]
    SCALAR --> ZPD["recommend_difficulty(skill_scalar)<br/>target win-rate σ(θ − b) ≈ 0.78<br/>→ next-round aggression_delta"]

    VIEW --> UI["Debrief θ bars (with Δ arrows)<br/>+ Progress θ panel (± uncertainty)"]
    ZPD --> CUR["DifficultyTuner → Opponent<br/>(zone of proximal development)"]

    FISHER["fisher_information(θ) = a²·P·(1−P)<br/><i>available for CAT next-item selection</i>"] -.->|"informs"| ZPD

    classDef pure fill:#0f2a1a,stroke:#34d399,color:#d1fae5;
    classDef ui fill:#1e1b4b,stroke:#818cf8,color:#e0e7ff;
    class OBS,PRIOR,KALMAN,G,M1,V1,POST,VIEW,SCALAR,ZPD,FISHER pure;
    class UI,CUR ui;
```

**Why Bayesian, not just an average:** the posterior carries *uncertainty* (`v`), so early rounds
move θ a lot and later rounds barely nudge it — and the ZPD matchmaker can be cautious when it's
still unsure. `fisher_information` is the principled "which item teaches most next" signal (CAT);
it's implemented and ready, currently feeding the difficulty heuristic rather than full item selection.
