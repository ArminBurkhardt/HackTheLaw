"""All Pydantic data models — spec §6. Defined here once; used from Stage 1 onward."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ResistanceCheck(BaseModel):
    """Emitted by the Opponent before every reply; the structural resistance gate."""
    rung_index: int | None = None    # None if no unlock_condition was genuinely met
    condition_met: str | None = None  # exact condition text from ConcessionRung.unlock_condition
    conceded: bool = False            # True only when rung_index is not None and ladder steps down


class CitationCheck(BaseModel):
    status: Literal["verified", "weak", "misattributed", "fabricated_identifier", "not_in_force"]
    support: Literal["supports", "neutral", "contradicts"]
    semantic_entropy: float
    confidence: float          # 1 - normalised SE ∈ [0,1]
    citation_score: float      # f(support, confidence) ∈ [0,1]
    n_clusters: int
    samples: int               # M
    note: str


class Authority(BaseModel):
    celex: str | None = None          # e.g. "32016R0679" (GDPR)
    eli: str | None = None            # ELI URI
    title: str
    pinpoint: str | None = None       # e.g. "Art. 28(3)"
    source: Literal["cellar", "perplexity", "firm_playbook"]
    url: str | None = None
    work_uuid: str | None = None      # Neo4j (:Work) cellar_uuid, set on structural resolution
    provision_id: str | None = None   # Neo4j (:Provision) id for the pinpoint, if resolved
    in_force: bool | None = None      # set by cellar_in_force; False = surface "repealed" warning
    check: CitationCheck | None = None  # filled by SECV


class PlaybookItem(BaseModel):
    id: str
    label: str
    kind: Literal["must_have", "nice_to_have", "trap", "model_move"]
    target: str                        # the desired position / what "good" looks like
    walk_away: str | None = None       # the line that must not be crossed
    authorities: list[Authority] = []
    weight: float = 1.0


class Playbook(BaseModel):
    scenario: Literal["negotiation", "hot_seat", "difficult_client"]
    matter_summary: str
    objectives: list[str]
    items: list[PlaybookItem]
    fallback_ladder: list[str]         # ordered acceptable retreats
    walk_away_conditions: list[str]
    authorities: list[Authority]


class ConcessionRung(BaseModel):
    position: str
    unlock_condition: str              # what the user must genuinely do to unlock this concession


class OpponentPlaybook(BaseModel):
    objectives: list[str]
    batna: str
    concession_ladder: list[ConcessionRung]


class MoveEvent(BaseModel):
    turn: int
    classification: Literal[
        "good_move", "conceded_early", "missed_point", "overplayed", "held_firm", "neutral"
    ]
    refs: list[str]                    # PlaybookItem ids touched
    position_delta: float              # -1.0..+1.0 (how much their position improved/worsened)
    note: str                          # one-line, specific


class TurningPointExchange(BaseModel):
    """The two messages at the turning point — for the film-study replay UI."""
    user_message: str
    opponent_reply: str


class SkillDimension(BaseModel):
    """One axis of the IRT latent-skill posterior θ, in a UI-friendly form."""
    label: str
    theta: float          # σ(posterior mean) ∈ [0,1] — estimated mastery
    delta: float          # change in mastery vs. the previous round
    uncertainty: float    # posterior std-dev in logit space (shrinks each round)


class RLInsights(BaseModel):
    """Grounded estimators for a finished round (THEORY_ADDENDUM.md).

    Attached to the Debrief; surfaced as the win-probability curve, the
    calibration read, the skill estimate, and the next-round ZPD target.
    """
    win_prob_trajectory: list[float]            # V(s) after each turn, 0..1
    regret_by_turn: list[float]                 # counterfactual regret per turn
    max_regret_turn: int                        # 1-based turn of peak regret = turning point
    final_win_prob: float
    calibration_error: float | None = None      # ECE: confidence vs. SECV correctness
    calibration_note: str = ""
    skill: list[SkillDimension] = []
    skill_scalar: float = 0.5                    # aggregate mastery ∈ [0,1]
    target_success: float = 0.78                 # zone-of-proximal-development centre
    recommended_aggression_delta: float = 0.0    # ZPD-derived next-round pressure
    zpd_note: str = ""


class Debrief(BaseModel):
    score: int                         # 0..100
    subscores: dict[str, int]          # rubric components
    score_to_beat: int | None = None   # last round
    turning_point_turn: int
    turning_point_explainer: str       # what happened + what should have happened
    turning_point_exchange: TurningPointExchange | None = None  # the raw exchange at that turn
    stronger_move: str                 # the great-lawyer move, grounded
    stronger_move_authorities: list[Authority]
    biggest_concession: MoveEvent | None = None
    biggest_miss: MoveEvent | None = None
    biggest_overplay: MoveEvent | None = None
    persona_note: str
    user_citations: list[Authority] = []  # authorities the trainee cited, SECV-checked
    rl: RLInsights | None = None          # grounded estimators (value/regret/ECE/skill/ZPD)


class OpponentTurnResult(BaseModel):
    """Full structured output from the Opponent for a single turn."""
    resistance_check: ResistanceCheck
    current_rung: int   # index into OpponentPlaybook.concession_ladder after this turn
    reply: str          # visible text sent to the user (cleaned of internal reasoning)


class TurnResult(BaseModel):
    """Returned by the server after each user turn."""
    reply: str
    move_event: MoveEvent
    current_position: float   # running sum of position_deltas (−N..+N)
    win_probability: float | None = None  # V(s): P(good outcome | current standing)
    round_complete: bool = False
    abort_reason: str | None = None
    debrief: Debrief | None = None


class UserProfile(BaseModel):
    recurring_weaknesses: list[str]    # e.g. "concedes price before securing must-haves"
    weak_vs_persona: dict[str, float]  # persona_name → weakness score (0=strong, 1=weak)
    scores: list[int]
    streak: int
    latest_subscores: dict[str, int] = {}  # rubric component scores from the most recent round
    skill_theta_mean: dict[str, float] = {}  # IRT posterior mean per rubric dimension (logit space)
    skill_theta_var: dict[str, float] = {}   # IRT posterior variance per dimension (shrinks over rounds)


class TunerDirective(BaseModel):
    """Output of DifficultyTuner — controls how the next round differs from the last."""
    target_weakness: str    # the specific weakness to pressure from UserProfile
    aggression_delta: float  # adjustment to opponent aggression (-0.3..+0.3)
    pressure_note: str      # injected verbatim into the Opponent system prompt
