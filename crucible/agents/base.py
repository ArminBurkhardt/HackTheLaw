"""ModelClient seam — the single mockable boundary around the LLM."""
from __future__ import annotations
from typing import Protocol, Callable, runtime_checkable


@runtime_checkable
class ModelClient(Protocol):
    def generate(self, *, model: str, system: str, messages: list[dict], **kw) -> str: ...


class FakeModelClient:
    """Returns canned replies from a list or a callable. Used in tests and when use_real_model=False."""

    def __init__(self, scripted: list[str] | Callable):
        if callable(scripted) and not isinstance(scripted, list):
            self._fn: Callable | None = scripted
            self._replies: list[str] = []
        else:
            self._fn = None
            self._replies = list(scripted)
        self._index = 0

    def generate(self, *, model: str, system: str, messages: list[dict], **kw) -> str:
        if self._fn is not None:
            return self._fn(model=model, system=system, messages=messages, **kw)
        if self._index >= len(self._replies):
            return self._replies[-1]  # repeat last reply if exhausted
        reply = self._replies[self._index]
        self._index += 1
        return reply


def make_client(settings) -> ModelClient:
    """Return a real Gemini client or FakeModelClient based on settings."""
    if not settings.use_real_model:
        return FakeModelClient(scripted=["[stub reply]"])
    from crucible.agents.gemini_client import GeminiModelClient
    return GeminiModelClient(settings)
