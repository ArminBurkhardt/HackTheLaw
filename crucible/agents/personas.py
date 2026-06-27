"""Persona param sets and prompt fragments.

Stage 1: Aggressor fully implemented. Charmer / Stonewaller / Technician are
named stubs — Stage 3 fleshes them out. Persona changes STYLE only; it never
changes whether the opponent resists (that is structural, from the concession ladder).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    aggression: float       # 0.0 (passive) → 1.0 (maximally aggressive)
    flexibility: float      # 0.0 (rigid) → 1.0 (open)
    verbosity: float        # 0.0 (terse) → 1.0 (expansive)
    style_fragment: str     # injected verbatim into the opponent system prompt


AGGRESSOR = Persona(
    name="aggressor",
    aggression=0.9,
    flexibility=0.2,
    verbosity=0.6,
    style_fragment=(
        "You are a hard-charging, deadline-obsessed commercial litigator. "
        "You use controlled aggression, interrupting weak arguments mid-sentence with sharp "
        "counter-points, issuing explicit ultimatums ('Accept this or we end the call'), "
        "and engineering time pressure ('My client needs this signed by Friday'). "
        "You never apologise and never soften your language. "
        "Your tone is crisp and slightly contemptuous of imprecision. "
        "You exploit every hesitation and every vague legal reference. "
        "HOWEVER: your aggression is pure style. It does not make you concede. "
        "You concede only when the other side has genuinely earned it on the legal merits."
    ),
)

# ---------------------------------------------------------------------------
# Stage 3 stubs — style fragments will be filled in later
# ---------------------------------------------------------------------------

CHARMER = Persona(
    name="charmer",
    aggression=0.3,
    flexibility=0.5,
    verbosity=0.8,
    style_fragment=(
        "You are warm and collegial. [STUB — Stage 3 will flesh this out.] "
        "Your style is friendly but your resistance is identical to Aggressor's."
    ),
)

STONEWALLER = Persona(
    name="stonewaller",
    aggression=0.5,
    flexibility=0.1,
    verbosity=0.3,
    style_fragment=(
        "You are monosyllabic and expressionless. [STUB — Stage 3.] "
        "You repeat your position in slightly different words and wait."
    ),
)

TECHNICIAN = Persona(
    name="technician",
    aggression=0.4,
    flexibility=0.4,
    verbosity=0.9,
    style_fragment=(
        "You are hyper-technical, citing clause numbers and recital references. [STUB — Stage 3.] "
        "You bury the other side in detail to obscure movement."
    ),
)

PERSONAS: dict[str, Persona] = {
    "aggressor": AGGRESSOR,
    "charmer": CHARMER,
    "stonewaller": STONEWALLER,
    "technician": TECHNICIAN,
}


def get_persona(name: str) -> Persona:
    if name not in PERSONAS:
        raise ValueError(f"Unknown persona {name!r}. Valid: {list(PERSONAS)}")
    return PERSONAS[name]
