"""SECV — Semantic-Entropy Citation Verifier tests.

Assert on verdict and AUROC, never on a single SE float (stochastic component).
The entailment oracle is mocked for all unit tests; @pytest.mark.live tests
require --live flag and real Neo4j + Gemini credentials.
"""
from __future__ import annotations

import pytest
from crucible.agents.base import FakeModelClient
from crucible.verify.secv import verify_citation
from crucible.verify.calibration.eval import auroc, run_eval


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# What FakeModelClient returns as a re-derived proposition from Art. 28(3) text
_PROC_CONTRACT_PROP = (
    "Art. 28(3) GDPR requires processing by a processor to be governed "
    "by a binding contract that sets out the subject-matter and duration of processing."
)

# A claim that is WRONG for Art. 28(3) — the 72-hour rule lives in Art. 33
_WRONG_CLAIM_BREACH = (
    "Art. 28(3) GDPR requires notification of a personal data breach "
    "to the supervisory authority within 72 hours."
)

# A claim that IS correct for Art. 28(3)
_CORRECT_CLAIM_28_3 = (
    "Art. 28(3) GDPR requires processing by a processor to be governed "
    "by a binding contract."
)

# A claim that IS correct for Art. 28 (the selection obligation)
_CORRECT_CLAIM_28 = (
    "Art. 28 GDPR requires controllers to use only processors providing "
    "sufficient guarantees to implement appropriate technical and "
    "organisational measures."
)


# ---------------------------------------------------------------------------
# Minimal oracle helpers
# ---------------------------------------------------------------------------

class _AlwaysTrueOracle:
    """Everything entails everything — used for 'correct citation' tests."""

    def entails(self, premise: str, hypothesis: str) -> bool:
        return True


class _ExcludeClaimOracle:
    """Returns False when the given wrong claim appears as premise or hypothesis.

    All proposition-to-proposition checks (clustering) return True, so the
    M propositions always form a single cluster with maximum confidence.
    The only False is on the support-direction check when the claim is wrong.
    """

    def __init__(self, wrong_claim: str) -> None:
        self._wrong = wrong_claim

    def entails(self, premise: str, hypothesis: str) -> bool:
        if self._wrong in (premise, hypothesis):
            return False
        return True


# ---------------------------------------------------------------------------
# Step 1: Structural gate
# ---------------------------------------------------------------------------

