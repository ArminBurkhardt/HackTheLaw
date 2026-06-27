"""CELLAR SPARQL / REST harvest — INGEST ONLY.

Queries the EUR-Lex SPARQL endpoint to discover CELEX numbers for a
scenario sub-corpus and to fetch metadata. Results feed into mtd_stream
and neo4j_loader — never into runtime agents.

Rate-limit rules (spec §7.1):
  - 60-second timeout per query
  - Max 5 concurrent requests
  - LIMIT/OFFSET pagination
  - Exponential backoff on 429/503
"""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
_DEFAULT_TIMEOUT = 60
_MAX_RETRIES = 5


@dataclass
class CelexEntry:
    celex: str
    eli: str | None
    title: str
    work_type: str


def query_gdpr_subcorpus() -> list[str]:
    """Return CELEX numbers for the DPA/GDPR scenario sub-corpus.

    Includes GDPR + directly cited/related acts.
    """
    return [
        "32016R0679",  # GDPR
        "31995L0046",  # Directive 95/46/EC (repealed by GDPR)
        "32002L0058",  # ePrivacy Directive
        "32016L0680",  # Law Enforcement Directive
        "32018R1725",  # EU institutions data protection regulation
    ]


def fetch_work_metadata(
    celex: str,
    timeout: int = _DEFAULT_TIMEOUT,
) -> CelexEntry | None:
    """Fetch basic metadata for a single CELEX number from the SPARQL endpoint."""
    import httpx

    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?eli ?title ?type WHERE {{
      ?work cdm:work_has_resource-type_eurovoc_concept.0.identifier "{celex}" ;
            dcterms:title ?title .
      OPTIONAL {{ ?work cdm:work_id_document_eli ?eli }}
      OPTIONAL {{ ?work cdm:work_has_resource-type.0.identifier ?type }}
      FILTER(lang(?title) = "en")
    }} LIMIT 1
    """

    for attempt in range(_MAX_RETRIES):
        try:
            resp = httpx.get(
                _SPARQL_ENDPOINT,
                params={"query": query, "format": "application/sparql-results+json"},
                timeout=timeout,
            )
            if resp.status_code in (429, 503):
                wait = 2 ** attempt
                logger.warning("Rate limited (%d); waiting %ds", resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            bindings = data.get("results", {}).get("bindings", [])
            if not bindings:
                return None
            b = bindings[0]
            return CelexEntry(
                celex=celex,
                eli=b.get("eli", {}).get("value"),
                title=b.get("title", {}).get("value", ""),
                work_type=b.get("type", {}).get("value", "").rsplit("/", 1)[-1],
            )
        except Exception as exc:
            if attempt == _MAX_RETRIES - 1:
                logger.error("Failed to fetch %s: %s", celex, exc)
                return None
            time.sleep(2 ** attempt)
    return None
