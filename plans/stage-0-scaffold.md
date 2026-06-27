# Stage 0 — Scaffold

**Goal:** a runnable skeleton. One stub agent round-trips a message through the ADK Runner and into the React Arena. No real legal logic yet.

**Prerequisites:** none (this is the first stage). You need a Google Cloud project with Vertex AI enabled, or a Gemini API key, to hit a model. If neither is available yet, stub the model call behind an interface and return a canned reply so the round-trip still works (see "Fallback" below).

**Estimated size:** ~½ day.

---

## 1. Confirm/pin model strings first (blocking)

Model strings move fast (spec §3, §13). Before writing any agent code:

1. Run a Model Garden / API check for the strings in the spec: `gemini-3.1-pro`, `gemini-3-flash` (or `3.5-flash`).
2. If a string isn't GA/available in `europe-west1`, fall back to `gemini-2.5-pro` (GA) and a `2.5-flash` equivalent.
3. **Pin the resolved strings in `crucible/config.py`.** Agents read from config — never hardcode a model name in an agent module.

Record what you pinned and why in [../MEMORY.md](../MEMORY.md).

## 2. Files to create

```
pyproject.toml              # python 3.12, deps: google-adk, fastapi, uvicorn, pydantic, pyyaml, python-dotenv, pytest, httpx
.env.example                # all keys from spec §11, no values
Makefile                    # dev, test (more targets added in later stages)
crucible/__init__.py
crucible/config.py          # Settings (pydantic-settings): model strings, region, flags; reads env
crucible/schemas.py         # ALL Pydantic models from spec §6, verbatim — define them now, use later
crucible/agents/__init__.py
crucible/agents/base.py     # thin wrapper around ADK LlmAgent + a ModelClient interface (so it's mockable)
crucible/runner.py          # ADK Runner + session creation; run_turn(session_id, user_msg) -> str
server/__init__.py
server/app.py               # FastAPI: GET /health, WS /round/{id}/turn (echo via runner)
web/                        # Vite + React + Tailwind skeleton
  src/main.tsx, src/App.tsx, src/Arena.tsx, src/lib/ws.ts
tests/__init__.py
tests/conftest.py           # fixtures: fake model client, test settings
tests/test_scaffold.py      # the gate test (write FIRST)
```

## 3. `config.py` shape

Use `pydantic-settings`. Required fields (defaults where sensible):

```python
class Settings(BaseSettings):
    reasoning_model: str          # pinned in step 1
    fast_model: str
    google_cloud_project: str | None = None
    google_cloud_location: str = "europe-west1"
    perplexity_api_key: str | None = None
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    embed_model: str = "text-embedding"
    entailment_model: str | None = None     # defaults to fast_model if None
    # feature flags
    opponent_spot_the_bad_citation: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

`crucible/schemas.py`: copy **all** models from spec §6 (`Authority`, `CitationCheck`, `PlaybookItem`, `Playbook`, `ConcessionRung`, `OpponentPlaybook`, `MoveEvent`, `Debrief`, `UserProfile`). They are needed across every later stage; defining them now means no schema churn later. Add nothing extra yet.

## 4. The model-client seam (critical for testability)

All later stages mock the model boundary (spec §11). Establish it now:

```python
# crucible/agents/base.py
class ModelClient(Protocol):
    def generate(self, *, model: str, system: str, messages: list[dict], **kw) -> str: ...

class FakeModelClient:                 # used in deterministic tests
    def __init__(self, scripted: list[str] | Callable): ...
    def generate(self, **kw) -> str: ...   # pops/looks up a canned reply

def make_client(settings) -> ModelClient:  # real ADK/Gemini client or FakeModelClient
    ...
```

`runner.py` and every agent take a `ModelClient` (dependency-injected), never a global. This is the single most important structural decision in Stage 0 — get it right and every later test is cheap.

## 5. Frontend skeleton

- Vite + React + TS + Tailwind. One screen: `Arena.tsx` with a message list, an input box, and a WebSocket client (`lib/ws.ts`) to `/round/{id}/turn`.
- Keep it minimal but **lay the routing seam**: `App.tsx` should have a notion of app phase (`setup | arena | debrief | progress`) even if only `arena` is wired. Later stages fill the others without restructuring. This serves the "one cohesive app" UX north star (see [README.md](README.md)).

## 6. Test (write this FIRST, watch it fail, then build)

```python
# tests/test_scaffold.py
def test_runner_roundtrips_message():
    settings = test_settings()
    client = FakeModelClient(scripted=["pong"])
    runner = make_runner(settings, client)
    reply = runner.run_turn(session_id="s1", user_msg="ping")
    assert reply == "pong"
```

Optionally add an httpx WebSocket test that the FastAPI `/round/{id}/turn` endpoint echoes a model reply, using the fake client via dependency override.

## Fallback if no model access yet

Runtime uses the real Gemini client; deterministic tests inject `FakeModelClient` directly. The round-trip (UI → WS → Runner → agent → client → back) is the thing being proven.

## ✅ Done when

A message typed in the React Arena travels over the WebSocket, through the ADK Runner into the stub agent, and the reply renders back in the Arena — and `tests/test_scaffold.py` is green.

## Update before moving on

- [../MEMORY.md](../MEMORY.md): pinned model strings + region, whether real model access exists, any ADK/Vertex setup gotchas, exact dep versions installed.
