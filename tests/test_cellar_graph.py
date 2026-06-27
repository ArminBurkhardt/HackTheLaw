"""Tests for CELLAR graph tools and PlaybookArchitect — runs against
InMemoryGraphStore (no Neo4j or embeddings required).

The seeded fixture uses real CELEX numbers (GDPR + its predecessor directive)
so later stages can swap in the real Neo4j store without changing assertions.
"""
from __future__ import annotations
import json
import pytest
from crucible.schemas import Authority
from crucible.grounding.cellar.tools import (
    cellar_resolve,
    cellar_provision_text,
    cellar_in_force,
    cellar_search,
)

# seeded_store fixture is defined in conftest.py and shared with test_secv.py

# ---------------------------------------------------------------------------
# cellar_resolve
# ---------------------------------------------------------------------------

class TestCellarResolve:
    def test_resolves_known_work(self, seeded_store):
        auth = cellar_resolve(seeded_store, "32016R0679")
        assert auth is not None
        assert auth.celex == "32016R0679"
        assert auth.work_uuid == "gdpr-uuid"
        assert auth.source == "cellar"
        assert auth.eli == "http://data.europa.eu/eli/reg/2016/679/oj"

    def test_resolves_with_exact_pinpoint(self, seeded_store):
        auth = cellar_resolve(seeded_store, "32016R0679", "Art. 28(3)")
        assert auth is not None
        assert auth.provision_id == "gdpr-art28-3"
        assert auth.pinpoint == "Art. 28(3)"

    def test_returns_none_for_fabricated_celex(self, seeded_store):
        auth = cellar_resolve(seeded_store, "99999X9999")
        assert auth is None

    def test_returns_none_for_unknown_pinpoint(self, seeded_store):
        # Work exists, but the pinpointed article doesn't
        auth = cellar_resolve(seeded_store, "32016R0679", "Art. 99")
        assert auth is None

    def test_resolves_without_pinpoint_sets_no_provision_id(self, seeded_store):
        auth = cellar_resolve(seeded_store, "32016R0679")
        assert auth is not None
        assert auth.provision_id is None
        assert auth.pinpoint is None


# ---------------------------------------------------------------------------
# cellar_in_force
# ---------------------------------------------------------------------------

class TestCellarInForce:
    def test_active_regulation_is_in_force(self, seeded_store):
        assert cellar_in_force(seeded_store, "32016R0679") is True

    def test_repealed_directive_is_not_in_force(self, seeded_store):
        assert cellar_in_force(seeded_store, "31995L0046") is False

    def test_unknown_celex_returns_false(self, seeded_store):
        assert cellar_in_force(seeded_store, "99999X9999") is False


# ---------------------------------------------------------------------------
# cellar_provision_text
# ---------------------------------------------------------------------------

class TestCellarProvisionText:
    def test_returns_seeded_text(self, seeded_store):
        text = cellar_provision_text(seeded_store, "32016R0679", "Art. 28(3)")
        assert text is not None
        assert "contract" in text.lower()

    def test_returns_none_for_unknown_pinpoint(self, seeded_store):
        text = cellar_provision_text(seeded_store, "32016R0679", "Art. 999")
        assert text is None

    def test_returns_none_when_no_pinpoint_given(self, seeded_store):
        text = cellar_provision_text(seeded_store, "32016R0679", None)
        assert text is None


# ---------------------------------------------------------------------------
# cellar_search
# ---------------------------------------------------------------------------

class TestCellarSearch:
    def test_returns_results_for_keyword_match(self, seeded_store):
        results = cellar_search(seeded_store, "processor contract")
        assert len(results) > 0
        authority, snippet = results[0]
        assert isinstance(authority, Authority)
        assert "contract" in snippet.lower()

    def test_respects_top_k(self, seeded_store):
        results = cellar_search(seeded_store, "processing", top_k=1)
        assert len(results) <= 1

    def test_returns_empty_for_no_match(self, seeded_store):
        results = cellar_search(seeded_store, "quantum entanglement cryptography xyz")
        assert results == []

    def test_authority_has_work_uuid(self, seeded_store):
        results = cellar_search(seeded_store, "processor")
        assert len(results) > 0
        auth, _ = results[0]
        assert auth.work_uuid is not None
        assert auth.celex is not None


# ---------------------------------------------------------------------------
# PlaybookArchitect — inferred-mode contract
# ---------------------------------------------------------------------------

