from __future__ import annotations

from typing import Any

from crucible.config import Settings
from crucible.grounding.cellar.tools import cellar_search
from crucible.grounding.perplexity import make_perplexity_client
from crucible.grounding.source_policy import load_source_policy
from crucible.schemas import Playbook


def build_round_context(
    *,
    playbook: Playbook,
    transcript: list[dict],
    move_events: list,
    current_position: float,
    persona_name: str,
    settings: Settings,
    round_complete: bool = False,
    abort_reason: str | None = None,
) -> dict[str, Any]:
    latest_user = _latest(transcript, "user")
    query = latest_user or playbook.matter_summary
    sources, tools = collect_grounding(
        query=query,
        settings=settings,
        use_cellar=_has_celex_authorities(playbook),
    )
    return {
        "scenario": playbook.scenario,
        "persona": persona_name,
        "current_position": current_position,
        "latest_user": latest_user,
        "latest_opponent": _latest(transcript, "assistant"),
        "last_move": move_events[-1].model_dump() if move_events else None,
        "round_complete": round_complete,
        "abort_reason": abort_reason,
        "hooks": [_hook(item) for item in playbook.items[:5]],
        "tools": tools,
        "sources": sources,
    }


def collect_grounding(
    *,
    query: str,
    settings: Settings,
    use_cellar: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    tools = [
        {"name": "perplexity_search", "configured": bool(settings.perplexity_api_key), "status": "not_configured"},
    ]
    if use_cellar:
        tools.append(
            {"name": "neo4j_cellar", "configured": _neo4j_configured(settings), "status": "not_configured"}
        )

    if settings.perplexity_api_key:
        try:
            policy = load_source_policy(settings.allowed_sources_path)
            results = make_perplexity_client(settings.perplexity_api_key).search(
                _perplexity_query(query, policy.allowed_domains),
                max_results=8,
            )
            tools[0]["status"] = "ok"
            all_allowed_results = [result for result in results if policy.allows(result.url)]
            filtered_count = len(results) - len(all_allowed_results)
            allowed_results = all_allowed_results[:3]
            tools[0]["allowed_domains"] = list(policy.allowed_domains)
            if filtered_count:
                tools[0]["filtered"] = filtered_count
            sources.extend(
                {
                    "tool": "perplexity_search",
                    "title": result.title or result.url,
                    "url": result.url,
                    "snippet": result.snippet,
                }
                for result in allowed_results
            )
        except Exception as error:
            tools[0]["status"] = "error"
            tools[0]["detail"] = str(error)

    if use_cellar and _neo4j_configured(settings):
        try:
            from crucible.grounding.cellar.neo4j_store import make_neo4j_store

            store = make_neo4j_store(settings.neo4j_uri or "", settings.neo4j_user or "", settings.neo4j_password or "")
            try:
                hits = cellar_search(store, query, top_k=3)
            finally:
                store.close()
            tools[-1]["status"] = "ok"
            sources.extend(
                {
                    "tool": "neo4j_cellar",
                    "title": authority.title,
                    "url": authority.eli,
                    "pinpoint": authority.pinpoint,
                    "snippet": snippet,
                }
                for authority, snippet in hits
            )
        except Exception as error:
            tools[-1]["status"] = "error"
            tools[-1]["detail"] = str(error)

    return sources, tools


def _neo4j_configured(settings: Settings) -> bool:
    return bool(settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password)


def _perplexity_query(query: str, allowed_domains: tuple[str, ...]) -> str:
    domains = ", ".join(allowed_domains)
    return (
        f"{query}\n\n"
        "Use only official legal or regulatory sources from these allowed domains: "
        f"{domains}. Do not use Wikipedia, Reddit, blogs, forums, or vendor marketing pages."
    )


def _has_celex_authorities(playbook: Playbook) -> bool:
    if any(authority.celex for authority in playbook.authorities):
        return True
    return any(authority.celex for item in playbook.items for authority in item.authorities)


def _latest(transcript: list[dict], role: str) -> str:
    for message in reversed(transcript):
        if message.get("role") == role:
            return str(message.get("content", ""))
    return ""


def _hook(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "label": item.label,
        "kind": item.kind,
        "target": item.target,
        "authorities": [auth.model_dump() for auth in item.authorities[:2]],
    }
