from collections.abc import Callable
from typing import Any

import httpx

from .grounding_providers import PERPLEXITY_TRUSTED_DOMAINS, extract_answer, extract_sources, query_neo4j_sync
from .settings import Settings


def build_grounding_tools(settings: Settings) -> list[Callable[[str], dict[str, Any]]]:
    return [
        perplexity_search_tool(settings),
        neo4j_cellar_tool(settings),
    ]


def perplexity_search_tool(settings: Settings) -> Callable[[str], dict[str, Any]]:
    def perplexity_search(query: str) -> dict[str, Any]:
        """Search current external sources for legal grounding and citations."""
        if not settings.perplexity_api_key:
            return {"status": "missing_config", "answer": "PERPLEXITY_API_KEY is not configured.", "sources": []}

        try:
            with httpx.Client(timeout=settings.grounding_timeout_seconds) as client:
                response = client.post(
                    "https://api.perplexity.ai/v1/sonar",
                    headers={
                        "Authorization": f"Bearer {settings.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.perplexity_model,
                        "messages": [{"role": "user", "content": query}],
                        "search_domain_filter": PERPLEXITY_TRUSTED_DOMAINS,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            return {"status": "error", "answer": f"Perplexity grounding failed: {error}", "sources": []}

        return {
            "status": "ok",
            "answer": extract_answer(payload),
            "sources": [source.model_dump() for source in extract_sources(payload)],
        }

    return perplexity_search


def neo4j_cellar_tool(settings: Settings) -> Callable[[str], dict[str, Any]]:
    def neo4j_cellar(query: str) -> dict[str, Any]:
        """Search the local Neo4j EU CELLAR graph for treaty, regulation, concept, and citation context."""
        if not settings.neo4j_configured:
            return {"status": "missing_config", "answer": "Neo4j CELLAR credentials are not configured.", "sources": []}

        try:
            result = query_neo4j_sync(settings, query)
        except Exception as error:
            return {"status": "error", "answer": f"Neo4j CELLAR grounding failed: {error}", "sources": []}
        return {
            "status": "ok",
            "answer": result.answer,
            "sources": [source.model_dump() for source in result.sources],
        }

    return neo4j_cellar
