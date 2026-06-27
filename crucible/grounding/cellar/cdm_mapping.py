"""CDM (Common Data Model) predicate → Crucible edge type mapping.

CELLAR RDF uses CDM predicates; we normalise them to one of three
edge type groups before loading into Neo4j:
  - DESTROYS group: REPEALS | IMPLICITLY_REPEALS | AMENDS | CORRECTS | REPLACES | OVERRULES
  - DEPENDENCY group: CITES | BASED_ON | ADOPTS
  - (others ignored)

Reference: EUR-Lex CDM ontology documentation.
"""
from __future__ import annotations

# CDM predicate URI fragments → Crucible edge type
_CDM_TO_EDGE: dict[str, str] = {
    # DESTROYS group
    "repeals": "REPEALS",
    "implicitly_repeals": "IMPLICITLY_REPEALS",
    "amends": "AMENDS",
    "corrects": "CORRECTS",
    "replaces": "REPLACES",
    "overrules": "OVERRULES",
    # DEPENDENCY group
    "cites": "CITES",
    "based_on": "BASED_ON",
    "adopts": "ADOPTS",
    # Alias variants sometimes seen in CELLAR dumps
    "is_about": "CITES",
    "completed_by": "CITES",
}

_DESTROYS_GROUP = frozenset({
    "REPEALS", "IMPLICITLY_REPEALS", "AMENDS", "CORRECTS", "REPLACES", "OVERRULES",
})


def predicate_to_edge_type(predicate_uri: str) -> str | None:
    """Map a CDM predicate URI to a Crucible edge type.

    Returns None for predicates we don't track (silently skipped at ingest).
    """
    fragment = predicate_uri.rstrip("/").rsplit("/", 1)[-1].lower()
    fragment = fragment.rsplit("#", 1)[-1].lower()
    return _CDM_TO_EDGE.get(fragment)


def is_destroys_edge(edge_type: str) -> bool:
    return edge_type in _DESTROYS_GROUP
