"""CLI entrypoint for `make index-cellar SCENARIO=negotiation`.

Orchestrates the full ingest pipeline:
  1. Discover CELEX sub-corpus for the scenario
  2. Fetch / stream RDF metadata → :Work nodes
  3. Fetch FORMEX XML → :Provision nodes
  4. Chunk + embed → :Chunk nodes + vector index

Usage:
    python -m crucible.grounding.cellar.ingest --scenario negotiation

Respects NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD from .env.
SPARQL/REST access is ONLY used here — runtime touches Neo4j only.
"""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _scenario_celexes(scenario: str) -> list[str]:
    from crucible.grounding.cellar.cellar_sparql import query_gdpr_subcorpus
    if scenario == "negotiation":
        return query_gdpr_subcorpus()
    raise ValueError(f"Unknown scenario: {scenario!r}. Supported: 'negotiation'")


def run_ingest(scenario: str, dump_path: Path | None = None) -> None:
    from crucible.config import get_settings
    from crucible.grounding.cellar.cellar_sparql import fetch_work_metadata
    from crucible.grounding.cellar.neo4j_loader import (
        create_schema, load_works, load_provisions, load_edges,
    )
    from crucible.grounding.cellar.kg_build import build_chunks
    from crucible.grounding.cellar.formex_extract import extract_provisions

    settings = get_settings()
    if not all([settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password]):
        logger.error("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD must be set in .env")
        sys.exit(1)

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,  # type: ignore[arg-type]
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    logger.info("Creating schema constraints and indexes…")
    create_schema(driver)

    celexes = _scenario_celexes(scenario)
    logger.info("Sub-corpus: %d CELEX numbers for scenario=%r", len(celexes), scenario)

    work_rows: list[dict] = []
    for celex in celexes:
        entry = fetch_work_metadata(celex)
        if entry:
            work_rows.append({
                "cellar_uuid": entry.celex,  # use CELEX as UUID if no explicit UUID
                "celex": entry.celex,
                "eli": entry.eli,
                "title": entry.title,
                "type": entry.work_type,
                "sector": entry.celex[0] if entry.celex else "",
                "date_document": "",
            })
            logger.info("  ✓ %s — %s", celex, entry.title[:60])
        else:
            logger.warning("  ✗ %s — metadata not found", celex)

    if dump_path and dump_path.is_file():
        logger.info("Streaming RDF dump: %s", dump_path)
        from crucible.grounding.cellar.mtd_stream import stream_ntriples, triples_to_work_rows
        rdf_rows = list(triples_to_work_rows(
            stream_ntriples(dump_path), scope_celexes=set(celexes)
        ))
        work_rows.extend(rdf_rows)
        logger.info("  + %d work rows from RDF dump", len(rdf_rows))

    # Deduplicate by CELEX
    seen: set[str] = set()
    unique_work_rows = []
    for row in work_rows:
        if row["celex"] not in seen:
            seen.add(row["celex"])
            unique_work_rows.append(row)

    n_works = load_works(driver, unique_work_rows)
    logger.info("Loaded %d :Work nodes", n_works)

    prov_rows: list[dict] = []
    for celex in celexes:
        if dump_path:
            formex_path = dump_path.parent / f"{celex}.xml"
            if formex_path.exists():
                from crucible.grounding.cellar.formex_extract import extract_provisions
                provs = extract_provisions(celex, formex_path)
                for p in provs:
                    prov_rows.append({
                        "celex": p.celex,
                        "provision_id": p.provision_id,
                        "article_no": p.article_no,
                        "heading": p.heading,
                        "text": p.text,
                    })

    n_provs = load_provisions(driver, prov_rows)
    logger.info("Loaded %d :Provision nodes", n_provs)

    logger.info("Building chunks + embeddings (dim=%d)…", settings.embed_dim)
    n_chunks = build_chunks(driver, settings.embed_model, settings.embed_dim)
    logger.info("Built %d :Chunk nodes", n_chunks)

    driver.close()
    logger.info("Ingest complete for scenario=%r", scenario)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest CELLAR data into Neo4j")
    parser.add_argument("--scenario", default="negotiation", help="Scenario name")
    parser.add_argument("--dump", default=None, help="Path to local RDF .nt dump file")
    args = parser.parse_args()
    dump_path = Path(args.dump) if args.dump else None
    run_ingest(args.scenario, dump_path)


if __name__ == "__main__":
    main()
