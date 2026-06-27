"""Chunk + embed provisions → :Chunk{embedding}; create vector index.

This is the last ingest step. It reads :Provision nodes from Neo4j,
chunks their text, embeds each chunk, and writes :Chunk nodes back.

The embed_dim in config.py MUST equal the Neo4j vector index dimension.
The assertion in Neo4jGraphStore._embed() enforces this at runtime;
create_vector_index() enforces it at index-build time.

Runtime rule: ingest-only.
"""
from __future__ import annotations
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver

_CHUNK_SIZE = 500   # characters
_CHUNK_OVERLAP = 100


def chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level chunks."""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def embed_texts(texts: list[str], embed_model: str, embed_dim: int) -> list[list[float]]:
    """Embed a batch of texts using the configured Vertex AI model."""
    from vertexai.language_models import TextEmbeddingModel
    model = TextEmbeddingModel.from_pretrained(embed_model)
    # Vertex allows up to 250 texts per batch
    all_vecs: list[list[float]] = []
    batch_size = 250
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = model.get_embeddings(batch)
        for emb in embeddings:
            vec = emb.values
            assert len(vec) == embed_dim, (
                f"embed_dim mismatch: got {len(vec)}, expected {embed_dim}. "
                f"Update embed_dim in config.py or re-create the Neo4j vector index."
            )
            all_vecs.append(list(vec))
    return all_vecs


def build_chunks(driver: "Driver", embed_model: str, embed_dim: int) -> int:
    """Read all :Provision nodes, chunk + embed, write :Chunk nodes. Returns chunk count."""
    from crucible.grounding.cellar.neo4j_loader import load_chunks, create_vector_index

    # Ensure vector index exists with correct dim
    create_vector_index(driver, embed_dim)

    # Fetch all provisions
    with driver.session() as session:
        records = list(session.run(
            "MATCH (p:Provision) RETURN p.provision_id AS pid, p.text AS text"
        ))

    chunk_rows: list[dict] = []
    texts_to_embed: list[str] = []
    chunk_meta: list[dict] = []

    for rec in records:
        pid = rec["pid"]
        text = rec["text"] or ""
        for idx, chunk_text_str in enumerate(chunk_text(text)):
            chunk_id = hashlib.sha1(f"{pid}::{idx}::{chunk_text_str}".encode()).hexdigest()
            texts_to_embed.append(chunk_text_str)
            chunk_meta.append({"provision_id": pid, "chunk_id": chunk_id, "text": chunk_text_str})

    if not texts_to_embed:
        return 0

    embeddings = embed_texts(texts_to_embed, embed_model, embed_dim)
    for meta, emb in zip(chunk_meta, embeddings):
        chunk_rows.append({**meta, "embedding": emb})

    load_chunks(driver, chunk_rows)
    return len(chunk_rows)
