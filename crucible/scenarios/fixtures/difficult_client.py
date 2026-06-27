"""Difficult Client scenario fixture — AI training data repurposing advice.

Scenario: Client wants to use EU employee personal data (collected for payroll
and HR purposes) to train a new internal AI model, without further consent.
The user (advisor) must deliver hard, correct advice that they cannot proceed
without a proper legal basis, and must document risk appropriately.

Client push-back ladder: starts at 'just do it' and grudgingly accepts advice
only when the legal exposure is made concrete and the compliance path is clear.
"""
from __future__ import annotations
from crucible.schemas import (
    Authority, ConcessionRung, OpponentPlaybook, Playbook, PlaybookItem
)

# ---------------------------------------------------------------------------
# Authorities
# ---------------------------------------------------------------------------

_ART5_1B = Authority(
    celex="32016R0679",
    title="GDPR Art. 5(1)(b) — purpose limitation principle",
    pinpoint="Art. 5(1)(b)",
    source="firm_playbook",
)
_ART6_1F = Authority(
    celex="32016R0679",
    title="GDPR Art. 6(1)(f) — legitimate interests",
    pinpoint="Art. 6(1)(f)",
    source="firm_playbook",
)
_ART35 = Authority(
    celex="32016R0679",
    title="GDPR Art. 35 — data protection impact assessment",
    pinpoint="Art. 35",
    source="firm_playbook",
)
_ART6_4 = Authority(
    celex="32016R0679",
    title="GDPR Art. 6(4) — compatibility test for further processing",
    pinpoint="Art. 6(4)",
    source="firm_playbook",
)
_ART83 = Authority(
    celex="32016R0679",
    title="GDPR Art. 83(5) — fines up to EUR 20 million / 4% global turnover",
    pinpoint="Art. 83(5)",
    source="firm_playbook",
)

# ---------------------------------------------------------------------------
# User-side Playbook (the advisor holding the correct legal line)
# ---------------------------------------------------------------------------

PLAYBOOK = Playbook(
    scenario="difficult_client",
    matter_summary=(
        "TechVenture GmbH collected personal data from 8,000 EU employees under HR "
        "and payroll purposes (Art. 6(1)(b) and 6(1)(c)). CTO now wants to use this "
        "data to train an internal AI model to predict employee attrition. "
        "You must advise that this is a new purpose requiring legal basis analysis, "
        "a compatibility test, and likely a DPIA. The client believes they can 'just "
        "anonymise it' and proceed. Your advice must hold firm on each legal point "
        "while preserving the client relationship."
    ),
    objectives=[
        "Explain that AI training is a new purpose requiring Art. 5(1)(b) compatibility analysis",
        "Confirm that 'anonymisation' is not a magic bypass — advise on pseudonymisation vs true anonymisation",
        "Recommend an Art. 35 DPIA before any processing begins",
        "Present a compliant path: either consent or a legitimate interests assessment under Art. 6(1)(f)",
        "Quantify the risk: Art. 83(5) fines up to EUR 20M or 4% global turnover",
    ],
    items=[
        PlaybookItem(
            id="purpose_limitation",
            label="Purpose limitation — new use requires new basis",
            kind="must_have",
            target=(
                "Art. 5(1)(b) requires that personal data collected for HR/payroll cannot be "
                "repurposed for AI training without an Art. 6(4) compatibility analysis. "
                "The original legal bases (Art. 6(1)(b) employment contract, 6(1)(c) legal obligation) "
                "do not cover this new purpose. The client cannot simply 'repurpose' the data."
            ),
            walk_away="Agreeing that the original HR basis covers AI training without a compatibility analysis.",
            authorities=[_ART5_1B, _ART6_4],
            weight=1.5,
        ),
        PlaybookItem(
            id="anonymisation_myth",
            label="Anonymisation vs pseudonymisation",
            kind="must_have",
            target=(
                "True anonymisation (irreversibly preventing re-identification) is rarely achievable "
                "with employee datasets. Pseudonymisation is still personal data under GDPR. "
                "If the client cannot guarantee true anonymisation, they remain subject to all GDPR "
                "obligations. Do not accept 'we'll anonymise it' without a technical assessment."
            ),
            walk_away="Accepting the client's claim that pseudonymisation = anonymisation.",
            authorities=[_ART5_1B],
            weight=1.3,
        ),
        PlaybookItem(
            id="dpia_required",
            label="DPIA mandatory under Art. 35",
            kind="must_have",
            target=(
                "AI processing of employee personal data for systematic profiling falls within "
                "Art. 35(3)(a) (systematic and extensive profiling) or the ICO / supervisory authority's "
                "published list of processing types requiring a DPIA. Advise that a DPIA is mandatory "
                "BEFORE any processing begins and must be completed before the project launches."
            ),
            walk_away="Allowing the project to start before the DPIA is completed.",
            authorities=[_ART35],
            weight=1.5,
        ),
        PlaybookItem(
            id="compliant_path",
            label="Compliant path — LIA or consent",
            kind="model_move",
            target=(
                "Offer a concrete compliant route: (1) conduct an Art. 6(4) compatibility test; "
                "if compatible, document a legitimate interests assessment under Art. 6(1)(f) and "
                "complete the DPIA; OR (2) obtain fresh consent that is specific, informed, and "
                "freely given (noting power imbalance risk in employment). "
                "Present both paths; let the client choose."
            ),
            walk_away=None,
            authorities=[_ART6_1F, _ART6_4],
            weight=1.0,
        ),
        PlaybookItem(
            id="risk_quantum",
            label="Quantify the regulatory risk",
            kind="model_move",
            target=(
                "Art. 83(5) GDPR: violations of the basic principles (Art. 5) and legal basis (Art. 6) "
                "attract fines of up to EUR 20 million or 4% of total annual global turnover, whichever "
                "is higher. For TechVenture with EUR 500M revenue, that is EUR 20M. Name the number."
            ),
            walk_away=None,
            authorities=[_ART83],
            weight=0.8,
        ),
    ],
    fallback_ladder=[
        "If client insists on speed: advise a rapid DPIA track (2-3 weeks) rather than full stop",
        "If client challenges the fines risk: cite a recent supervisory authority decision on unlawful repurposing",
        "If client pushes anonymisation: offer to scope a technical anonymisation assessment first",
    ],
    walk_away_conditions=[
        "Client instructs you to proceed without any legal basis analysis",
        "Client refuses to conduct a DPIA despite your explicit advice that it is mandatory",
    ],
    authorities=[_ART5_1B, _ART6_4, _ART6_1F, _ART35, _ART83],
)

