"""Perplexity search client — current-context commentary, not black-letter law.

The real client calls the Perplexity sonar API using the OpenAI-compatible
chat completions endpoint with `return_citations=True`. Results are flagged
as `source="perplexity"` (not structurally resolvable → coaching commentary).

Secrets rule: PERPLEXITY_API_KEY is server-side only; never shipped to web/.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PerplexityResult:
    title: str
    url: str
    snippet: str
    date: str | None = None


@runtime_checkable
class PerplexityClient(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[PerplexityResult]: ...


class FakePerplexityClient:
    """Returns empty results — used in tests and when no API key is configured."""

    def search(self, query: str, max_results: int = 5) -> list[PerplexityResult]:
        return []


class RealPerplexityClient:
    """HTTP client for the Perplexity sonar-pro API.

    Uses the OpenAI-compatible chat completions endpoint with citation extraction.
    """

    _ENDPOINT = "https://api.perplexity.ai/chat/completions"
    _MODEL = "sonar-pro"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def search(self, query: str, max_results: int = 5) -> list[PerplexityResult]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._MODEL,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1024,
            "return_citations": True,
        }
        resp = httpx.post(self._ENDPOINT, headers=headers, json=body, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        # The sonar API returns `citations` as a list of URLs; richer metadata
        # may be in `search_results` depending on API version.
        citations: list[dict] = data.get("citations", [])
        search_results: list[dict] = data.get("search_results", [])

        results: list[PerplexityResult] = []
        if search_results:
            for item in search_results[:max_results]:
                results.append(PerplexityResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    date=item.get("date"),
                ))
        else:
            # Fallback: citations are just URLs; build minimal results
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            for url in citations[:max_results]:
                results.append(PerplexityResult(
                    title="",
                    url=str(url),
                    snippet=content[:300] if not results else "",
                ))

        return results


def make_perplexity_client(api_key: str | None) -> PerplexityClient:
    """Return a real client if api_key is set, otherwise a no-op fake."""
    if not api_key:
        return FakePerplexityClient()
    return RealPerplexityClient(api_key)
