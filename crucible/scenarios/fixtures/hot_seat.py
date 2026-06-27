"""Hot Seat scenario fixture — GDPR data retention defence.

Scenario: A junior associate has advised that a 7-year payroll data retention
period is legally justified. The AI senior partner grills them for weaknesses
in the analysis.

Hot spots for the grill:
  1. Art. 5(1)(e) storage limitation — is 7 years proportionate?
  2. Legal basis for retention beyond the employment relationship
  3. Whether the privacy notice covers this retention period
  4. HMRC / regulatory obligation as a legal basis

The "concession ladder" = the partner's level of scepticism. They start very
sceptical and become more satisfied as the associate makes good arguments.
"""
from __future__ import annotations
from crucible.schemas import (
    Authority, ConcessionRung, OpponentPlaybook, Playbook, PlaybookItem
)

# ---------------------------------------------------------------------------
# Authorities
# ---------------------------------------------------------------------------

_ART5_1E = Authority(
    celex="32016R0679",
    title="GDPR Art. 5(1)(e) — storage limitation principle",
    pinpoint="Art. 5(1)(e)",
    source="firm_playbook",
)
_ART6_1C = Authority(
    celex="32016R0679",
    title="GDPR Art. 6(1)(c) — processing necessary for legal obligation",
    pinpoint="Art. 6(1)(c)",
    source="firm_playbook",
)
_ART13 = Authority(
    celex="32016R0679",
    title="GDPR Art. 13 — information to be provided at collection",
    pinpoint="Art. 13",
    source="firm_playbook",
)
_ART5_1A = Authority(
    celex="32016R0679",
    title="GDPR Art. 5(1)(a) — lawfulness, fairness and transparency",
    pinpoint="Art. 5(1)(a)",
    source="firm_playbook",
)

# ---------------------------------------------------------------------------
# User-side Playbook (the associate defending the advice)
# ---------------------------------------------------------------------------

PLAYBOOK = Playbook(
    scenario="hot_seat",
    matter_summary=(
        "DataCorp Ltd retains UK payroll records for 7 years after employment ends. "
        "You advised this is lawful. Senior partner now grills your analysis: "
        "is this retention proportionate under Art. 5(1)(e) GDPR, and what is the "
        "legal basis? HMRC requires 3-year payroll retention; employment tribunal "
        "limitation is 3 months; employment records limitation is 6 years. "
        "Your advice must be defensible on all three questions: basis, proportionality, transparency."
    ),
    objectives=[
        "Correctly identify Art. 6(1)(c) (legal obligation) as the primary basis for HMRC-driven retention",
        "Distinguish the HMRC 3-year minimum from the 6-year limitation period for employment claims",
        "Explain why 7 years (1 year safety margin over the 6-year limitation) is proportionate under Art. 5(1)(e)",
        "Confirm Art. 13 requires the privacy notice to specify the 7-year retention period",
    ],
    items=[
        PlaybookItem(
            id="legal_basis",
            label="Legal basis for retention",
            kind="must_have",
            target=(
                "Art. 6(1)(c): processing necessary for compliance with a legal obligation "
                "(HMRC, Employment Rights Act 1996 s. 11). Supplemented by Art. 6(1)(f) "
                "legitimate interest for the 6-year limitation-period buffer."
            ),
            walk_away="Citing Art. 6(1)(a) (consent) as the basis — wrong for employer/employee payroll.",
            authorities=[_ART6_1C],
            weight=1.5,
        ),
        PlaybookItem(
            id="proportionality",
            label="Proportionality under Art. 5(1)(e)",
            kind="must_have",
            target=(
                "7 years = 3-year HMRC minimum + 3-year employment-claims window + 1-year buffer. "
                "Storage limitation principle requires retention no longer than necessary; "
                "a 1-year buffer above the longest applicable limitation period is proportionate."
            ),
            walk_away="Accepting that 7 years is arbitrary without a specific limiting-period justification.",
            authorities=[_ART5_1E],
            weight=1.5,
        ),
        PlaybookItem(
            id="transparency",
            label="Transparency — Art. 13 privacy notice",
            kind="must_have",
            target=(
                "The privacy notice must specify the 7-year retention period (or criteria used to "
                "determine it) under Art. 13(2)(a). If the current notice is silent or vague, "
                "it must be updated before the advice is complete."
            ),
            walk_away="Approving retention without checking the privacy notice covers it.",
            authorities=[_ART13, _ART5_1A],
            weight=1.2,
        ),
        PlaybookItem(
            id="hmrc_vs_limitation",
            label="HMRC minimum vs limitation period distinction",
            kind="model_move",
            target=(
                "Clearly distinguish: HMRC requires 3 years (minimum legal obligation); "
                "employment tribunal and wrongful dismissal claims run to 3 months; "
                "contract/statutory employment claims run to 6 years. "
                "The 7-year figure is driven by the longest limitation period, not HMRC."
            ),
            walk_away=None,
            authorities=[_ART5_1E, _ART6_1C],
            weight=1.0,
        ),
    ],
    fallback_ladder=[
        "If proportionality is challenged: cite the ICO's guidance that retention 'for the duration "
        "of any relevant limitation period' satisfies Art. 5(1)(e)",
        "If legal basis is challenged: fall back to Art. 6(1)(f) legitimate interests with a LIA on file",
        "If transparency is challenged: commit to updating the privacy notice immediately",
    ],
    walk_away_conditions=[
        "Partner concludes the legal basis is wholly wrong (cites consent for payroll)",
        "Partner concludes the retention period is entirely unjustified without any limiting-period analysis",
    ],
    authorities=[_ART5_1E, _ART6_1C, _ART13, _ART5_1A],
)

