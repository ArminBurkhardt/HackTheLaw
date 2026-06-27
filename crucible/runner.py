"""CrucibleRunner — wraps the model client and manages per-session message history.

Stage 0: thin wrapper over ModelClient. Stage 1 will wire in ADK LlmAgent + session state.
"""
from __future__ import annotations
from crucible.config import Settings
from crucible.agents.base import ModelClient

_SYSTEM_STUB = "You are a legal opponent in an adversarial training scenario."


class CrucibleRunner:
    def __init__(self, settings: Settings, client: ModelClient) -> None:
        self._settings = settings
        self._client = client
        self._sessions: dict[str, list[dict]] = {}

    def run_turn(self, session_id: str, user_msg: str) -> str:
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_msg})
        reply = self._client.generate(
            model=self._settings.fast_model,
            system=_SYSTEM_STUB,
            messages=list(history),
        )
        history.append({"role": "assistant", "content": reply})
        return reply


def make_runner(settings: Settings, client: ModelClient) -> CrucibleRunner:
    return CrucibleRunner(settings, client)
