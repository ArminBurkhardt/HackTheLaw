"""Batched Neo4j loader — constraints + MERGE via apoc.periodic.iterate.

Handles:
  - :Work nodes with uniqueness constraint on cellar_uuid
  - :Provision nodes attached via HAS_PROVISION
  - :Chunk nodes attached via HAS_CHUNK (with embedding)
  - Relationship edges (REPEALS, CITES, etc.)
  - Vector index creation on Chunk.embedding

Runtime rule: ingest-only. Runtime agents use Neo4jGraphStore, not this module.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver


_BATCH_SIZE = 10_000

# ------------------------------------------------------------------
# Schema setup (idempotent)
# ------------------------------------------------------------------

_CONSTRAINTS = [
    "CREATE CONSTRAINT work_uuid_unique IF NOT EXISTS FOR (w:Work) REQUIRE w.cellar_uuid IS UNIQUE",
    "CREATE INDEX work_celex IF NOT EXISTS FOR (w:Work) ON (w.celex)",
    "CREATE INDEX work_date IF NOT EXISTS FOR (w:Work) ON (w.date_document)",
    "CREATE CONSTRAINT provision_id_unique IF NOT EXISTS FOR (p:Provision) REQUIRE p.provision_id IS UNIQUE",
]


def create_schema(driver: "Driver") -> None:
    with driver.session() as session:
        for stmt in _CONSTRAINTS:
            session.run(stmt)


def create_vector_index(driver: "Driver", dim: int) -> None:
    """Create the chunk_vec vector index (idempotent — IF NOT EXISTS)."""
    stmt = (
        "CREATE VECTOR INDEX chunk_vec IF NOT EXISTS "
        "FOR (c:Chunk) ON (c.embedding) "
        "OPTIONS {indexConfig: {"
        f"  `vector.dimensions`: {dim}, "
        "  `vector.similarity_function`: 'cosine'"
        "}}"
    )
    with driver.session() as session:
        session.run(stmt)


# ------------------------------------------------------------------
# Batch MERGE helpers
# ------------------------------------------------------------------

def load_works(driver: "Driver", rows: list[dict]) -> int:
    """MERGE :Work nodes in batches. Returns total merged count."""
    if not rows:
        return 0
    query = (
        "UNWIND $rows AS row "
        "MERGE (w:Work {cellar_uuid: row.cellar_uuid}) "
        "SET w.celex = row.celex, w.eli = row.eli, w.title = row.title, "
        "    w.type = row.type, w.sector = row.sector, "
        "    w.date_document = row.date_document"
    )
    _batch_run(driver, query, rows)
    return len(rows)


def load_provisions(driver: "Driver", rows: list[dict]) -> int:
    """MERGE :Provision nodes and attach to :Work via HAS_PROVISION."""
    if not rows:
        return 0
    query = (
        "UNWIND $rows AS row "
        "MATCH (w:Work {celex: row.celex}) "
        "MERGE (p:Provision {provision_id: row.provision_id}) "
        "SET p.article_no = row.article_no, p.heading = row.heading, "
        "    p.text = row.text, p.celex = row.celex "
        "MERGE (w)-[:HAS_PROVISION]->(p)"
    )
    _batch_run(driver, query, rows)
    return len(rows)


def load_chunks(driver: "Driver", rows: list[dict]) -> int:
    """MERGE :Chunk nodes with embeddings, attach via HAS_CHUNK."""
    if not rows:
        return 0
    query = (
        "UNWIND $rows AS row "
        "MATCH (p:Provision {provision_id: row.provision_id}) "
        "MERGE (c:Chunk {chunk_id: row.chunk_id}) "
        "SET c.text = row.text, c.embedding = row.embedding "
        "MERGE (p)-[:HAS_CHUNK]->(c)"
    )
    _batch_run(driver, query, rows)
    return len(rows)


def load_edges(driver: "Driver", rows: list[dict]) -> int:
    """Create directed edges between :Work nodes by CELEX."""
    if not rows:
        return 0
    # We load each edge type separately to use the correct relationship type
    from itertools import groupby
    rows_sorted = sorted(rows, key=lambda r: r["edge_type"])
    total = 0
    for edge_type, group in groupby(rows_sorted, key=lambda r: r["edge_type"]):
        batch = list(group)
        # Dynamic relationship type — Neo4j doesn't support parameterised rel types,
        # so we build the query string. edge_type is from our controlled vocabulary
        # (cdm_mapping.py), never from user input — not a injection risk.
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (a:Work {{celex: row.from_celex}}) "
            f"MATCH (b:Work {{celex: row.to_celex}}) "
            f"MERGE (a)-[:{edge_type}]->(b)"
        )
        _batch_run(driver, query, batch)
        total += len(batch)
    return total


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _batch_run(driver: "Driver", query: str, rows: list[dict]) -> None:
    for i in range(0, len(rows), _BATCH_SIZE):
        batch = rows[i : i + _BATCH_SIZE]
        with driver.session() as session:
            session.run(query, rows=batch)
