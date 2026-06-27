import asyncio
from typing import Any, Protocol

import httpx

from .schemas import GroundingSource, ToolAvailability
from .settings import Settings


class ProviderResult:
    def __init__(self, answer: str, sources: list[GroundingSource]) -> None:
        self.answer = answer
        self.sources = sources


class GroundingProvider(Protocol):
    name: str

    def availability(self) -> ToolAvailability: ...
    async def ground(self, query: str) -> ProviderResult: ...


class PerplexityProvider:
    name = "perplexity_search"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def availability(self) -> ToolAvailability:
        if self._settings.perplexity_api_key:
            return ToolAvailability(
                name=self.name,
                configured=True,
                status="ready",
                detail=f"Perplexity model {self._settings.perplexity_model} is configured.",
            )
        return ToolAvailability(
            name=self.name,
            configured=False,
            status="missing_config",
            detail="Set PERPLEXITY_API_KEY on the backend service.",
        )

    async def ground(self, query: str) -> ProviderResult:
        if not self._settings.perplexity_api_key:
            raise ProviderUnavailable("PERPLEXITY_API_KEY is not configured.")

        async with httpx.AsyncClient(timeout=self._settings.grounding_timeout_seconds) as client:
            response = await client.post(
                "https://api.perplexity.ai/v1/sonar",
                headers={
                    "Authorization": f"Bearer {self._settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._settings.perplexity_model,
                    "messages": [{"role": "user", "content": query}],
                },
            )
            response.raise_for_status()
            payload = response.json()

        return ProviderResult(answer=extract_answer(payload), sources=extract_sources(payload))


class Neo4jCellarProvider:
    name = "neo4j_cellar"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def availability(self) -> ToolAvailability:
        if self._settings.neo4j_configured:
            return ToolAvailability(
                name=self.name,
                configured=True,
                status="ready",
                detail="Neo4j URI/user/password are configured for CELLAR grounding.",
            )
        return ToolAvailability(
            name=self.name,
            configured=False,
            status="missing_config",
            detail="Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD on the backend service.",
        )

    async def ground(self, query: str) -> ProviderResult:
        if not self._settings.neo4j_configured:
            raise ProviderUnavailable("Neo4j CELLAR credentials are not configured.")
        return await query_neo4j(self._settings, query)


def adk_availability(settings: Settings) -> ToolAvailability:
    if settings.runner_backend == "adk" and settings.adk_model and settings.google_configured:
        return ToolAvailability(
            name="google_adk_runtime",
            configured=True,
            status="ready",
            detail=f"Google ADK runner is selected with model {settings.adk_model}.",
        )
    if settings.runner_backend == "adk":
        return ToolAvailability(
            name="google_adk_runtime",
            configured=False,
            status="missing_config",
            detail="Set CRUCIBLE_ADK_MODEL when CRUCIBLE_RUNNER=adk.",
        )
    if settings.runner_backend == "adk":
        return ToolAvailability(
            name="google_adk_runtime",
            configured=False,
            status="missing_config",
            detail="Set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT/GOOGLE_CLOUD_LOCATION for Google ADK.",
        )
    return ToolAvailability(
        name="google_adk_runtime",
        configured=False,
        status="disabled",
        detail="Set CRUCIBLE_RUNNER=adk to use Google ADK.",
    )


class ProviderUnavailable(RuntimeError):
    pass


def extract_answer(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    if isinstance(payload.get("answer"), str):
        return payload["answer"]
    return "Perplexity returned no answer text."


def extract_sources(payload: dict[str, Any]) -> list[GroundingSource]:
    citations = payload.get("citations", [])
    if not isinstance(citations, list):
        return []
    return [source_from_citation(item) for item in citations[:8]]


def source_from_citation(item: Any) -> GroundingSource:
    if isinstance(item, str):
        return GroundingSource(title=item, url=item)
    if isinstance(item, dict):
        title = str(item.get("title") or item.get("url") or "Perplexity citation")
        url = item.get("url")
        snippet = item.get("snippet") or item.get("text")
        return GroundingSource(title=title, url=url, snippet=snippet)
    return GroundingSource(title=str(item))


async def query_neo4j(settings: Settings, query: str) -> ProviderResult:
    return await asyncio.to_thread(query_neo4j_sync, settings, query)


def query_neo4j_sync(settings: Settings, query: str) -> ProviderResult:
    from neo4j import GraphDatabase

    cypher = """
    MATCH (n)
    WHERE any(k IN keys(n) WHERE toLower(toString(n[k])) CONTAINS toLower($search))
    RETURN labels(n) AS labels, properties(n) AS properties
    LIMIT 5
    """
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    try:
        with driver.session() as session:
            records = list(session.run(cypher, search=query))
    finally:
        driver.close()

    sources = [
        GroundingSource(
            title=", ".join(record["labels"]) or "Neo4j node",
            snippet=str(record["properties"])[:500],
        )
        for record in records
    ]
    answer = f"Neo4j returned {len(sources)} candidate CELLAR node(s)."
    return ProviderResult(answer=answer, sources=sources)