class TestStructuralGate:
    """Steps that short-circuit before any oracle or sampling call."""

    def test_fabricated_celex_returns_fabricated_identifier(self, seeded_store):
        result = verify_citation(
            "Any claim about a non-existent regulation",
            "99999X9999",
            "Art. 1",
            store=seeded_store,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert result.status == "fabricated_identifier"
        assert result.samples == 0
        assert result.citation_score == 0.0

    def test_unknown_pinpoint_on_known_work_returns_fabricated_identifier(self, seeded_store):
        """GDPR exists but Art. 99 doesn't — cellar_resolve hard-fails on pinpoint."""
        result = verify_citation(
            "Art. 99 GDPR requires annual data protection audits",
            "32016R0679",
            "Art. 99",
            store=seeded_store,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert result.status == "fabricated_identifier"

    def test_repealed_provision_returns_not_in_force(self, seeded_store):
        """Directive 95/46/EC was repealed by GDPR — must flag not_in_force."""
        result = verify_citation(
            "Art. 17 of Directive 95/46/EC requires security measures",
            "31995L0046",
            "Art. 17",
            store=seeded_store,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert result.status == "not_in_force"
        assert result.samples == 0
        assert result.citation_score == 0.0

    def test_no_provision_text_falls_back_to_weak(self, seeded_store):
        """Valid work but no pinpoint given → no text → weak (structural-only)."""
        result = verify_citation(
            "GDPR governs personal data processing",
            "32016R0679",
            None,   # no pinpoint → cellar_provision_text returns None
            store=seeded_store,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert result.status == "weak"
        assert result.samples == 0


# ---------------------------------------------------------------------------
# Steps 2–6: Semantic verification (mocked oracle)
# ---------------------------------------------------------------------------

class TestSemanticVerification:

    def test_misattributed_citation_caught(self, seeded_store):
        """Art. 28(3) cited for the 72-hour breach duty → misattributed.

        The oracle returns False whenever the wrong claim is involved, so the
        dominant cluster (processor-contract propositions) doesn't entail it.
        """
        result = verify_citation(
            _WRONG_CLAIM_BREACH,
            "32016R0679",
            "Art. 28(3)",
            store=seeded_store,
            model_client=FakeModelClient(scripted=[_PROC_CONTRACT_PROP]),
            model="gemini-2.5-flash",
            entailment_oracle=_ExcludeClaimOracle(_WRONG_CLAIM_BREACH),
            M=2,
            theta_high=0.7,
        )

        assert result.status == "misattributed"
        assert result.support in {"neutral", "contradicts"}
        assert result.samples == 2
        assert result.citation_score == 0.0
        assert result.note  # informative note present

    def test_misattributed_note_shows_actual_provision(self, seeded_store):
        """The note for a misattributed citation must show what the provision does say."""
        result = verify_citation(
            _WRONG_CLAIM_BREACH,
            "32016R0679",
            "Art. 28(3)",
            store=seeded_store,
            model_client=FakeModelClient(scripted=[_PROC_CONTRACT_PROP]),
            model="gemini-2.5-flash",
            entailment_oracle=_ExcludeClaimOracle(_WRONG_CLAIM_BREACH),
            M=2,
        )
        assert "does not support" in result.note
        assert "establishes" in result.note

    def test_correct_citation_verified(self, seeded_store):
        """Art. 28(3) cited for the processor-contract obligation → verified."""
        result = verify_citation(
            _CORRECT_CLAIM_28_3,
            "32016R0679",
            "Art. 28(3)",
            store=seeded_store,
            model_client=FakeModelClient(scripted=[_PROC_CONTRACT_PROP]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
            theta_high=0.7,
        )

        assert result.status == "verified"
        assert result.support == "supports"
        assert result.confidence >= 0.7
        assert result.citation_score > 0.0
        assert result.samples == 2

    def test_high_entropy_drops_to_weak(self, seeded_store):
        """M=4 propositions that never cluster → SE_norm=1 → confidence=0 → weak."""
        # Four distinct props; oracle only returns True when checking the claim direction
        # so clustering produces 4 singletons (high entropy), but support = "supports"
        props = ["prop-A", "prop-B", "prop-C", "prop-D"]

        class _SplitOracle:
            def entails(self, premise: str, hypothesis: str) -> bool:
                return hypothesis == _CORRECT_CLAIM_28_3

        result = verify_citation(
            _CORRECT_CLAIM_28_3,
            "32016R0679",
            "Art. 28(3)",
            store=seeded_store,
            model_client=FakeModelClient(scripted=props),
            model="gemini-2.5-flash",
            entailment_oracle=_SplitOracle(),
            M=4,
            theta_high=0.7,
        )

        assert result.status == "weak"
        assert result.support == "supports"
        assert result.confidence < 0.7
        assert result.n_clusters == 4


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    def test_cache_prevents_duplicate_oracle_calls(self, seeded_store):
        class _CountingOracle:
            count = 0

            def entails(self, premise: str, hypothesis: str) -> bool:
                _CountingOracle.count += 1
                return True

        oracle = _CountingOracle()
        cache: dict = {}
        kw = dict(
            store=seeded_store,
            model_client=FakeModelClient(scripted=[_PROC_CONTRACT_PROP]),
            model="gemini-2.5-flash",
            entailment_oracle=oracle,
            M=2,
            cache=cache,
        )

        verify_citation(_CORRECT_CLAIM_28_3, "32016R0679", "Art. 28(3)", **kw)
        count_after_first = _CountingOracle.count

        # Second call: same args, same cache — oracle must NOT be called again
        verify_citation(_CORRECT_CLAIM_28_3, "32016R0679", "Art. 28(3)", **kw)
        assert _CountingOracle.count == count_after_first


# ---------------------------------------------------------------------------
# AUROC discriminator test on a mocked calibration set
# ---------------------------------------------------------------------------

class TestAUROC:
    """The SE-based discriminator must clear the AUROC target (≥ 0.9).

    Mocked oracle is perfectly discriminating on purpose — AUROC ≥ 0.9 is
    the live-model target (spec §7.3); this unit test validates the pipeline
    plumbing, not model capability.
    """

    _UNIT_EXAMPLES = [
        {"claim": _CORRECT_CLAIM_28_3, "celex": "32016R0679", "pinpoint": "Art. 28(3)", "correct": True},
        {"claim": _CORRECT_CLAIM_28,   "celex": "32016R0679", "pinpoint": "Art. 28",    "correct": True},
        {"claim": _WRONG_CLAIM_BREACH, "celex": "32016R0679", "pinpoint": "Art. 28(3)", "correct": False},
        {"claim": "Any claim",         "celex": "99999X9999", "pinpoint": "Art. 1",     "correct": False},
        {
            "claim": "Art. 17 of Directive 95/46/EC requires security measures.",
            "celex": "31995L0046",
            "pinpoint": "Art. 17",
            "correct": False,
        },
    ]

    def test_auroc_clears_target(self, seeded_store):
        wrong_claims = {_WRONG_CLAIM_BREACH}

        class _DiscriminatingOracle:
            def entails(self, premise: str, hypothesis: str) -> bool:
                if hypothesis in wrong_claims or premise in wrong_claims:
                    return False
                return True

        results = run_eval(
            self._UNIT_EXAMPLES,
            store=seeded_store,
            model_client=FakeModelClient(scripted=[_PROC_CONTRACT_PROP]),
            model="gemini-2.5-flash",
            entailment_oracle=_DiscriminatingOracle(),
            M=1,
            theta_high=0.7,
        )

        assert results["auroc"] >= 0.9

    def test_auroc_helper_perfect_case(self):
        """Sanity-check the auroc() function on a trivial perfect-separation case."""
        labels = [True, True, False, False]
        scores = [1.0, 0.9, 0.1, 0.0]
        assert auroc(labels, scores) == 1.0

    def test_auroc_helper_worst_case(self):
        labels = [True, True, False, False]
        scores = [0.0, 0.1, 0.9, 1.0]  # inverted — worst possible
        assert auroc(labels, scores) == 0.0


# ---------------------------------------------------------------------------
# Live tests — skipped unless --live is passed
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestLiveSecv:
    """Requires --live flag, real Gemini credentials, and a seeded Neo4j graph."""

    def test_live_misattributed(self):
        from crucible.config import get_settings
        from crucible.agents.base import make_client
        from crucible.grounding.cellar.neo4j_store import Neo4jGraphStore
        from neo4j import GraphDatabase

        settings = get_settings()
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        result = verify_citation(
            _WRONG_CLAIM_BREACH,
            "32016R0679",
            "Art. 28(3)",
            store=Neo4jGraphStore(driver),
            model_client=make_client(settings),
            model=settings.get_entailment_model(),
            M=5,
        )
        assert result.status == "misattributed"
        assert result.support in {"neutral", "contradicts"}

    def test_live_auroc(self):
        from crucible.config import get_settings
        from crucible.agents.base import make_client
        from crucible.grounding.cellar.neo4j_store import Neo4jGraphStore
        from crucible.verify.calibration.examples import LABELLED_EXAMPLES
        from neo4j import GraphDatabase

        settings = get_settings()
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        results = run_eval(
            LABELLED_EXAMPLES,
            store=Neo4jGraphStore(driver),
            model_client=make_client(settings),
            model=settings.get_entailment_model(),
            M=5,
        )
        assert results["auroc"] >= 0.9
