"""PlaybookArchitect — builds the Playbook, OpponentPlaybook, and Rubric.

Two modes (spec §5):
  - inferred: from a pasted case description, researches via cellar_search
    (authoritative) + perplexity_search (current commentary), then synthesises
    both sides' playbooks + a scoring rubric.  Every legal Authority is resolved
    via cellar_resolve (work_uuid + provision_id set) and checked with
    cellar_in_force (in_force flag set).
  - playbook: normalises an uploaded firm playbook into the schema, derives the
    hidden OpponentPlaybook from it.

The Architect runs once at session start (SequentialAgent pattern: research →
synthesise → validate).  It never breaks character; it's not a live opponent.
"""
from __future__ import annotations
import json
import re
from crucible.agents.base import ModelClient
from crucible.grounding.cellar.graph_store import GraphStore
from crucible.grounding.cellar.tools import cellar_resolve, cellar_search, cellar_in_force
from crucible.grounding.perplexity import PerplexityClient
from crucible.schemas import (
    Authority, ConcessionRung, OpponentPlaybook, Playbook, PlaybookItem,
)


# ---------------------------------------------------------------------------
# Default rubric weights (used when the model omits rubric_weights)
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: dict[str, int] = {
    "outcome": 35,
    "must_haves": 25,
    "concession_discipline": 20,
    "legal_grounding": 15,
    "composure": 5,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError(f"Cannot extract JSON from architect response: {raw[:200]!r}")


def _resolve_authority_list(
    authorities: list[Authority],
    store: GraphStore,
) -> list[Authority]:
    """Resolve each cellar authority against the graph; set work_uuid, provision_id, in_force."""
    resolved: list[Authority] = []
    for auth in authorities:
        if auth.source == "cellar" and auth.celex:
            result = cellar_resolve(store, auth.celex, auth.pinpoint)
            if result:
                resolved.append(auth.model_copy(update={
                    "work_uuid": result.work_uuid,
                    "provision_id": result.provision_id,
                    "eli": result.eli or auth.eli,
                    "in_force": result.in_force,
                }))
            else:
                # Not found in graph — keep as-is; SECV will flag this
                resolved.append(auth)
        else:
            resolved.append(auth)
    return resolved


def _resolve_playbook_authorities(playbook: Playbook, store: GraphStore) -> Playbook:
    """Walk the full playbook and resolve every cellar authority."""
    resolved_items = [
        item.model_copy(update={
            "authorities": _resolve_authority_list(item.authorities, store),
        })
        for item in playbook.items
    ]
    return playbook.model_copy(update={
        "authorities": _resolve_authority_list(playbook.authorities, store),
        "items": resolved_items,
    })


# ---------------------------------------------------------------------------
# Architect
# ---------------------------------------------------------------------------

class PlaybookArchitect:
    """Builds both sides' playbooks from either a firm playbook or a case description."""

    def __init__(
        self,
        client: ModelClient,
        model: str,
        graph_store: GraphStore,
        perplexity_client: PerplexityClient,
    ) -> None:
        self._client = client
        self._model = model
        self._store = graph_store
        self._perplexity = perplexity_client

    # ------------------------------------------------------------------
    # Inferred mode: case description → Playbook + OpponentPlaybook + weights
    # ------------------------------------------------------------------

    def infer(
        self,
        case_description: str,
        scenario: str = "negotiation",
        top_k_cellar: int = 5,
        max_perplexity: int = 3,
    ) -> tuple[Playbook, OpponentPlaybook, dict[str, int]]:
        """Research + synthesise from a case description.

        Step 1 — Research via cellar_search (authoritative) + Perplexity (commentary).
        Step 2 — Synthesise playbooks + rubric via model.
        Step 3 — Resolve all cellar authorities (work_uuid + in_force).
        """
        # Research phase
        cellar_hits = cellar_search(self._store, case_description, top_k=top_k_cellar)
        perplexity_hits = self._perplexity.search(case_description, max_results=max_perplexity)

        cellar_block = "\n".join(
            f"[{auth.celex} {auth.pinpoint or ''}] {snippet[:250]}"
            for auth, snippet in cellar_hits
        ) or "(no authoritative sources found)"

        perplexity_block = "\n".join(
            f"[{r.title}] {r.snippet[:200]}"
            for r in perplexity_hits
        ) or "(no current context found)"

        # Synthesis phase
        system = _INFERRED_SYSTEM_PROMPT.format(scenario=scenario)
        user_msg = (
            f"CASE DESCRIPTION:\n{case_description}\n\n"
            f"AUTHORITATIVE SOURCES (CELLAR/Neo4j — black-letter law):\n{cellar_block}\n\n"
            f"CURRENT CONTEXT (Perplexity — commentary only):\n{perplexity_block}\n\n"
            "Produce the JSON output now."
        )
        raw = self._client.generate(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        data = _extract_json(raw)

        playbook = Playbook.model_validate(data["playbook"])
        opp_playbook = OpponentPlaybook.model_validate(data["opp_playbook"])
        rubric_weights: dict[str, int] = {
            k: int(v)
            for k, v in data.get("rubric_weights", _DEFAULT_WEIGHTS).items()
        }

        # Resolution phase: set work_uuid + in_force for all cellar authorities
        playbook = _resolve_playbook_authorities(playbook, self._store)

        return playbook, opp_playbook, rubric_weights

    # ------------------------------------------------------------------
    # Playbook mode: raw firm playbook text → Playbook + OpponentPlaybook
    # ------------------------------------------------------------------

    def normalize(
        self,
        raw_playbook_text: str,
        scenario: str = "negotiation",
    ) -> tuple[Playbook, OpponentPlaybook]:
        """Parse and normalise a firm playbook, then derive the opponent's hidden side."""
        system = _NORMALIZE_SYSTEM_PROMPT
        user_msg = (
            f"FIRM PLAYBOOK (raw text):\n{raw_playbook_text}\n\n"
            "Normalise into the JSON schema. Return ONLY the JSON object."
        )
        raw = self._client.generate(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        data = _extract_json(raw)
        playbook = Playbook.model_validate(data["playbook"])
        opp_playbook = OpponentPlaybook.model_validate(data["opp_playbook"])
        playbook = _resolve_playbook_authorities(playbook, self._store)
        return playbook, opp_playbook


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_INFERRED_SYSTEM_PROMPT = """You are a senior legal training architect. Given a case description and research, produce two-sided playbooks and a scoring rubric for an adversarial training scenario.

Scenario type: {scenario}

Output a single JSON object with this EXACT structure (no prose, no markdown fences):
{{
  "playbook": {{
    "scenario": "{scenario}",
    "matter_summary": "<1-2 sentence summary>",
    "objectives": ["<objective>", ...],
    "items": [
      {{
        "id": "<snake_case_id>",
        "label": "<short label>",
        "kind": "<must_have|nice_to_have|trap|model_move>",
        "target": "<desired position>",
        "walk_away": "<line not to cross or null>",
        "authorities": [
          {{"celex": "<e.g. 32016R0679>", "eli": null, "title": "<act title>", "pinpoint": "<e.g. Art. 28(3)>", "source": "cellar"}}
        ],
        "weight": 1.0
      }}
    ],
    "fallback_ladder": ["<fallback>", ...],
    "walk_away_conditions": ["<condition>", ...],
    "authorities": [
      {{"celex": "...", "eli": null, "title": "...", "pinpoint": "...", "source": "cellar"}}
    ]
  }},
  "opp_playbook": {{
    "objectives": ["<objective>", ...],
    "batna": "<what the opponent does if talks fail>",
    "concession_ladder": [
      {{"position": "<what they would accept>", "unlock_condition": "<specific legal/factual demonstration required>"}}
    ]
  }},
  "rubric_weights": {{
    "outcome": 35,
    "must_haves": 25,
    "concession_discipline": 20,
    "legal_grounding": 15,
    "composure": 5
  }}
}}

Rules:
- Every authority for an EU legislative act MUST include the CELEX number
- Concession ladder unlock_conditions must be legally specific (cite exact articles)
- rubric_weights must sum to exactly 100
- Return ONLY the JSON — no surrounding text
"""

_NORMALIZE_SYSTEM_PROMPT = """You are a legal playbook parser. Given a raw firm playbook, normalise it into the Crucible schema and derive the hidden opponent playbook.

Output a single JSON object (no prose, no markdown fences):
{{
  "playbook": {{
    "scenario": "<negotiation|hot_seat|difficult_client>",
    "matter_summary": "...",
    "objectives": [...],
    "items": [...],
    "fallback_ladder": [...],
    "walk_away_conditions": [...],
    "authorities": [...]
  }},
  "opp_playbook": {{
    "objectives": [...],
    "batna": "...",
    "concession_ladder": [...]
  }}
}}

Follow the same schema as inferred mode. Return ONLY JSON."""