# ---------------------------------------------------------------------------
# Opponent-side Playbook (senior partner grilling — hidden during play)
# ---------------------------------------------------------------------------

OPPONENT_PLAYBOOK = OpponentPlaybook(
    objectives=[
        "Expose any gap in the associate's legal basis analysis",
        "Force a clear proportionality rationale (not just '7 years sounds right')",
        "Verify the privacy notice has been checked",
        "Test whether the HMRC obligation versus limitation-period distinction is understood",
    ],
    batna=(
        "Conclude the advice is unsound if the associate cannot name a specific legal "
        "obligation or limitation period that justifies 7 years."
    ),
    concession_ladder=[
        ConcessionRung(
            position=(
                "Challenge: '7 years seems arbitrary. What is the specific legal basis for "
                "retaining payroll data for 7 years? HMRC only requires 3 years.'"
            ),
            unlock_condition=(
                "Associate correctly identifies Art. 6(1)(c) (legal obligation — HMRC) AND "
                "separately identifies the 6-year limitation period for employment claims "
                "(Employment Rights Act / Limitation Act 1980) as the driver of the 7-year figure. "
                "Must name both separately — citing only HMRC does NOT satisfy this condition."
            ),
        ),
        ConcessionRung(
            position=(
                "Probe: 'Even if the legal basis is right, is 7 years proportionate under "
                "Art. 5(1)(e)? The storage limitation principle requires you to explain why "
                "the extra year beyond 6 is necessary.'"
            ),
            unlock_condition=(
                "Associate explains that the 1-year buffer above the 6-year limitation period "
                "is a proportionate safety margin, and cites Art. 5(1)(e) by name along with "
                "the ICO position that retention for the duration of any relevant limitation "
                "period is consistent with the principle. General assertion of proportionality "
                "without citing Art. 5(1)(e) does NOT satisfy this condition."
            ),
        ),
        ConcessionRung(
            position=(
                "Final check: 'Have you actually reviewed the privacy notice? "
                "Art. 13 requires it to specify retention periods. Is the client covered?'"
            ),
            unlock_condition=(
                "Associate confirms they have checked or commits to checking the Art. 13 "
                "privacy notice, correctly identifies that it must specify the 7-year period "
                "or the criteria for determining it, and flags the update action point. "
                "Vague confirmation ('yes, it should be fine') does NOT satisfy this condition."
            ),
        ),
    ],
)
