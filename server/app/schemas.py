from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Persona(StrEnum):
    aggressor = "aggressor"
    charmer = "charmer"
    stonewaller = "stonewaller"
    technician = "technician"


class Difficulty(StrEnum):
    junior = "junior"
    associate = "associate"
    partner = "partner"


class Language(StrEnum):
    english = "en"
    german = "de"


class Role(StrEnum):
    user = "user"
    opponent = "opponent"


class MoveKind(StrEnum):
    good_move = "good_move"
    held_firm = "held_firm"
    conceded_early = "conceded_early"
    missed_point = "missed_point"
    overplayed = "overplayed"
    neutral = "neutral"


class Message(BaseModel):
    role: Role
    text: str


class MoveEvent(BaseModel):
    turn: int
    classification: MoveKind
    points: int
    note: str


class RoundState(BaseModel):
    id: str
    persona: Persona
    difficulty: Difficulty
    language: Language = Language.english
    score: int
    turn: int
    ladder: int
    messages: list[Message]
    events: list[MoveEvent]
    runtime: str = "unconfigured"


class ArgumentReview(BaseModel):
    turn: int
    verdict: str
    quote: str
    feedback: str


class ArgumentOption(BaseModel):
    label: str
    move: str
    rationale: str


class GroundingSource(BaseModel):
    title: str
    url: str | None = None
    snippet: str | None = None


class Debrief(BaseModel):
    score: int
    headline: str
    turning_point: str
    turning_point_turn: int
    turning_point_exchange: list[Message]
    stronger_move: str
    next_run_focus: str
    argument_reviews: list[ArgumentReview] = Field(default_factory=list)


class CreateRoundRequest(BaseModel):
    persona: Persona = Persona.aggressor
    difficulty: Difficulty = Difficulty.associate
    language: Language = Language.english


class TurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class TurnResponse(BaseModel):
    round: RoundState
    event: MoveEvent


class TurnDeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    text: str


class TurnFinalEvent(BaseModel):
    type: Literal["final"] = "final"
    round: RoundState
    event: MoveEvent


class RoundResponse(BaseModel):
    round: RoundState


class DebriefResponse(BaseModel):
    debrief: Debrief


class ArgumentOptionsResponse(BaseModel):
    options: list[ArgumentOption]
    tools_used: list[str] = Field(default_factory=list)
    sources: list[GroundingSource] = Field(default_factory=list)
    grounding_note: str = "Grounding tools are available on demand; they are not forced for every turn."


class LiveAudioRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: Language = Language.english


class ToolAvailability(BaseModel):
    name: str
    configured: bool
    status: str
    detail: str


class ToolsResponse(BaseModel):
    tools: list[ToolAvailability]


class GroundingRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    tools: list[str] = Field(default_factory=lambda: ["perplexity_search", "neo4j_cellar"])


class GroundingJob(BaseModel):
    id: str
    status: str
    query: str
    requested_tools: list[str] = Field(default_factory=lambda: ["perplexity_search", "neo4j_cellar"])
    answer: str | None = None
    sources: list[GroundingSource] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    error: str | None = None


class GroundingJobResponse(BaseModel):
    job: GroundingJob
