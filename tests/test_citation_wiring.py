"""SECV wiring tests — citation extraction + the CELLAR/Perplexity verifier.

These cover the runtime glue that connects SECV (verify_citation) to the
debrief: extracting the authorities a trainee actually cited, and verifying
both those and the coach's recommended authorities. The SECV core itself is
tested in test_secv.py; here we test orchestration and graceful degradation.
"""
from __future__ import annotations

from crucible.agents.base import FakeModelClient
from crucible.grounding.perplexity import PerplexityResult
from crucible.grounding.source_policy import SourcePolicy
from crucible.schemas import Authority, Debrief
from crucible.scenarios.fixtures.saas_license_negotiation import PLAYBOOK
from crucible.verify.citations import (
    extract_user_citations,
    verify_authority,
    verify_debrief_citations,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _AlwaysTrueOracle:
    def entails(self, premise: str, hypothesis: str) -> bool:
        return True


class _FakePerplexity:
    """Returns one allowed result whose snippet is the provision text."""

    def __init__(self, snippet: str, url: str = "https://www.gesetze-im-internet.de/bgb/__307.html") -> None:
        self._snippet = snippet
        self._url = url

    def search(self, query: str, max_results: int = 5) -> list[PerplexityResult]:
        return [PerplexityResult(title="BGB", url=self._url, snippet=self._snippet)]


_BGB_POLICY = SourcePolicy(allowed_domains=("gesetze-im-internet.de",))


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_matches_playbook_bgb_authority(self):
        transcript = [
            {"role": "assistant", "content": "We offer a 1x annual fee cap."},
            {"role": "user", "content": "Under Sec. 307 BGB those standard terms are unfair."},
        ]
        cites = extract_user_citations(transcript, PLAYBOOK)
        assert len(cites) == 1
        auth, claim = cites[0]
        assert "307" in (auth.pinpoint or auth.title)
        assert auth.source == "firm_playbook"  # came from the playbook fixture
        assert "307" in claim

    def test_creates_bare_authority_for_unlisted_gdpr_cite(self):
        transcript = [
            {"role": "user", "content": "Art. 82 GDPR gives my client a damages claim."},
        ]
        cites = extract_user_citations(transcript, PLAYBOOK)
        assert len(cites) == 1
        auth, _claim = cites[0]
        assert auth.celex == "32016R0679"
        assert "82" in (auth.pinpoint or "")

    def test_dedupes_repeated_citation(self):
        transcript = [
            {"role": "user", "content": "Sec. 307 BGB. Again, Sec. 307 BGB applies here."},
        ]
        cites = extract_user_citations(transcript, PLAYBOOK)
        assert len(cites) == 1

    def test_ignores_opponent_and_uncited_numbers(self):
        transcript = [
            {"role": "assistant", "content": "Sec. 307 BGB is irrelevant."},
            {"role": "user", "content": "We have 5 users and a 30 day notice period."},
        ]
        cites = extract_user_citations(transcript, PLAYBOOK)
        assert cites == []


# ---------------------------------------------------------------------------
# verify_authority — source selection
# ---------------------------------------------------------------------------

class TestVerifyAuthority:
    def test_cellar_path_verifies(self, seeded_store):
        auth = Authority(
            title="GDPR Art. 28(3)", celex="32016R0679",
            pinpoint="Art. 28(3)", source="cellar",
        )
        check = verify_authority(
            auth,
            "Art. 28(3) GDPR requires a binding processor contract.",
            store=seeded_store,
            perplexity=None,
            policy=None,
            model_client=FakeModelClient(scripted=["A binding processor contract is required."]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert check.status == "verified"
        assert check.support == "supports"

    def test_perplexity_path_used_when_no_celex(self):
        auth = Authority(title="BGB Sec. 307", pinpoint="Sec. 307 BGB", source="firm_playbook")
        check = verify_authority(
            auth,
            "Sec. 307 BGB controls unfair standard business terms.",
            store=None,
            perplexity=_FakePerplexity("Provisions in standard business terms are ineffective if they unreasonably disadvantage the other party."),
            policy=_BGB_POLICY,
            model_client=FakeModelClient(scripted=["Standard terms that unreasonably disadvantage a party are ineffective."]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert check.status == "verified"
        assert check.citation_score <= 0.7  # Perplexity (non-black-letter) cap

    def test_no_source_degrades_to_weak(self):
        auth = Authority(title="BGB Sec. 307", pinpoint="Sec. 307 BGB", source="firm_playbook")
        check = verify_authority(
            auth,
            "Sec. 307 BGB controls unfair standard business terms.",
            store=None,
            perplexity=None,
            policy=None,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert check.status == "weak"
        assert check.samples == 0


# ---------------------------------------------------------------------------
# verify_debrief_citations — end-to-end glue
# ---------------------------------------------------------------------------

class TestVerifyDebriefCitations:
    def _debrief(self, authorities: list[Authority]) -> Debrief:
        return Debrief(
            score=60, subscores={}, turning_point_turn=1,
            turning_point_explainer="x", stronger_move="Cite Art. 28(3) GDPR.",
            stronger_move_authorities=authorities, persona_note="x",
        )

    def test_populates_checks_on_recommended_and_user_citations(self, seeded_store):
        rec = Authority(title="GDPR Art. 28(3)", celex="32016R0679",
                        pinpoint="Art. 28(3)", source="cellar")
        debrief = self._debrief([rec])
        transcript = [
            {"role": "user", "content": "Art. 28(3) GDPR requires a binding processor contract."},
        ]
        verify_debrief_citations(
            debrief, transcript, PLAYBOOK,
            store=seeded_store,
            perplexity=None,
            policy=None,
            model_client=FakeModelClient(scripted=["A binding processor contract is required."]),
            model="gemini-2.5-flash",
            entailment_oracle=_AlwaysTrueOracle(),
            M=2,
        )
        assert debrief.stronger_move_authorities[0].check is not None
        assert len(debrief.user_citations) == 1
        assert debrief.user_citations[0].check is not None

    def test_skips_entirely_when_no_source_configured(self, seeded_store):
        rec = Authority(title="GDPR Art. 28(3)", celex="32016R0679",
                        pinpoint="Art. 28(3)", source="cellar")
        debrief = self._debrief([rec])
        transcript = [{"role": "user", "content": "Art. 28(3) GDPR matters."}]
        verify_debrief_citations(
            debrief, transcript, PLAYBOOK,
            store=None,
            perplexity=None,
            policy=None,
            model_client=FakeModelClient(scripted=["unused"]),
            model="gemini-2.5-flash",
        )
        assert debrief.stronger_move_authorities[0].check is None
        assert debrief.user_citations == []
