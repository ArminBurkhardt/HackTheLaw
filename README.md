# Crucible

[![CI](https://github.com/ArminBurkhardt/HackTheLaw/actions/workflows/ci.yml/badge.svg)](https://github.com/ArminBurkhardt/HackTheLaw/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)

Crucible is an adversarial legal training app built for the HackTheLaw hackathon.
It gives junior lawyers repeatable practice at the parts of lawyering that are
hard to learn from a textbook: negotiating under pressure, holding a position,
using legal authority correctly, and learning from a specific debrief after the
round ends.

Instead of acting as a legal assistant, Crucible acts as the other side. The AI
opponent argues, resists, probes weak reasoning, and only concedes when the user
earns it. A separate adjudicator and coach then score the round against a written
playbook and explain what the user should do differently next time.

## Hackathon Challenge

We chose Legora's **The Sparring Room** challenge.

Our selected arena is **the negotiation table**: the user negotiates a SaaS
liability clause against an AI counterparty that is trying to preserve a
provider-friendly position. The current demo focuses on this negotiation scenario
because it gives judges a concrete, replayable adversarial loop:

1. Read a short matter brief and legal strategy notes.
2. Enter a multi-turn negotiation against an AI opponent persona.
3. Try to improve the commercial/legal outcome without overplaying the hand.
4. End the round and receive a scored debrief with concrete coaching.
5. Run again and try to beat the previous score.

## What It Demonstrates

- **Realistic adversary**: the opponent has a concession ladder, BATNA pressure,
  persona behavior, and instructions not to coach or fold too early.
- **Measurable standard**: the adjudicator scores each user move against a
  scenario playbook with weighted criteria.
- **Specific coaching**: the debrief identifies missed points, early concessions,
  overplayed arguments, the turning point, and stronger alternative moves.
- **Grounded legal material**: the project includes EU law grounding through
  CELLAR/SPARQL, Neo4j graph storage, source policy checks, and citation
  verification.
- **Replayable UI**: the web app supports scenario setup, persona and hardness
  selection, live arena turns, debrief review, and progress tracking.

## Tech Stack

| Area | Tools and frameworks |
| --- | --- |
| Backend API | Python 3.12, FastAPI, Uvicorn, WebSockets, Pydantic |
| Agent orchestration | Custom opponent, adjudicator, coach, architect, and tuner agents |
| LLM provider | Google Gemini via `google-genai`, Google ADK, and Vertex AI configuration |
| Legal grounding | EU Publications Office CELLAR SPARQL, Neo4j, custom source policy checks |
| Verification | Self-Entropy-Coded Verification (SECV), citation checks, entailment hooks |
| Persistence | SQLite-backed user progress and profile memory |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Testing | Pytest, pytest-asyncio, Vite/TypeScript build checks |
| Infrastructure | Docker Compose for Neo4j, GitHub Actions CI |

## Repository Layout

```text
crucible/
  agents/       Opponent, adjudicator, coach, architect, and difficulty tuner
  grounding/    CELLAR, Neo4j, source policy, and commentary integrations
  scenarios/    Scenario playbooks and fixtures
  verify/       SECV and citation verification code
server/         FastAPI REST and WebSocket backend
web/            React/Vite frontend
tests/          Mocked unit tests plus opt-in live integration tests
plans/          Hackathon implementation notes and staged design plans
```

## Quick Start

### 1. Install the Python backend

```bash
python -m venv venv
source venv/bin/activate
make install
```

### 2. Install the frontend

```bash
cd web
npm install
cd ..
```

### 3. Configure environment variables

Create a `.env` file in the repository root:

```ini
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=europe-west1
GOOGLE_API_KEY=your-google-api-key

REASONING_MODEL=gemini-3.1-pro-preview
FAST_MODEL=gemini-3.5-flash
SESSION_PREP_MODEL=gemini-3.1-flash-lite
TURN_RATING_MODEL=gemini-3.1-flash-lite

PERPLEXITY_API_KEY=your-perplexity-api-key

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=crucible-dev
```

The mocked test suite does not require live model credentials. Live model and
grounding features require the relevant Google/Vertex, Perplexity, and Neo4j
configuration.

### 4. Start Neo4j for graph grounding

```bash
make neo4j
```

Neo4j Browser runs at [http://localhost:7474](http://localhost:7474), and the
Bolt endpoint is `bolt://localhost:7687`.

### 5. Run the app

In one terminal:

```bash
make dev
```

In another terminal:

```bash
cd web
npm run dev
```

Open the Vite URL, usually [http://localhost:5173](http://localhost:5173).

## Testing

Run the mocked backend test suite:

```bash
make test
```

Run frontend checks:

```bash
cd web
npm run typecheck
npm run build
```

Run opt-in live tests when credentials are configured:

```bash
make test-live
```

The GitHub Actions workflow runs the mocked Python tests and the frontend
typecheck/build on every push and pull request.

## Useful Commands

```bash
make install
make dev
make test
make test-live
make neo4j
make index-cellar SCENARIO=negotiation
make secv-eval
```

## Current Demo Scope

Implemented for the hackathon demo:

- Negotiation-table arena for a SaaS liability clause.
- Opponent personas and hardness controls.
- Turn-by-turn adjudication and position movement.
- Final debrief with score, breakdown, turning point, and stronger moves.
- Progress tracking across rounds for the demo user.
- Optional CELLAR/Neo4j grounding and citation verification.
- Optional live audio path for speech-based practice.

Not yet implemented as full production features:

- Fully selectable non-negotiation arenas in the API.
- Hosted authentication and multi-user account management.
- Production deployment hardening.

## License

This hackathon project does not currently declare an open-source license. Add one
before distributing or reusing the code outside the team.
