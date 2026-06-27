# Crucible ⚖️
### AI-Powered Adversarial Sparring and Coaching Ground for Junior Lawyers

*HackTheLaw Hackathon @Cambridge*

Crucible is an adversarial training ground designed for junior lawyers to practice real-world legal work. Instead of acting as an assistant that completes tasks for the user, Crucible acts as a sparring partner and a coach. The user faces an AI opponent that **fights back, refuses to fold to confidence, and exploits weak reasoning**, while a separate neutral Adjudicator/Coach measures their performance against a concrete playbook/rubric and provides **specific, grounded coaching** with stronger, cited moves.

---

## 🌟 Key Features

1. **Realistic Adversary (Opponent Agent)**: Resists multi-turn persuasion, utilizes structured concession ladders with explicit unlock conditions, enforces BATNA (Best Alternative to a Negotiated Agreement) anchoring, and never breaks character to coach.
2. **Standard-Based Rubric (Adjudicator & Coach)**: Performance is evaluated against a concrete, structured playbook/rubric (not just generic vibes) after each round.
3. **Structured & Grounded Feedback**: The Coach provides a complete debrief, highlighting specific errors, score breakdowns, and suggesting cited legal moves.
4. **EU Law (CELLAR) GraphRAG Grounding**: Deep semantic search and structural knowledge retrieval from the official European EU Law portal (CELLAR) using SPARQL and Neo4j.
5. **Self-Entropy-Coded Verification (SECV)**: A custom verification mechanism that checks citation validity, reduces LLM hallucinations, and provides cost-controlled verification on legal citations and claims.
6. **Unified Web UI**: An interactive arena with a real-time tension meter, detailed debrief panels, rubric breakdowns, and historical performance tracking.

---

## 🏗️ Repository Architecture

Crucible is designed with strict separation of concerns:
```
crucible/               # Core business logic & AI Agents
    agents/             # Opponent, Adjudicator, Coach, Architect, Tuner agents
    grounding/          # GraphRAG (CELLAR via SPARQL & Neo4j) & commentary (Perplexity)
    scenarios/          # Scenario playbooks (negotiations, difficult client, hot seat)
    verify/             # SECV (Self-Entropy-Coded Verification) implementation
server/                 # FastAPI WebSocket & REST backend
web/                    # React / Vite / Tailwind CSS modern frontend application
tests/                  # Mocked unit tests & Live integration test suite
plans/                  # Stage-by-stage implementation specifications
```

---

## 🛠️ Prerequisites

Ensure you have the following installed on your system:
- **Python 3.12+**
- **Node.js & npm** (v18+ recommended)
- **Docker & Docker Compose** (for running Neo4j)
- **Google Cloud CLI** configured with Vertex AI access in `europe-west1`

---

## ⚙️ Installation & Setup

### 1. Clone & Set Up the Python Environment
Clone the repository and set up a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the package in editable development mode with dev dependencies
make install
```

### 2. Set Up the Frontend
Install Node.js dependencies for the web interface:

```bash
cd web
npm install
cd ..
```

### 3. Spin Up Neo4j Graph Database
Crucible uses Neo4j for GraphRAG grounding. You can spin up the pre-configured Neo4j community server with Docker Compose (includes APOC and Graph Data Science plugins):

```bash
make neo4j
```
*The Neo4j browser UI will be accessible at [http://localhost:7474](http://localhost:7474) and Bolt connection at `bolt://localhost:7687`.*

---

## 📝 Environment Configuration (`.env`)

Create a `.env` file in the root directory of the project. It is used by `crucible/config.py` to configure API keys, database settings, and models.

```ini
# --- Google Cloud / Vertex AI Settings ---
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=europe-west1

# --- LLM Models Configurations ---
REASONING_MODEL=gemini-2.5-pro
FAST_MODEL=gemini-2.5-flash
EMBED_MODEL=text-embedding-004
EMBED_DIM=768

# --- Perplexity AI (Current Legal Commentary) ---
PERPLEXITY_API_KEY=your-perplexity-api-key

# --- Neo4j Graph Database Settings ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=crucible-dev

# --- Feature Flags ---
OPPONENT_SPOT_THE_BAD_CITATION=true
```

---

## 🚀 Running the Application

### 1. Start the Backend API Server
The backend runs on FastAPI with WebSockets for real-time turn exchange in the Arena.

```bash
make dev
```
*The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).*

### 2. Start the Frontend Dev Server
Run the Vite development server to launch the Crucible user interface:

```bash
cd web
npm run dev
```
*Open your browser at the URL printed by Vite (typically [http://localhost:5173](http://localhost:5173)).*

---

## 🧪 Testing

Crucible employs strict **Test-Driven Development (TDD)**. All key interfaces and agent contracts are fully covered.

* **Mocked Test Suite** (Gates PR/merges, does not use real model API calls):
  ```bash
  make test
  ```
* **Live Test Suite** (Requires valid GCP/Vertex/Perplexity credentials):
  ```bash
  make test-live
  ```

---

## 📚 Grounding & SECV Evaluation

### Ingesting & Indexing CELLAR Scenarios
To trigger SPARQL queries to the official EU Law portal, pull case information, and index it into your local Neo4j instance for a specific scenario:
```bash
make index-cellar SCENARIO=negotiation
```

### Self-Entropy-Coded Verification (SECV) Calibration
To evaluate the SECV calibration (detecting hallucinations, evaluating AUROC, and generating confusion matrices):
```bash
make secv-eval
```

---

## 🎯 Developer Operational Guide

Refer to [CLAUDE.md](CLAUDE.md) for core operational guidelines, implementation principles, and project rules. Detailed milestones and stage specifications can be found under the [plans/](plans/README.md) directory.

