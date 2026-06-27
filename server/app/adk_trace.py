from dataclasses import dataclass, field
from typing import Any

from .schemas import GroundingSource


@dataclass
class ToolTrace:
    tools_used: list[str] = field(default_factory=list)
    sources: list[GroundingSource] = field(default_factory=list)


def trace_from_event(event: object) -> ToolTrace:
    trace = ToolTrace()
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    for part in parts:
        trace.tools_used.extend(tool_names_from_part(part))
        trace.sources.extend(sources_from_part(part))
    return dedupe_trace(trace)


def merge_traces(traces: list[ToolTrace]) -> ToolTrace:
    merged = ToolTrace()
    for trace in traces:
        merged.tools_used.extend(trace.tools_used)
        merged.sources.extend(trace.sources)
    return dedupe_trace(merged)


def tool_names_from_part(part: object) -> list[str]:
    names: list[str] = []
    for attr in ("function_call", "function_response"):
        payload = getattr(part, attr, None)
        name = getattr(payload, "name", None)
        if isinstance(name, str):
            names.append(name)

    payload = as_dict(part)
    if payload:
        names.extend(names_from_dict(payload))
    return unique(names)


def sources_from_part(part: object) -> list[GroundingSource]:
    payload = as_dict(part)
    if not payload:
        response = getattr(getattr(part, "function_response", None), "response", None)
        payload = as_dict(response) or response
    return sources_from_payload(payload)


def names_from_dict(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("function_call", "function_response"):
        item = payload.get(key)
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return unique(names)


def sources_from_payload(payload: object) -> list[GroundingSource]:
    sources: list[GroundingSource] = []
    if isinstance(payload, dict):
        raw_sources = payload.get("sources")
        if isinstance(raw_sources, list):
            sources.extend(valid_sources(raw_sources))
        for value in payload.values():
            sources.extend(sources_from_payload(value))
    elif isinstance(payload, list):
        for item in payload:
            sources.extend(sources_from_payload(item))
    return dedupe_sources(sources)


def valid_sources(items: list[object]) -> list[GroundingSource]:
    sources: list[GroundingSource] = []
    for item in items:
        try:
            sources.append(GroundingSource.model_validate(item))
        except Exception:
            if isinstance(item, str):
                sources.append(GroundingSource(title=item, url=item))
    return sources


def as_dict(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        return dumped if isinstance(dumped, dict) else None
    return None


def dedupe_trace(trace: ToolTrace) -> ToolTrace:
    return ToolTrace(tools_used=unique(trace.tools_used), sources=dedupe_sources(trace.sources))


def dedupe_sources(sources: list[GroundingSource]) -> list[GroundingSource]:
    seen: set[tuple[str, str | None]] = set()
    unique_sources: list[GroundingSource] = []
    for source in sources:
        key = (source.title, source.url)
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)
    return unique_sources


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
