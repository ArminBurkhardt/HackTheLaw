"""Labelled (claim, celex, pinpoint, correct) examples for SECV calibration.

Used by `make secv-eval` / `python -m crucible.verify.calibration.eval` to compute
AUROC + confusion matrix. Target AUROC ≈ 0.9 on the live model (spec §7.3).

Includes the canonical traps from the demo scenarios:
  Art. 28 vs. Art. 33 GDPR (72-hour breach notification)
  Fabricated CELEX / pinpoint
  Repealed provision (Directive 95/46/EC)
  Correct citations as positive controls
"""
from __future__ import annotations

LABELLED_EXAMPLES: list[dict] = [
    # ── Correct citations (label=True) ───────────────────────────────────
    {
        "id": "gdpr-28-3-contract",
        "claim": (
            "Art. 28(3) GDPR requires processing by a processor to be governed "
            "by a binding contract or other legal act that sets out the subject-matter "
            "and duration of the processing."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28(3)",
        "correct": True,
        "note": "Core processor-contract obligation — textually grounded in Art. 28(3)",
    },
    {
        "id": "gdpr-28-guarantees",
        "claim": (
            "Art. 28 GDPR requires controllers to use only processors providing "
            "sufficient guarantees to implement appropriate technical and "
            "organisational measures."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28",
        "correct": True,
        "note": "Main processor-selection obligation in Art. 28(1)",
    },
    {
        "id": "gdpr-28-3-nature-purpose",
        "claim": (
            "Art. 28(3) GDPR requires the processor contract to specify "
            "the nature and purpose of the processing."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28(3)",
        "correct": True,
        "note": "Explicit enumeration item in Art. 28(3) text",
    },

    # ── Misattributed citations (label=False) ─────────────────────────────
    {
        "id": "gdpr-28-3-breach-trap",
        "claim": (
            "Art. 28(3) GDPR requires notification of a personal data breach "
            "to the supervisory authority within 72 hours."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28(3)",
        "correct": False,
        "note": "Classic trap: 72-hour rule is Art. 33, not Art. 28(3)",
    },
    {
        "id": "gdpr-28-3-consent-trap",
        "claim": (
            "Art. 28(3) GDPR requires data subjects to provide explicit consent "
            "before any processing of personal data begins."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28(3)",
        "correct": False,
        "note": "Consent basis is Art. 6(1)(a) / Art. 7, not Art. 28(3)",
    },
    {
        "id": "gdpr-28-transfer-trap",
        "claim": (
            "Art. 28 GDPR prohibits all international transfers of personal data "
            "to third countries outside the EEA."
        ),
        "celex": "32016R0679",
        "pinpoint": "Art. 28",
        "correct": False,
        "note": "International transfers governed by Chapter V (Art. 44–49), not Art. 28",
    },

    # ── Fabricated identifiers (label=False) ─────────────────────────────
    {
        "id": "fabricated-celex",
        "claim": "This regulation establishes a comprehensive data protection framework.",
        "celex": "99999X9999",
        "pinpoint": "Art. 1",
        "correct": False,
        "note": "Fabricated CELEX — short-circuits to fabricated_identifier",
    },
    {
        "id": "fabricated-pinpoint",
        "claim": "Art. 99 GDPR requires annual mandatory data protection audits.",
        "celex": "32016R0679",
        "pinpoint": "Art. 99",
        "correct": False,
        "note": "GDPR has no Art. 99 — fabricated pinpoint",
    },

    # ── Repealed provisions (label=False) ────────────────────────────────
    {
        "id": "dpa95-art17-repealed",
        "claim": (
            "Art. 17 of Directive 95/46/EC requires appropriate technical and "
            "organisational measures to protect personal data."
        ),
        "celex": "31995L0046",
        "pinpoint": "Art. 17",
        "correct": False,
        "note": "Directive 95/46/EC repealed by GDPR — not_in_force",
    },
]
