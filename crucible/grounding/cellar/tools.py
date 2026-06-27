"""The four CELLAR graph tools — the contract agents and SECV depend on.

All functions take a GraphStore (injected) so they work with both the
in-memory test stub and the real Neo4jGraphStore.

Runtime rule: these are the ONLY Neo4j entry-points at runtime.
SPARQL / CELLAR REST is used at ingest time only (cellar_sparql.py).
"""
from __future__ import annotations
from crucible.schemas import Authority
from crucible.grounding.cellar.graph_store import GraphStore


def cellar_resolve(
    store: GraphStore,
    celex: str,
    pinpoint: str | None = None,
) -> Authority | None:
    """Structural lookup: does the Work + optional Provision exist?

    Returns Authority with work_uuid (and provision_id if pinpointed) set.
    Returns None if the Work doesn't exist OR if pinpoint is specified but
    not found — this strict failure mode is intentional (SECV Step 1).
    """
    work = store.resolve_work(celex)
    if work is None:
        return None

    prov_id: str | None = None
    if pinpoint is not None:
        prov = store.resolve_provision(celex, pinpoint)
        if prov is None:
            return None  # pinpoint given but not found — hard fail
        prov_id = prov.provision_id

    in_force = not store.is_repealed(celex)
    return Authority(
        celex=celex,
        eli=work.eli,
        title=work.title,
        pinpoint=pinpoint,
        source="cellar",
        work_uuid=work.cellar_uuid,
        provision_id=prov_id,
        in_force=in_force,
    )


def cellar_provision_text(
    store: GraphStore,
    celex: str,
    pinpoint: str | None,
) -> str | None:
    """Return the exact provision text for a pinpointed article.

    Returns None if no pinpoint is given or the article isn't found.
    This is SECV Step 2 — the text used for entailment checking.
    """
    if pinpoint is None:
        return None
    prov = store.resolve_provision(celex, pinpoint)
    return prov.text if prov else None


def cellar_in_force(store: GraphStore, celex: str) -> bool:
    """Return False if this Work has been repealed (via REPEALS/AMENDS edges).

    Unknown CELEX → False (conservative; prefer explicit ingest over guessing).
    """
    work = store.resolve_work(celex)
    if work is None:
        return False
    return not store.is_repealed(celex)


def cellar_search(
    store: GraphStore,
    query: str,
    top_k: int = 5,
) -> list[tuple[Authority, str]]:
    """Semantic / keyword search over :Chunk text nodes.

    Returns (Authority, snippet) pairs sorted by relevance.
    In production uses Neo4j VectorCypherRetriever (embedding-based).
    In tests the InMemoryGraphStore uses simple keyword scoring.
    """
    hits = store.search_provisions(query, top_k=top_k)
    results: list[tuple[Authority, str]] = []
    for prov, work in hits:
        in_force = not store.is_repealed(work.celex)
        auth = Authority(
            celex=work.celex,
            eli=work.eli,
            title=work.title,
            pinpoint=prov.article_no,
            source="cellar",
            work_uuid=work.cellar_uuid,
            provision_id=prov.provision_id,
            in_force=in_force,
        )
        snippet = prov.text[:300]
        results.append((auth, snippet))
    return results
