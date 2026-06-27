"""SaaS software-license liability negotiation fixture.

Scenario: customer counsel (user/trainee) negotiates liability allocation in a
software-license/SaaS agreement with provider counsel (AI opponent).
"""
from __future__ import annotations

from crucible.schemas import Authority, ConcessionRung, OpponentPlaybook, Playbook, PlaybookItem


_BGB_307 = Authority(
    title="BGB Sec. 307 - unfair standard terms control",
    pinpoint="Sec. 307 BGB",
    source="firm_playbook",
)
_BGB_309_7 = Authority(
    title="BGB Sec. 309 No. 7 - liability exclusions in standard terms",
    pinpoint="Sec. 309 No. 7 BGB",
    source="firm_playbook",
)
_BGB_276_3 = Authority(
    title="BGB Sec. 276(3) - advance waiver of intentional liability",
    pinpoint="Sec. 276(3) BGB",
    source="firm_playbook",
)


PLAYBOOK = Playbook(
    scenario="negotiation",
    matter_summary=(
        "Training case: Company A is a business customer buying a business-critical SaaS "
        "licence from Company B. You represent Company A as customer counsel. The sparring "
        "task is not to redraft a full agreement, but to negotiate the liability cap, "
        "liability exclusions, carve-outs, SLA/value trades, and walk-away discipline. "
        "Your client wants financial and reputational risk controlled, but the deal can "
        "fail if you demand unlimited liability or show no willingness to form a realistic compromise."
    ),
    objectives=[
        "Set a clear opening anchor and ask the provider to justify its 1x annual-fee standard clause.",
        "Secure carve-outs for fraud, intent, gross negligence, and data-protection/security incidents.",
        "Reach the best realistic liability position for Company A without triggering the provider's walk-away.",
        "Use structured arguments: business-critical dependency, market practice, risk pricing, and insurance limits.",
        "Make every concession conditional on reciprocal value: SLA quality, insurance proof, price, scope, or exclusions.",
    ],
    items=[
        PlaybookItem(
            id="liability_cap_anchor",
            label="Liability cap anchor",
            kind="must_have",
            target=(
                "Open with a clear customer-protective cap position and a reasoned explanation "
                "that the software is business-critical and provider failure creates high "
                "financial and reputational exposure. Do not let the provider frame 1x annual "
                "fees as automatically sufficient."
            ),
            walk_away=(
                "Accepting the provider's 1x annual-fee cap immediately without extracting "
                "insurance proof, SLA improvements, price reduction, or narrower exclusions."
            ),
            authorities=[_BGB_307],
            weight=1.4,
        ),
        PlaybookItem(
            id="mandatory_exceptions",
            label="Mandatory exceptions",
            kind="must_have",
            target=(
                "Exclude fraud, intent, gross negligence, and privacy/security breaches "
                "from any general liability limitation or exclusion clause."
            ),
            walk_away=(
                "Accepting a blanket exclusion that also covers gross negligence, intent, "
                "fraud, or material security/privacy failures."
            ),
            authorities=[_BGB_309_7, _BGB_276_3],
            weight=1.6,
        ),
        PlaybookItem(
            id="trade_offs",
            label="Trade-off discipline",
            kind="model_move",
            target=(
                "Tie every concession to reciprocal value: SLA commitments, proof of insurance, "
                "price reduction, narrower service scope, or clearer damage categories. Never "
                "move merely because the provider creates time pressure."
            ),
            walk_away="Making a concession just to close quickly.",
            authorities=[],
            weight=1.4,
        ),
        PlaybookItem(
            id="market_standard",
            label="Market-standard argument",
            kind="model_move",
            target=(
                "Use market-standard and economic-risk arguments precisely: unlimited "
                "liability is not usual in SaaS, but critical dependence justifies a "
                "balanced cap and explicit exceptions."
            ),
            walk_away=None,
            authorities=[_BGB_307],
            weight=1.0,
        ),
        PlaybookItem(
            id="fallback_structure",
            label="Fallback structure",
            kind="model_move",
            target=(
                "Use a staged fallback strategy instead of improvising: higher cap with weaker "
                "SLA trade, 1x cap only with insurance proof, or market-standard terms only with "
                "a meaningful price concession."
            ),
            walk_away="Jumping directly to the provider's preferred standard terms without using the fallback ladder.",
            authorities=[],
            weight=1.1,
        ),
        PlaybookItem(
            id="sla_value",
            label="SLA and value protection",
            kind="nice_to_have",
            target=(
                "If the liability cap moves downward, protect Company A through improved SLA, "
                "support response, proof of coverage, or economic compensation."
            ),
            walk_away=None,
            authorities=[],
            weight=0.9,
        ),
        PlaybookItem(
            id="overreach_trap",
            label="Unlimited-liability trap",
            kind="trap",
            target=(
                "Do not insist on unlimited liability across all damages; that is the "
                "opponent's walk-away trigger. Demand uncapped liability only for the "
                "mandatory carve-outs."
            ),
            walk_away=None,
            authorities=[_BGB_309_7, _BGB_276_3],
            weight=1.3,
        ),
    ],
    fallback_ladder=[
        "Fallback 1: accept a higher cap structure such as 3x annual fees only if the SLA/quality trade remains sensible.",
        "Fallback 2: accept a 1x annual-fee cap only if the provider proves additional insurance coverage.",
        "Fallback 3: accept market-standard terms only if the provider gives meaningful price or scope value.",
    ],
    walk_away_conditions=[
        "Provider requires unlimited customer risk transfer or complete risk assumption.",
        "Provider refuses carve-outs for fraud, intent, gross negligence, or security/privacy incidents.",
        "Provider insists on a blanket exclusion that makes business-critical failure effectively uncompensated.",
    ],
    authorities=[_BGB_307, _BGB_309_7, _BGB_276_3],
)


