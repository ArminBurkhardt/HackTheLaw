"""SECV — Semantic-Entropy Citation Verifier.

Never call verify_citation inside a live opponent turn — only at debrief and
on user citations (spec §7.3). Cost: M + O(M²) Flash calls per citation.
Cache by sha1(claim | celex | pinpoint).
"""
from __future__ import annotations
import hashlib

from crucible.schemas import CitationCheck
from crucible.grounding.cellar.graph_store import GraphStore
from crucible.grounding.cellar.tools import cellar_resolve, cellar_provision_text, cellar_in_force
from crucible.agents.base import ModelClient
from crucible.verify.entailment import EntailmentOracle, ModelEntailmentOracle
from crucible.verify.entropy import cluster_by_bidirectional_entailment, discrete_semantic_entropy


_SAMPLING_SYSTEM = (
    "You are a precise legal analyst. Based solely on the legal provision text below, "
    "state ONE legal proposition that this provision establishes. "
    "Do not use any external knowledge. State it as a single declarative sentence."
)


def _cache_key(claim: str, celex: str | None, pinpoint: str | None) -> str:
    return hashlib.sha1(f"{claim}|{celex}|{pinpoint}".encode()).hexdigest()


def _sample_propositions(
    provision_text: str,
    claim: str,
    client: ModelClient,
    model: str,
    M: int,
) -> list[str]:
    """Sample M grounded re-derivations from the provision text."""
    props = []
    for _ in range(M):
        reply = client.generate(
            model=model,
            system=_SAMPLING_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Provision text:\n{provision_text}\n\n"
                    f"Regarding: {claim}\n\n"
                    "State ONE proposition this provision establishes:"
                ),
            }],
        )
        props.append(reply.strip())
    return props


def _dominant_rep(propositions: list[str], clusters: list[list[int]]) -> str:
    """First element of the largest cluster."""
    dominant = max(clusters, key=lambda c: len(c))
    return propositions[dominant[0]]


def _check_support(dominant: str, claim: str, oracle: EntailmentOracle) -> str:
    """Returns 'supports', 'neutral', or 'contradicts'."""
    if oracle.entails(dominant, claim):
        return "supports"
    if oracle.entails(claim, dominant):
        return "neutral"   # claim is more specific than what provision says
    return "neutral"


def _done(
    cache: dict[str, CitationCheck] | None,
    key: str,
    result: CitationCheck,
) -> CitationCheck:
    if cache is not None:
        cache[key] = result
    return result


def verify_citation(
    claim: str,
    celex: str | None,
    pinpoint: str | None,
    *,
    store: GraphStore,
    model_client: ModelClient,
    model: str,
    entailment_oracle: EntailmentOracle | None = None,
    provision_text_override: str | None = None,
    M: int = 5,
    theta_high: float = 0.7,
    cache: dict[str, CitationCheck] | None = None,
) -> CitationCheck:
    """Run the 6-step SECV pipeline → CitationCheck.

    CELLAR path: provide celex (+ optional pinpoint for semantic verification).
    Perplexity path: pass celex=None and provision_text_override=<web snippet>;
      citation_score is capped at 0.7 (commentary, not black-letter law).
    """
    key = _cache_key(claim, celex, pinpoint)
    if cache is not None and key in cache:
        return cache[key]

    # ── Step 1: Structural gate (CELLAR only) ────────────────────────────
    if celex is not None:
        auth = cellar_resolve(store, celex, pinpoint)
        if auth is None:
            ref = f"CELEX {celex!r}" + (f" pinpoint {pinpoint!r}" if pinpoint else "")
            return _done(cache, key, CitationCheck(
                status="fabricated_identifier",
                support="neutral",
                semantic_entropy=0.0,
                confidence=0.0,
                citation_score=0.0,
                n_clusters=0,
                samples=0,
                note=f"{ref} not found in graph.",
            ))

        if not cellar_in_force(store, celex):
            return _done(cache, key, CitationCheck(
                status="not_in_force",
                support="neutral",
                semantic_entropy=0.0,
                confidence=0.0,
                citation_score=0.0,
                n_clusters=0,
                samples=0,
                note=f"{celex} is repealed or not currently in force.",
            ))

        provision_text = provision_text_override or cellar_provision_text(store, celex, pinpoint) or ""
    else:
        provision_text = provision_text_override or ""

    if not provision_text:
        ref = f"{celex} {pinpoint}".strip() if celex else "(external source)"
        return _done(cache, key, CitationCheck(
            status="weak",
            support="neutral",
            semantic_entropy=1.0,
            confidence=0.0,
            citation_score=0.0,
            n_clusters=0,
            samples=0,
            note=f"{ref}: no provision text available — structural resolution only.",
        ))

    oracle = entailment_oracle or ModelEntailmentOracle(model_client, model)

    # ── Step 2: Grounded re-derivation sampling ───────────────────────────
    propositions = _sample_propositions(provision_text, claim, model_client, model, M)

    # ── Step 3: Semantic clustering by bidirectional entailment ───────────
    clusters = cluster_by_bidirectional_entailment(propositions, oracle)

    # ── Step 4: Discrete semantic entropy ─────────────────────────────────
    se, se_norm, confidence = discrete_semantic_entropy([len(c) for c in clusters], M)
    n_clusters = len(clusters)

    # ── Step 5: Claim-entailment direction ────────────────────────────────
    dom = _dominant_rep(propositions, clusters)
    support = _check_support(dom, claim, oracle)

    # ── Step 6: Verdict ───────────────────────────────────────────────────
    if support == "supports" and confidence >= theta_high:
        status = "verified"
    elif support == "supports":
        status = "weak"
    else:
        status = "misattributed"

    citation_score = confidence if support == "supports" else 0.0
    if celex is None:
        citation_score = min(citation_score, 0.7)  # Perplexity cap

    ref = f"{celex} {pinpoint}".strip() if celex else "(external source)"
    if status == "verified":
        note = f"{ref}: provision text supports the claimed proposition."
    elif status == "weak":
        note = f"{ref}: weakly supported — high semantic entropy suggests uncertain grounding."
    else:
        snippet = dom[:120] + ("…" if len(dom) > 120 else "")
        note = (
            f"{ref} does not support the claimed proposition. "
            f"Provision actually establishes: '{snippet}'"
        )

    return _done(cache, key, CitationCheck(
        status=status,
        support=support,
        semantic_entropy=se,
        confidence=confidence,
        citation_score=citation_score,
        n_clusters=n_clusters,
        samples=M,
        note=note,
    ))