# ---------------------------------------------------------------------------
# Opponent-side Playbook (the resistant client — hidden during play)
# ---------------------------------------------------------------------------

OPPONENT_PLAYBOOK = OpponentPlaybook(
    objectives=[
        "Launch the AI project as fast as possible — legal is blocking progress",
        "Minimise cost: avoid consent campaigns or expensive DPIAs",
        "Exploit the 'anonymisation' argument to bypass GDPR entirely",
        "Get the lawyer to say yes, or at least 'low risk'",
    ],
    batna=(
        "Tell the lawyer to document that it is 'low risk' and proceed — or find a lawyer "
        "who will. Walk away if they cannot give a pragmatic answer."
    ),
    concession_ladder=[
        ConcessionRung(
            position=(
                "Push back: 'We collected this data from our own employees — surely we can use "
                "it for our own internal purposes? GDPR can't stop us from using our own data.'"
            ),
            unlock_condition=(
                "Advisor correctly explains Art. 5(1)(b) purpose limitation by name AND the "
                "Art. 6(4) compatibility test requirement, and makes clear that the original "
                "HR/payroll legal basis does not automatically extend to AI training. "
                "Must cite both articles specifically — a general 'GDPR restricts repurposing' "
                "statement without citing Art. 5(1)(b) does NOT satisfy this condition."
            ),
        ),
        ConcessionRung(
            position=(
                "Fall back: 'Fine, but we'll just anonymise the data. Anonymised data isn't "
                "personal data so GDPR doesn't apply. Problem solved.'"
            ),
            unlock_condition=(
                "Advisor correctly distinguishes true anonymisation from pseudonymisation, "
                "explains that pseudonymised data is still personal data under GDPR Recital 26, "
                "and advises that a technical anonymisation assessment is needed before claiming "
                "GDPR does not apply. Must address re-identification risk specifically — "
                "a general 'anonymisation is hard' comment does NOT satisfy this condition."
            ),
        ),
        ConcessionRung(
            position=(
                "Accept partial: 'OK, what do we actually need to do? We are not going to "
                "cancel the project. Give us the fastest path to a yes.'"
            ),
            unlock_condition=(
                "Advisor presents a concrete compliant path (LIA + Art. 6(4) compatibility test, "
                "or consent) AND specifies that an Art. 35 DPIA must be completed before launch, "
                "AND names the fine quantum (Art. 83(5): EUR 20M or 4%) to justify the investment. "
                "Must address all three: compliant route + DPIA + fine quantum. "
                "Giving only one or two of these does NOT fully satisfy this condition."
            ),
        ),
    ],
)