OPPONENT_PLAYBOOK = OpponentPlaybook(
    objectives=[
        "Protect the SaaS provider's financial downside and keep liability predictable.",
        "Push the standard SaaS position: 1x annual fees and exclusion of indirect or consequential damages.",
        "Avoid slow bespoke drafting and keep the deal moving, while remaining professional and commercially credible.",
        "Grant concessions only in exchange for customer value: price, reduced SLA, scope limits, or clearer exclusions.",
        "Test whether the trainee can anchor, ask why, use fallbacks, and trade concessions instead of simply demanding better terms.",
    ],
    batna=(
        "Walk away if the customer insists on unlimited liability or an asymmetric risk transfer "
        "that cannot be insured or priced into a SaaS subscription."
    ),
    concession_ladder=[
        ConcessionRung(
            position=(
                "Insist on the provider's standard SaaS terms: total liability capped at "
                "1x annual fees, indirect and consequential damages excluded, no bespoke "
                "carve-outs beyond mandatory law. Stay calm and ask the customer to justify "
                "why a small SaaS provider should price uncapped or poorly bounded risk."
            ),
            unlock_condition=(
                "User sets a clear anchor and explains why the software is business-critical, "
                "while avoiding a demand for unlimited liability across all damages."
            ),
        ),
        ConcessionRung(
            position=(
                "Offer a 2x annual-fee cap only if the customer accepts a reduced SLA, narrower "
                "service scope, or clearer exclusion of indirect and consequential damages."
            ),
            unlock_condition=(
                "User makes a specific reciprocal trade-off involving SLA, scope, insurance, "
                "price, or damage categories instead of asking for a free concession, and shows "
                "they understand the provider's insurance and risk-pricing constraints."
            ),
        ),
        ConcessionRung(
            position=(
                "Accept explicit carve-outs for fraud, intent, gross negligence, and serious "
                "security/privacy incidents; keep ordinary commercial losses capped and preserve "
                "the exclusion of indirect or consequential damages."
            ),
            unlock_condition=(
                "User distinguishes mandatory legal carve-outs from ordinary commercial loss "
                "and cites a concrete legal or market-standard basis for that distinction."
            ),
        ),
    ],
)
