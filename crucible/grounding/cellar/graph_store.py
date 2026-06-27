"""GraphStore Protocol + InMemoryGraphStore for tests.

The Protocol is the injection seam: Neo4jGraphStore (prod) and
InMemoryGraphStore (tests) both satisfy it. Agents and SECV depend on
this interface only — never on the concrete Neo4j driver.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class _WorkData:
    cellar_uuid: str
    celex: str
    eli: str | None
    title: str
    work_type: str
    date_document: str


@dataclass
class _ProvisionData:
    provision_id: str
    celex: str
    article_no: str
    heading: str
    text: str


@runtime_checkable
class GraphStore(Protocol):
    """Injection seam for graph operations.

    Implemented by Neo4jGraphStore (production) and InMemoryGraphStore (tests).
    No agent or tool imports the concrete implementations directly.
    """

    def resolve_work(self, celex: str) -> _WorkData | None: ...
    def resolve_provision(self, celex: str, pinpoint: str) -> _ProvisionData | None: ...
    def is_repealed(self, celex: str) -> bool: ...
    def search_provisions(
        self, query: str, top_k: int = 5
    ) -> list[tuple[_ProvisionData, _WorkData]]: ...


class InMemoryGraphStore:
    """Deterministic in-memory graph for unit tests.

    No Neo4j driver, no embeddings, no network — all data seeded via
    add_work / add_provision / add_repeals_edge calls.
    """

    def __init__(self) -> None:
        self._works: dict[str, _WorkData] = {}
        self._provisions: dict[str, _ProvisionData] = {}
        self._prov_by_article: dict[tuple[str, str], str] = {}  # (celex, article_no) → id
        self._prov_by_celex: dict[str, list[str]] = {}           # celex → [provision_id]
        self._repealed_by: dict[str, str] = {}                   # repealed_celex → repealor

    # ------------------------------------------------------------------
    # Seed helpers (used in fixtures and test setup)
    # ------------------------------------------------------------------

    def add_work(
        self,
        *,
        cellar_uuid: str,
        celex: str,
        eli: str | None = None,
        title: str,
        work_type: str,
        date_document: str,
    ) -> None:
        self._works[celex] = _WorkData(
            cellar_uuid=cellar_uuid,
            celex=celex,
            eli=eli,
            title=title,
            work_type=work_type,
            date_document=date_document,
        )

    def add_provision(
        self,
        *,
        celex: str,
        provision_id: str,
        article_no: str,
        heading: str,
        text: str,
    ) -> None:
        data = _ProvisionData(
            provision_id=provision_id,
            celex=celex,
            article_no=article_no,
            heading=heading,
            text=text,
        )
        self._provisions[provision_id] = data
        self._prov_by_celex.setdefault(celex, []).append(provision_id)
        self._prov_by_article[(celex, article_no)] = provision_id

    def add_repeals_edge(self, *, from_celex: str, to_celex: str) -> None:
        self._repealed_by[to_celex] = from_celex

    # ------------------------------------------------------------------
    # GraphStore Protocol implementation
    # ------------------------------------------------------------------

    def resolve_work(self, celex: str) -> _WorkData | None:
        return self._works.get(celex)

    def resolve_provision(self, celex: str, pinpoint: str) -> _ProvisionData | None:
        pid = self._prov_by_article.get((celex, pinpoint))
        return self._provisions.get(pid) if pid else None

    def is_repealed(self, celex: str) -> bool:
        return celex in self._repealed_by

    def search_provisions(
        self, query: str, top_k: int = 5
    ) -> list[tuple[_ProvisionData, _WorkData]]:
        """Simple keyword search — prod uses Neo4j vector index instead."""
        query_lower = query.lower()
        hits: list[tuple[float, _ProvisionData, _WorkData]] = []
        for pid, prov in self._provisions.items():
            work = self._works.get(prov.celex)
            if not work:
                continue
            combined = f"{prov.heading} {prov.text}".lower()
            score = sum(1.0 for word in query_lower.split() if word in combined)
            if score > 0:
                hits.append((score, prov, work))
        hits.sort(key=lambda t: t[0], reverse=True)
        return [(p, w) for _, p, w in hits[:top_k]]
