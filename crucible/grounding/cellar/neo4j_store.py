"""Neo4jGraphStore — production GraphStore backed by the real Neo4j instance.

Import is lazy so the neo4j driver is only required when this class is
instantiated (tests use InMemoryGraphStore and never touch this file).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from crucible.grounding.cellar.graph_store import _WorkData, _ProvisionData

if TYPE_CHECKING:
    from neo4j import Driver


class Neo4jGraphStore:
    """GraphStore implementation backed by Neo4j 5.x (APOC + GDS)."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase  # lazy — only fails if not installed
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------
    # GraphStore Protocol
    # ------------------------------------------------------------------

    def resolve_work(self, celex: str) -> _WorkData | None:
        query = (
            "MATCH (w:Work {celex: $celex}) "
            "RETURN w.cellar_uuid AS uuid, w.celex AS celex, w.eli AS eli, "
            "       w.title AS title, w.type AS work_type, "
            "       toString(w.date_document) AS date_document "
            "LIMIT 1"
        )
        with self._driver.session() as session:
            record = session.run(query, celex=celex).single()
        if record is None:
            return None
        return _WorkData(
            cellar_uuid=record["uuid"],
            celex=record["celex"],
            eli=record["eli"],
            title=record["title"],
            work_type=record["work_type"] or "",
            date_document=record["date_document"] or "",
        )

    def resolve_provision(self, celex: str, pinpoint: str) -> _ProvisionData | None:
        query = (
            "MATCH (w:Work {celex: $celex})-[:HAS_PROVISION]->(p:Provision) "
            "WHERE p.article_no = $pinpoint "
            "RETURN p.provision_id AS pid, p.article_no AS article_no, "
            "       p.heading AS heading, p.text AS text "
            "LIMIT 1"
        )
        with self._driver.session() as session:
            record = session.run(query, celex=celex, pinpoint=pinpoint).single()
        if record is None:
            return None
        return _ProvisionData(
            provision_id=record["pid"],
            celex=celex,
            article_no=record["article_no"],
            heading=record["heading"] or "",
            text=record["text"] or "",
        )

    def is_repealed(self, celex: str) -> bool:
        # A work is repealed if another work has a REPEALS (or IMPLICITLY_REPEALS) edge to it
        query = (
            "MATCH (:Work)-[:REPEALS|IMPLICITLY_REPEALS]->(:Work {celex: $celex}) "
            "RETURN count(*) AS cnt LIMIT 1"
        )
        with self._driver.session() as session:
            record = session.run(query, celex=celex).single()
        return bool(record and record["cnt"] > 0)

    def search_provisions(
        self, query: str, top_k: int = 5
    ) -> list[tuple[_ProvisionData, _WorkData]]:
        """Vector search via Neo4j's native index + structural context traversal."""
        # Runtime embedding is performed here; the vector index dim must match
        # the embed_dim in config.py (768 for text-embedding-004).
        embedding = self._embed(query)
        cypher = (
            "CALL db.index.vector.queryNodes('chunk_vec', $top_k, $embedding) "
            "YIELD node AS chunk, score "
            "MATCH (chunk)<-[:HAS_CHUNK]-(p:Provision)<-[:HAS_PROVISION]-(w:Work) "
            "RETURN p.provision_id AS pid, p.article_no AS article_no, "
            "       p.heading AS heading, p.text AS text, "
            "       w.cellar_uuid AS uuid, w.celex AS celex, w.eli AS eli, "
            "       w.title AS title, w.type AS work_type, "
            "       toString(w.date_document) AS date_document "
            "ORDER BY score DESC LIMIT $top_k"
        )
        with self._driver.session() as session:
            records = list(session.run(cypher, top_k=top_k, embedding=embedding))

        results: list[tuple[_ProvisionData, _WorkData]] = []
        for rec in records:
            prov = _ProvisionData(
                provision_id=rec["pid"],
                celex=rec["celex"],
                article_no=rec["article_no"],
                heading=rec["heading"] or "",
                text=rec["text"] or "",
            )
            work = _WorkData(
                cellar_uuid=rec["uuid"],
                celex=rec["celex"],
                eli=rec["eli"],
                title=rec["title"],
                work_type=rec["work_type"] or "",
                date_document=rec["date_document"] or "",
            )
            results.append((prov, work))
        return results

    def _embed(self, text: str) -> list[float]:
        """Embed query text using the configured model.

        Uses google-cloud-aiplatform TextEmbeddingModel. The output dim
        MUST match the Neo4j vector index dim (embed_dim in config.py).
        """
        from vertexai.language_models import TextEmbeddingModel
        from crucible.config import get_settings
        settings = get_settings()
        model = TextEmbeddingModel.from_pretrained(settings.embed_model)
        embeddings = model.get_embeddings([text])
        vec: list[float] = embeddings[0].values
        assert len(vec) == settings.embed_dim, (
            f"Embedding dim mismatch: got {len(vec)}, expected {settings.embed_dim}. "
            f"Update embed_dim in config.py or re-create the Neo4j vector index."
        )
        return vec


def make_neo4j_store(uri: str, user: str, password: str) -> Neo4jGraphStore:
    return Neo4jGraphStore(uri, user, password)