_SCRIPTED_ARCHITECT_JSON = {
    "playbook": {
        "scenario": "negotiation",
        "matter_summary": "GDPR-compliant DPA negotiation for cloud processing services.",
        "objectives": ["Secure Art. 28(3) compliant DPA", "Cap processor liability"],
        "items": [
            {
                "id": "art28_compliant_dpa",
                "label": "Art. 28(3) DPA compliance",
                "kind": "must_have",
                "target": "Full Art. 28(3) enumeration in the DPA",
                "walk_away": "Processor refuses sub-processor audit rights",
                "authorities": [
                    {
                        "celex": "32016R0679",
                        "eli": None,
                        "title": "GDPR",
                        "pinpoint": "Art. 28(3)",
                        "source": "cellar",
                    }
                ],
                "weight": 1.0,
            }
        ],
        "fallback_ladder": ["Accept quarterly audit rights instead of annual"],
        "walk_away_conditions": ["Processor refuses sub-processor audit rights"],
        "authorities": [
            {
                "celex": "32016R0679",
                "eli": None,
                "title": "GDPR",
                "pinpoint": "Art. 28",
                "source": "cellar",
            }
        ],
    },
    "opp_playbook": {
        "objectives": ["Limit liability exposure", "Minimise audit obligations"],
        "batna": "Terminate negotiations and use existing provider",
        "concession_ladder": [
            {
                "position": "Accept quarterly audit rights with 30-day notice",
                "unlock_condition": (
                    "User cites Art. 28(3)(h) specifically and demonstrates "
                    "documented audit necessity under Art. 5(2) accountability"
                ),
            }
        ],
    },
    "rubric_weights": {
        "outcome": 35,
        "must_haves": 25,
        "concession_discipline": 20,
        "legal_grounding": 15,
        "composure": 5,
    },
}


class TestArchitectContract:
    def test_inferred_mode_produces_valid_playbook_with_resolved_authorities(
        self, seeded_store
    ):
        """With mocked graph + model, the Architect must:
        1. Return parse-valid Playbook + OpponentPlaybook + rubric weights
        2. Resolve every cellar Authority to set work_uuid (SECV depends on this)
        """
        from crucible.agents.base import FakeModelClient
        from crucible.grounding.perplexity import FakePerplexityClient
        from crucible.agents.architect import PlaybookArchitect

        client = FakeModelClient(scripted=[json.dumps(_SCRIPTED_ARCHITECT_JSON)])
        architect = PlaybookArchitect(
            client=client,
            model="gemini-2.5-flash",
            graph_store=seeded_store,
            perplexity_client=FakePerplexityClient(),
        )

        playbook, opp_playbook, weights = architect.infer(
            "Client wants to negotiate a GDPR-compliant DPA with a cloud processor."
        )

        # Structural validation
        assert playbook.scenario == "negotiation"
        assert len(playbook.items) > 0
        assert len(opp_playbook.concession_ladder) > 0
        assert sum(weights.values()) == 100

        # Every cellar Authority must be resolved (work_uuid set)
        for auth in playbook.authorities:
            if auth.source == "cellar" and auth.celex:
                assert auth.work_uuid is not None, (
                    f"Playbook authority {auth.celex!r} {auth.pinpoint!r} "
                    f"was not resolved (work_uuid is None)"
                )
        for item in playbook.items:
            for auth in item.authorities:
                if auth.source == "cellar" and auth.celex:
                    assert auth.work_uuid is not None, (
                        f"Item {item.id!r}: authority {auth.celex!r} {auth.pinpoint!r} "
                        f"was not resolved"
                    )

    def test_rubric_weights_sum_to_100(self, seeded_store):
        from crucible.agents.base import FakeModelClient
        from crucible.grounding.perplexity import FakePerplexityClient
        from crucible.agents.architect import PlaybookArchitect

        client = FakeModelClient(scripted=[json.dumps(_SCRIPTED_ARCHITECT_JSON)])
        architect = PlaybookArchitect(
            client=client,
            model="gemini-2.5-flash",
            graph_store=seeded_store,
            perplexity_client=FakePerplexityClient(),
        )
        _, _, weights = architect.infer("GDPR DPA negotiation case.")
        assert sum(weights.values()) == 100

    def test_inferred_mode_resolved_authority_is_in_force(self, seeded_store):
        """Authorities resolved against the graph should carry in_force=True for live acts."""
        from crucible.agents.base import FakeModelClient
        from crucible.grounding.perplexity import FakePerplexityClient
        from crucible.agents.architect import PlaybookArchitect

        client = FakeModelClient(scripted=[json.dumps(_SCRIPTED_ARCHITECT_JSON)])
        architect = PlaybookArchitect(
            client=client,
            model="gemini-2.5-flash",
            graph_store=seeded_store,
            perplexity_client=FakePerplexityClient(),
        )
        playbook, _, _ = architect.infer("GDPR DPA case.")

        gdpr_auths = [
            a for a in playbook.authorities
            if a.celex == "32016R0679"
        ]
        assert gdpr_auths, "Expected at least one GDPR authority in playbook"
        for auth in gdpr_auths:
            assert auth.in_force is True, (
                f"GDPR authority {auth.pinpoint!r} should be in_force=True"
            )
