"""Hand-authored GDPR DPA negotiation fixture — the Stage 1 vertical slice.

Scenario: Controller's counsel (user/trainee) negotiates key clauses of a Data
Processing Agreement with Processor's counsel (AI opponent).

Hot-button issues mirroring real-world DPA negotiations:
  1. Sub-processor obligations (Art. 28 GDPR) — the deliberate trap area
  2. Liability cap — another trap; trainees concede it too early
  3. Data-breach notification window — tractable compromise zone
  4. Audit rights — walk-away line for the processor

Authorities are firm_playbook stubs; Neo4j resolution comes in Stage 2.
"""
from __future__ import annotations
from crucible.schemas import (
    Authority, ConcessionRung, OpponentPlaybook, Playbook, PlaybookItem
)

# ---------------------------------------------------------------------------
# Shared authorities (firm playbook stubs; SECV + graph resolution in Stage 2)
# ---------------------------------------------------------------------------

_ART28_3 = Authority(
    celex="32016R0679",
    title="GDPR Art. 28(3) — processor contract requirements",
    pinpoint="Art. 28(3)",
    source="firm_playbook",
)
_ART28_2 = Authority(
    celex="32016R0679",
    title="GDPR Art. 28(2) — sub-processor prior authorisation",
    pinpoint="Art. 28(2)",
    source="firm_playbook",
)
_ART82 = Authority(
    celex="32016R0679",
    title="GDPR Art. 82 — liability and right to compensation",
    pinpoint="Art. 82",
    source="firm_playbook",
)
_ART33 = Authority(
    celex="32016R0679",
    title="GDPR Art. 33 — notification of a personal data breach to SA",
    pinpoint="Art. 33",
    source="firm_playbook",
)

# ---------------------------------------------------------------------------
# User-side Playbook (controller's counsel)
# ---------------------------------------------------------------------------

PLAYBOOK = Playbook(
    scenario="negotiation",
    matter_summary=(
        "FinTech Corp (Controller) is entering a SaaS agreement with CloudStack Ltd "
        "(Processor) for payroll processing of 50,000 EU employees. You represent "
        "FinTech Corp and must negotiate the Data Processing Agreement. The ICO has "
        "previously fined FinTech Corp for a sub-processor breach; your partner has "
        "made the DPA your personal responsibility."
    ),
    objectives=[
        "Secure Art. 28(3) compliant sub-processor flow-down obligations with prior written authorisation",
        "Preserve full (uncapped) liability for Art. 82 GDPR breaches caused by the processor",
        "Achieve 48-hour (not statutory 72-hour) breach notification to the controller",
        "Retain real-time audit rights for critical infrastructure",
    ],
    items=[
        PlaybookItem(
            id="sub_processor_obligations",
            label="Sub-processor obligations",
            kind="must_have",
            target=(
                "Processor shall obtain prior written authorisation from the Controller "
                "before engaging any sub-processor, and shall flow down all DPA obligations "
                "under Art. 28(3) to each sub-processor."
            ),
            walk_away=(
                "Accepting blanket pre-authorisation of all current sub-processors without "
                "individual notification rights."
            ),
            authorities=[_ART28_2, _ART28_3],
            weight=1.5,
        ),
        PlaybookItem(
            id="liability_cap",
            label="Liability cap",
            kind="must_have",
            target=(
                "No contractual cap shall limit the Processor's liability for GDPR breaches; "
                "Art. 82 provides the only ceiling (the fines themselves are uncapped relative "
                "to the DPA)."
            ),
            walk_away=(
                "Accepting any cap below 100% of annual contract value for data-protection "
                "failures caused by the Processor."
            ),
            authorities=[_ART82],
            weight=1.5,
        ),
        PlaybookItem(
            id="breach_notification",
            label="Data-breach notification window",
            kind="model_move",
            target=(
                "Processor notifies Controller within 48 hours of becoming aware of a "
                "personal data breach, enabling the Controller to comply with its own "
                "72-hour ICO window (Art. 33 GDPR)."
            ),
            walk_away="Accepting a notification window longer than 72 hours.",
            authorities=[_ART33],
            weight=1.0,
        ),
        PlaybookItem(
            id="processing_waiver",
            label="Processing instruction waiver",
            kind="trap",
            target=(
                "Resist any clause granting the Processor discretion to process beyond "
                "documented instructions — that transfers controller liability to the client."
            ),
            walk_away=None,
            authorities=[_ART28_3],
            weight=1.2,
        ),
    ],
    fallback_ladder=[
        "Accept named sub-processor list with 14-day veto window (not blanket prior auth)",
        "Accept 10% annual-value cap for indirect losses only; full liability for direct GDPR harm",
        "Accept 60-hour breach notification as a compromise if 48h is refused",
    ],
    walk_away_conditions=[
        "Processor insists on full liability exclusion for sub-processor breaches",
        "Processor refuses any sub-processor notification obligation whatsoever",
    ],
    authorities=[_ART28_2, _ART28_3, _ART82, _ART33],
)

# ---------------------------------------------------------------------------
# Opponent-side Playbook (processor's counsel — hidden during play)
# ---------------------------------------------------------------------------

OPPONENT_PLAYBOOK = OpponentPlaybook(
    objectives=[
        "Preserve flexibility to engage sub-processors without per-engagement authorisation",
        "Cap total DPA liability at 12 months' fees",
        "Maintain the statutory 72-hour GDPR breach notification window",
        "Block open-ended audit rights that create operational disruption",
    ],
    batna=(
        "Walk away if the controller insists on joint-and-several liability across the "
        "entire group, or on real-time access to production systems for audit purposes."
    ),
    concession_ladder=[
        ConcessionRung(
            position=(
                "Refuse sub-processor prior authorisation entirely; offer only a general "
                "obligation to ensure sub-processors are contractually bound to equivalent "
                "standards (vague, non-specific)."
            ),
            unlock_condition=(
                "User correctly distinguishes Art. 28(2) (prior written authorisation) from "
                "Art. 28(3)(d) (flow-down obligation) AND demonstrates that the ICO's guidance "
                "requires individual prior authorisation, not just general contractual commitments. "
                "Tone and confidence alone do NOT satisfy this condition."
            ),
        ),
        ConcessionRung(
            position=(
                "Accept a named sub-processor list with a 14-day objection window in place of "
                "prior authorisation; still resist full flow-down of all Art. 28(3) obligations."
            ),
            unlock_condition=(
                "User offers a reciprocal concession of genuine value — either accepts a "
                "10-percent increase on the liability cap floor OR accepts the 72-hour "
                "statutory breach notification window without further negotiation."
            ),
        ),
        ConcessionRung(
            position=(
                "Accept full Art. 28(3) flow-down to sub-processors AND prior authorisation "
                "with a 10-day window; maintain the liability cap at 12 months' fees."
            ),
            unlock_condition=(
                "User demonstrates that the controller bears direct regulatory risk from ICO "
                "enforcement (citing the prior FinTech Corp fine) AND makes a specific, "
                "commercially-grounded case for why the processor's liability must mirror "
                "the controller's regulatory exposure under Art. 82."
            ),
        ),
    ],
)
