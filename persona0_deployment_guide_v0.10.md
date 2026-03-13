# PERSONA0 — Deployment & Testing Guide

**For Students with LLM Experience and Limited Programming Background**
*v0.17 — Based on [github.com/jamie-bear/persona0](https://github.com/jamie-bear/persona0)*

---

## Table of Contents

1. [Before You Begin](#1--before-you-begin)
2. [Getting the Code](#2--getting-the-code)
3. [Understanding the Architecture](#3--understanding-the-architecture)
4. [Local Development Deployment](#4--local-development-deployment)
5. [Inspecting Results and Testing the Thesis](#5--inspecting-results-and-testing-the-thesis)
6. [Enabling a Real LLM (Optional)](#6--enabling-a-real-llm-optional)
7. [Production Deployment (Advanced)](#7--production-deployment-advanced)
8. [Troubleshooting](#8--troubleshooting)
9. [Quick Reference](#9--quick-reference)
- [Glossary](#glossary)

---

## 1 — Before You Begin

### 1.1  What Is Persona0?

Persona0 is a research project that tests a bold idea about AI identity. Consumer LLM products like ChatGPT or Claude start fresh every conversation — they have no memory of you between sessions. Persona0 proposes a different model:

Rather than asking the language model to "remember" things (which is unreliable and expensive), Persona0 builds a separate engine that stores the agent's memories, emotional states, goals, and self-beliefs externally. The LLM is relegated to a single job: turning that stored state into natural-sounding language. Everything else — what the agent remembers, how it feels, what it wants — lives in deterministic Python code, not inside the model's weights.

> 🧠 **CONCEPT — LLM as Renderer**
> Think of it like a film: the script, sets, and characters are written by the director (the Ego Engine). The actor (the LLM) just delivers the lines naturally. The actor does not own the story.

---

### 1.2  The Project's Thesis

The central claim Persona0 is testing is:

> *"Human-like continuity emerges from externalized autobiographical state, affective regulation, and time-based cognitive updates; language models should express this state, not own it."*

When you deploy and run Persona0, you are essentially running an experiment to test whether this thesis holds up. Can a chatbot feel coherent and continuous across sessions when its "mind" is externalized? The test results — memory coherence scores, identity stability scores, and policy violation rates — are the evidence for or against the thesis.

---

### 1.3  What You Will Do in This Guide

This guide will walk you through four phases:

1. Install the prerequisites on your computer.
2. Clone the repository and configure it locally.
3. Run the system in development mode (no real LLM needed).
4. Inspect the results to test the thesis.

> 📌 **NOTE**
> This guide focuses on local development mode. Production Kubernetes deployment is covered in Section 7, but requires Docker and cloud infrastructure knowledge. Start with Sections 1–5 first.

---

### 1.4  Prerequisites Checklist

Before starting, confirm you have the following. You do not need to understand them deeply — just ensure they are installed.

| Requirement | Details |
|---|---|
| **Python 3.11+** | The programming language Persona0 is written in. Version 3.11 or newer is required. Check by running: `python --version` |
| **Git** | The tool for downloading ("cloning") the repository from GitHub. Check: `git --version` |
| **A terminal** | On macOS: Terminal app. On Windows: PowerShell or Windows Terminal. On Linux: any terminal. |
| **~500 MB disk** | For Python dependencies. No GPU or special hardware required. |
| **(Optional) Docker** | Only needed for Section 7 (production deployment). You can skip this for now. |

> 💡 **TIP**
> If you are unsure whether Python 3.11 is installed, type `python3 --version` or `python --version` into your terminal. If you see a version below 3.11, visit [python.org/downloads](https://python.org/downloads) to upgrade.

---

## 2 — Getting the Code

### 2.1  Clone the Repository

Open your terminal and run the following commands one at a time. A command preceded by a `#` symbol is a comment — you do not need to type it.

```bash
# Step 1: Download (clone) the repository from GitHub
git clone https://github.com/jamie-bear/persona0.git

# Step 2: Enter the project folder
cd persona0

# Step 3: Confirm you can see the files
ls
```

You should see folders including `src/`, `config/`, `tests/`, and files like `Dockerfile`, `Makefile`, and `pyproject.toml`. If you see these, the clone was successful.

---

### 2.2  Create a Python Virtual Environment

A virtual environment is an isolated Python installation just for this project. It prevents Persona0's dependencies from interfering with other Python software on your machine.

```bash
# Create a virtual environment called .venv
python3 -m venv .venv

# Activate it (macOS / Linux)
source .venv/bin/activate

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

Once activated, your terminal prompt will show `(.venv)` at the start. This means all Python commands now use the isolated environment.

> 💡 **TIP**
> Always activate the virtual environment before working with Persona0. If you open a new terminal window, you will need to run the activation command again.

---

### 2.3  Install Dependencies

Persona0 depends on a small number of Python libraries. Install them with:

```bash
# Install the project and all development dependencies
pip install -e .[dev]
```

This uses pip (Python's package installer) to install Persona0 in "editable" mode along with testing tools. The core libraries installed are:

| Library | Purpose |
|---|---|
| `pydantic` | Validates data shapes. Ensures the agent's state always matches the expected structure. |
| `pydantic-settings` | Reads configuration from environment variables and files. |
| `pyyaml` | Reads YAML configuration files (`config/*.yaml`). |
| `rich` | Formats the CLI trace viewer output with colour and tables. |
| `pytest` / `pytest-asyncio` | Runs the automated test suite. |

> ⚠️ **WARNING**
> Do not skip the `[dev]` part of `pip install -e .[dev]`. Without it, the testing tools (pytest etc.) will not be installed and you will not be able to run the experiments in Section 5.

---

## 3 — Understanding the Architecture

Before running anything, it helps to understand how the pieces fit together. This section explains the architecture using analogies relevant to what you already know about LLMs.

### 3.1  The Four Layers

Persona0 is organized into four layers. Think of them as nested rings around the LLM:

| Layer | Plain-English Meaning |
|---|---|
| **Memory Fabric** | The agent's long-term diary. Stores episodes (events that happened), semantic beliefs ("I value honesty"), and a self-model ("I am curious by nature"). Each memory has a lifecycle: active → cooling → archived → deleted. |
| **Ego Engine Core** | The agent's cognitive loop. Runs deterministic cycles on a schedule: fast ticks (every 30 min), slow ticks (every 3 hrs), macro ticks (daily). Each cycle reads memory, updates state, and prepares context — all without calling the LLM. |
| **Adapter Layer** | The bridge to external services. The LLM adapter sends the prepared context to a language model and gets text back. The embeddings adapter converts memories to vectors for semantic search (RAG). In dev mode, both adapters use deterministic fallbacks — no real LLM needed. |
| **Runtime & Ops** | The infrastructure layer. A scheduler runs the cognitive loop continuously. Health probes check liveness. Logs record every cycle for inspection. Docker and Kubernetes manifests handle production deployment. |

> 🧠 **CONCEPT — RAG in Persona0**
> You are already familiar with RAG (Retrieval-Augmented Generation) from products like ChatGPT with files or Gemini with Google Drive. Persona0 uses the same idea internally: when the agent receives a message, it embeds it and retrieves the most relevant memories from the episodic store. Those memories become part of the LLM's context window. The difference is that Persona0 scores memories not just by semantic similarity, but also by recency, emotional importance, goal relevance, and self-relevance — a richer retrieval strategy.

---

### 3.2  The Cognitive Cycle

The Ego Engine runs four types of cycles. Understanding these is essential for interpreting the results of your experiment:

- **`FAST_TICK`** — runs every 30 minutes by default. Updates the agent's drive states (hunger for social interaction, curiosity, rest need), ingests world events, and runs quick affect updates.
- **`SLOW_TICK`** — runs every 3 hours. Generates desires from elevated drives, reviews goals, and performs memory scoring updates.
- **`MACRO`** — runs daily. Performs deep reflection: updates the self-model, compacts memories (moves old ones to archive), and reviews long-term goals.
- **`INTERACTION`** — runs on-demand when a user sends a message. Retrieves memories, builds context, calls the LLM adapter, checks governance policy, and commits the response.

> 📌 **NOTE**
> In development mode (the default), fast and slow ticks run on an accelerated clock. You will see many cycles complete quickly. This is intentional — it lets you observe days of simulated agent life in minutes.

---

### 3.3  The Configuration System

Persona0 uses a layered configuration system. Understanding this prevents confusing errors. The layers (highest priority first) are:

1. Environment variables starting with `PERSONA0_` (e.g. `PERSONA0_LLM_ADAPTER__API_KEY`)
2. Operator override files listed in `PERSONA0_CONFIG_FILES`
3. The deployment profile file: `config/profiles/{dev|staging|prod}.yaml`
4. Immutable baseline: `config/defaults.immutable.yaml` (read-only)

The most important setting for beginners is the **profile**. The `dev` profile (the default) has the LLM adapter disabled and runs in deterministic mode — meaning the system generates scripted fallback responses instead of calling a real LLM. This is intentional: it lets you test the full architecture without needing an API key.

> 💡 **TIP**
> To switch to a real LLM (staging or prod profile), you will need to set `PERSONA0_LLM_ADAPTER__API_KEY` as an environment variable. Never put API keys in config files — the system will reject them as a security measure.

---

## 4 — Local Development Deployment

This section walks you through running Persona0 on your own machine in development mode. No cloud account, Docker, or API key is required.

### 4.1  Verify the Configuration

First, confirm that the dev profile loads correctly:

```bash
# Run the configuration validation check
python -c "from src.engine.modules._config import validate_startup_config; validate_startup_config(); print('Config OK')"
```

You should see `Config OK`. If you see an error about a missing profile or immutable defaults file, ensure you are in the `persona0/` directory and that your virtual environment is activated.

> 📌 **NOTE**
> The dev profile sets: LLM adapter `enabled = false`, `deterministic_mode = true`, and governance `enforcement_mode = audit`. This means governance violations are logged but do not block the cycle — safe for exploration.

---

### 4.2  Run the Test Suite

Before running the live system, verify that all components work correctly by running the automated tests:

```bash
# Run the full test suite
pytest

# Or use the Makefile shortcut
make test
```

You should see output ending with something like `passed in X.XXs`. If tests fail, read the error output carefully — it will point to the specific file and line number.

> 🧠 **CONCEPT — Why run tests first?**
> The test suite is not just for developers. It is your first experiment. Every test is an assertion about how the Ego Engine should behave: state should not mutate unexpectedly, rollbacks should restore the previous state, policy violations should be logged. Running the tests confirms the theoretical design is implemented correctly before you observe it live.

---

### 4.3  Run the Scheduler

The scheduler is the heart of Persona0. It continuously runs cognitive cycles on a timer. Start it with:

```bash
# Run the scheduler (press Ctrl+C to stop)
python -m src.runtime.scheduler

# Or run it for a fixed duration (e.g. 300 seconds = 5 minutes)
python -m src.runtime.scheduler --duration-seconds 300
```

The scheduler will print structured log output to the terminal. You will see cycle types (`FAST_TICK`, `SLOW_TICK`, `MACRO`), timestamps, and status indicators. Let it run for at least 5 minutes to accumulate enough cycles for meaningful analysis.

> ⚠️ **WARNING**
> The scheduler does not stop on its own unless you use `--duration-seconds`. Use `Ctrl+C` (or `Cmd+C` on macOS) to stop it gracefully. A graceful stop allows in-flight cycles to complete.

---

### 4.4  Saving Cycle Logs to a File

By default, cycle logs are written to the console. To save them for later analysis with the trace viewer, redirect the output to a file:

```bash
# Run for 5 minutes and save logs to a file
python -m src.runtime.scheduler --duration-seconds 300 2>&1 | tee cycles.jsonl

# On Windows PowerShell:
python -m src.runtime.scheduler --duration-seconds 300 | Tee-Object -FilePath cycles.jsonl
```

The cycle log file (`cycles.jsonl`) contains one JSON object per line, each representing one completed cycle. You will use this in Section 5 to inspect results.

---

### 4.5  Interacting with the Agent

The `INTERACTION` cycle type is triggered when a user sends a message. In the current codebase this is invoked programmatically — there is no chat UI yet. You can trigger an interaction cycle from Python directly:

```python
# Open a Python shell
python3

# Then run this inside the Python shell:
from src.schema.state import AgentState
from src.engine.orchestrator import EgoOrchestrator
from src.engine.default_setup import register_default_steps
from src.engine.contracts import CycleType

state = AgentState()
orch = register_default_steps(EgoOrchestrator(state))

# Trigger an interaction with a user message
result = orch.run_cycle(CycleType.INTERACTION, {"message": "How are you feeling today?"})
print(result.success)
print(result)
```

In dev mode, the response will be a deterministic fallback string rather than a real LLM response. This is expected — it lets you verify that the full interaction pipeline (retrieval, context assembly, governance check) ran correctly.

---

## 5 — Inspecting Results and Testing the Thesis

This is where the science happens. Persona0's thesis is falsifiable through observable metrics. This section explains what to look for and how to interpret it.

### 5.1  The Trace Viewer

The trace viewer is a CLI tool that renders cycle logs as a rich, colour-coded table. Run it against the log file you captured in Section 4.4:

```bash
# View the cycle log
python -m src.cli.trace_viewer cycles.jsonl
```

The trace viewer shows the following columns for each cycle:

| Column | What It Shows |
|---|---|
| **Type** | The cycle type: `FAST_TICK`, `SLOW_TICK`, `MACRO`, or `INTERACTION`. |
| **Timestamp** | When the cycle ran (UTC). |
| **Steps** | How many pipeline steps executed in this cycle. |
| **Writes** | How many state fields were modified. |
| **Before / After hash** | SHA-256 hash of the agent state before and after the cycle. If these match, the state did not change (or a rollback occurred). |
| **Status** | `OK` (green) or `ROLLBACK` (red). A rollback means something triggered a policy violation or error; the state was restored. |
| **Policy** | Whether governance policy passed, warned, or blocked the cycle's writes. |
| **Delta (top 5)** | The specific state fields that changed, showing `before → after` values. |

> 🧠 **CONCEPT — State Hashing**
> Every cycle hashes the entire agent state before and after it runs. This is similar to a blockchain: if the hash changes unexpectedly or doesn't change when it should, something is wrong. This provides a strong integrity guarantee — you can prove exactly when and how the agent's state changed.

---

### 5.2  What to Look For: Testing the Thesis

The thesis claims that continuity and personality emerge from externalized state. Here is a concrete test checklist:

#### Test 1 — State Integrity

Look at the Before / After hash columns. For successful cycles, these should differ (state changed). For rollback cycles, they should be identical (state was restored). If a rollback shows different hashes, there is a bug in the rollback logic.

- **Expected:** majority of cycles show `OK` status with different hashes.
- **Red flag:** repeated rollbacks on the same cycle type may indicate a configuration problem.

#### Test 2 — Memory Lifecycle Progression

Run the scheduler for several macro cycles (each macro cycle represents a simulated day). Then check the `MACRO` cycle rows in the trace viewer. The "Delta" column for macro cycles should show memory compaction events: memories moving from `active` to `cooling` or `archived` states.

- **Expected:** after several macro cycles, the Compacted column in the macro detail table shows non-zero values.
- **If compaction never occurs:** the memory lifecycle thresholds may need adjustment in `config/defaults.yaml`.

#### Test 3 — Rollback Correctness

Run the following Python snippet to deliberately trigger a policy violation and observe the rollback:

```python
from src.engine.contracts import CycleType, PolicyViolation
from src.schema.state import AgentState
from src.engine.orchestrator import EgoOrchestrator
from src.engine.default_setup import register_default_steps
from src.engine.cycle_log import hash_state

state = AgentState()
orch = register_default_steps(EgoOrchestrator(state))

# Record state before
before = hash_state(orch.state)

# Register a step that intentionally fails
def bad_step(state, event, pending_writes):
    state.activity.current_activity = "mutated"
    raise PolicyViolation("deliberate test violation")

orch.register_step("world_ingest", bad_step)
result = orch.run_cycle(CycleType.FAST_TICK)

after = hash_state(orch.state)
print("Rollback occurred:", not result.success)
print("State restored:", before == after)
print("Activity (should be idle):", orch.state.activity.current_activity)
```

You should see `Rollback occurred: True`, `State restored: True`, and `Activity: idle`. This confirms the transaction-safe orchestrator is working correctly — even a mid-cycle mutation is fully undone on failure.

#### Test 4 — Policy Enforcement

At the bottom of the trace viewer output, there is a **Policy Check Outcomes** table. This shows how many cycles had blocks versus warnings. In dev mode with governance set to "audit", all violations are warnings. To test the thesis about identity protection, look for:

- Whether consecutive cycles show consistent policy outcomes (identity is stable).
- Whether `MACRO` cycles show accepted reflections — these represent the agent updating its self-model.

#### Test 5 — Running the Evaluation Harness

Persona0 includes a checkpoint-aligned evaluation harness. Run the evaluation tests directly:

```bash
# Run only the evaluation tests
pytest tests/eval/ -v

# Run with verbose output to see threshold checks
pytest tests/eval/ -v --tb=short
```

The eval tests check two key metrics tied to the project's thesis:

- **Precision@5 retrieval:** of the top-5 memories retrieved for a turn, at least one must be self-relevant in over 80% of test cases. This validates the RAG strategy is doing more than keyword matching.
- **Self-belief confidence delta cap:** no single macro cycle should update a self-belief by more than `+0.15` confidence. This prevents rapid identity drift.

> 🧠 **CONCEPT — Why these metrics matter**
> These metrics are direct operationalizations of the thesis. If retrieval frequently misses self-relevant memories, the LLM will lack the context it needs to express the agent's personality — the thesis fails. If confidence deltas are uncapped, the agent's self-model can drift rapidly, again undermining continuity. Passing these tests is evidence *for* the thesis; failing them is evidence *against* it.

---

## 6 — Enabling a Real LLM (Optional)

The steps in Sections 1–5 use deterministic fallbacks for all LLM calls. This is sufficient to test the architecture's correctness. To test the full thesis — whether the persona actually feels coherent to a human — you need to wire in a real LLM. This section explains how.

### 6.1  Understanding the Adapter Architecture

The LLM adapter (`src/engine/adapters/llm.py`) is the only place in the codebase that calls an external language model. This is intentional — it enforces the thesis that the LLM is just a renderer. To use a real provider, you set environment variables rather than editing source code.

The adapter supports four providers out of the box:

| Provider | `PERSONA0_LLM_ADAPTER__PROVIDER` value | API key env var |
|----------|----------------------------------------|----------------|
| Mock (default) | `mock` | None required |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Grok (xAI) | `grok` | `XAI_API_KEY` |

All real providers include exponential back-off retry logic, token-bucket rate limiting, and optional streaming responses.

---

### 6.2  Setting the Staging Profile

The staging profile enables the LLM adapter and requires an API key. Set all required variables for your chosen provider:

```bash
# OpenAI — macOS / Linux
export PERSONA0_CONFIG_PROFILE=staging
export PERSONA0_LLM_ADAPTER__PROVIDER=openai
export OPENAI_API_KEY=your-openai-key-here

# Anthropic — macOS / Linux
export PERSONA0_CONFIG_PROFILE=staging
export PERSONA0_LLM_ADAPTER__PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-anthropic-key-here

# Grok (xAI) — macOS / Linux
export PERSONA0_CONFIG_PROFILE=staging
export PERSONA0_LLM_ADAPTER__PROVIDER=grok
export XAI_API_KEY=your-xai-key-here

# Windows PowerShell equivalents (replace export with $env:VARIABLE = 'value')
```

Then validate the configuration loads without errors:

```bash
python -c "from src.engine.modules._config import validate_startup_config; validate_startup_config(); print('Config OK')"
```

> ⚠️ **WARNING**
> Never put your API key in a config file (`config/*.yaml`). The system will actively reject this and throw an error. API keys must only be passed via environment variables. This is a security feature, not a limitation.

---

### 6.3  Configuring the Model and Options

Specify the model and optional behaviour with environment variables:

```bash
# OpenAI
export PERSONA0_LLM_ADAPTER__MODEL=gpt-4o

# Anthropic
export PERSONA0_LLM_ADAPTER__MODEL=claude-sonnet-4-20250514

# Grok (xAI)
export PERSONA0_LLM_ADAPTER__MODEL=grok-3-latest

# Enable streaming (lower time-to-first-token)
export PERSONA0_LLM_ADAPTER__STREAMING=true

# Adjust rate limit (requests per minute) if your tier allows more
export PERSONA0_LLM_ADAPTER__RATE_LIMIT_RPM=120
```

Check `config/profiles/staging.yaml` for the full list of LLM adapter options (timeout, retries, etc.).

> 📌 **NOTE**
> The adapter requires `openai` (pip install openai) or `anthropic` (pip install anthropic) to be installed for their respective providers. Grok also uses the `openai` package (it is OpenAI-compatible). These are optional dependencies — they are not installed by the default `pip install -e .[dev]` command. Install only the one you intend to use.

---

### 6.4  Testing the Full Pipeline

Once the real LLM adapter is configured, run an interaction cycle as described in Section 4.5. The response in `event['candidate_response']` will now be a genuine LLM response rather than a fallback string. You can then compare qualitative outputs across multiple sessions to assess whether the persona feels consistent — the ultimate test of the thesis.

---

## 7 — Production Deployment (Advanced)

This section is for students who want to deploy Persona0 in a containerised environment. You will need Docker installed and a basic understanding of containers. Skip this section if you just want to run experiments locally.

### 7.1  Build and Run the Docker Container

The `Dockerfile` at the root of the repository builds the production image. It uses Python 3.11-slim and runs as a non-root user for security.

```bash
# Build the image locally
docker build -t persona0:local .

# Run it with the dev profile (no LLM needed)
docker run --rm \
  -e PERSONA0_CONFIG_PROFILE=dev \
  persona0:local

# Run with a real LLM (staging profile)
docker run --rm \
  -e PERSONA0_CONFIG_PROFILE=staging \
  -e PERSONA0_LLM_ADAPTER__API_KEY=your-key \
  persona0:local
```

The container runs the scheduler as its default command (`python -m src.runtime.scheduler`). Health checks run every 30 seconds via the readiness probe.

---

### 7.2  Production Vector Store (pgvector)

The default in-memory vector store loses all embeddings on restart. For persistent semantic memory search in production, use the `PgVectorStore` backed by PostgreSQL with the pgvector extension.

**Prerequisites:**

```bash
# Install the Python drivers
pip install "psycopg[binary]" pgvector

# On your PostgreSQL server (run once per database)
psql -d persona0 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Configure the connection:**

```bash
export PERSONA0_PGVECTOR_DSN="postgresql://user:password@localhost:5432/persona0"
```

The store creates its table (`persona0_vectors`) and indexes automatically on first use. It supports:
- **Batch upserts** — load existing episodic records in bulk at startup
- **IVFFlat cosine similarity index** — efficient approximate nearest-neighbour search
- **GIN metadata index** — fast filtering by lifecycle state, importance, or category
- **Index lifecycle** — call `reindex()` after large batch loads, `vacuum()` on a schedule

> 📌 **NOTE**
> The in-memory `VectorStore` is still used by default in dev mode. The pgvector backend is activated by setting `PERSONA0_PGVECTOR_DSN` and instantiating `PgVectorStore` in your bootstrap code. See `src/store/vector_store.py` for the API.

---

### 7.3  Kubernetes Deployment

The `deploy/kubernetes/` directory contains Kubernetes manifests. To deploy to a cluster:

```bash
# 1. Install provider-specific packages in the image if using a real LLM
#    (add to requirements or Dockerfile: pip install openai  OR  pip install anthropic)

# 2. Tag and push your image to a registry
docker tag persona0:local ghcr.io/your-username/persona0:v0.1.0
docker push ghcr.io/your-username/persona0:v0.1.0

# 2. Update the image tag in deploy/kubernetes/deployment.yaml
#    (change 'ghcr.io/example/persona0:latest' to your image)

# 3. Edit deploy/kubernetes/configmap.yaml to set PERSONA0_CONFIG_PROFILE

# 4. Apply the manifests
kubectl apply -k deploy/kubernetes
kubectl rollout status deployment/persona0

# 5. Verify health
kubectl get pods -l app=persona0
```

For rollbacks and incident response, see the full runbook in `docs/operations.md`.

> 📌 **NOTE**
> Kubernetes is not required to test the thesis. Sections 1–5 are sufficient for experimental evaluation. Kubernetes becomes relevant when you want multi-day persistent runs in a stable, monitored environment.

---

## 8 — Troubleshooting

| Symptom | Fix |
|---|---|
| `Config OK` fails with "Unknown config profile" | You are not inside the `persona0/` directory. Run `cd persona0` first, or verify your current directory with `pwd`. |
| `pytest: command not found` | Your virtual environment is not activated. Run `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\Activate.ps1` (Windows). |
| `ImportError` on `src.engine.*` | The package is not installed. Run `pip install -e .[dev]` from inside the `persona0/` directory with the venv activated. |
| Scheduler exits immediately | This usually means a startup config validation error. Run the `validate_startup_config()` check from Section 4.1 and read the error. |
| All cycles show `ROLLBACK` | Check the `rollback_reason` field in the log. If it says `world_ingest`, the `bad_step` from Test 3 may still be registered. Start a fresh Python session. |
| "No API key for provider" error | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` as an environment variable matching the configured provider. |
| `ModuleNotFoundError: openai` | Run `pip install openai` (or `pip install anthropic` for Anthropic). These are optional and not included in the default install. |
| `RateLimitError` from provider | Lower `PERSONA0_LLM_ADAPTER__RATE_LIMIT_RPM` or wait for your quota to reset. The adapter retries with backoff automatically. |
| pgvector `psycopg` import error | Run `pip install "psycopg[binary]" pgvector`. Also confirm `CREATE EXTENSION vector;` was run on your database. |
| pgvector table missing columns | Call `PgVectorStore.ensure_schema()` on startup to auto-create the table and indexes. |
| `cycles.jsonl` is empty | The `2>&1 | tee` redirect may not work on your shell. Try running the scheduler first, then checking the log output directly. |

> 💡 **TIP**
> When in doubt, start a fresh terminal, re-activate the virtual environment, and re-run the failing command. Most beginners' issues are caused by running commands in the wrong directory or with the wrong Python environment.

---

## 9 — Quick Reference

### Key Commands

| Command | What It Does |
|---|---|
| `git clone ... && cd persona0` | Download the repository and enter its directory. |
| `python3 -m venv .venv && source .venv/bin/activate` | Create and activate the virtual environment. |
| `pip install -e .[dev]` | Install all dependencies. |
| `make test` or `pytest` | Run all automated tests. |
| `python -m src.runtime.scheduler --duration-seconds 300` | Run the scheduler for 5 minutes. |
| `python -m src.cli.trace_viewer cycles.jsonl` | Inspect cycle logs with the trace viewer. |
| `pytest tests/eval/ -v` | Run the evaluation harness (thesis metrics). |

### Key Files

| File | Purpose |
|---|---|
| `config/profiles/dev.yaml` | Development profile: LLM disabled, deterministic mode on. |
| `config/defaults.immutable.yaml` | Locked baseline values — do not edit. |
| `config/defaults.yaml` | Tunable defaults (tick intervals, retrieval weights). |
| `src/engine/adapters/llm.py` | LLM adapter — supports mock, OpenAI, and Anthropic providers. |
| `src/store/vector_store.py` | In-memory `VectorStore` (dev) and `PgVectorStore` (production) backends. |
| `src/cli/trace_viewer.py` | CLI tool for reading and visualising cycle logs. |
| `docs/operations.md` | Production operations runbook. |
| `_knowledge/initial_research/thesis_v0.10/` | The foundational research thesis (PDF and DOCX). |

### Environment Variables

| Variable | Purpose |
|---|---|
| `PERSONA0_CONFIG_PROFILE` | Set the deployment profile: `dev` (default), `staging`, or `prod`. |
| `PERSONA0_LLM_ADAPTER__PROVIDER` | LLM provider: `mock` (default), `openai`, or `anthropic`. |
| `OPENAI_API_KEY` | OpenAI API key. Required when provider is `openai`. |
| `ANTHROPIC_API_KEY` | Anthropic API key. Required when provider is `anthropic`. |
| `PERSONA0_LLM_ADAPTER__MODEL` | Model name (e.g. `gpt-4o`, `claude-sonnet-4-20250514`). |
| `PERSONA0_LLM_ADAPTER__ENABLED` | Override whether the LLM adapter is active (`true` / `false`). |
| `PERSONA0_LLM_ADAPTER__STREAMING` | Enable streaming responses (`true` / `false`). |
| `PERSONA0_LLM_ADAPTER__RATE_LIMIT_RPM` | Max requests per minute for rate limiting (default: `60`). |
| `PERSONA0_PGVECTOR_DSN` | PostgreSQL DSN for production vector store (e.g. `postgresql://user:pass@host/db`). |
| `PERSONA0_CONFIG_FILES` | Comma-separated paths to additional YAML override files. |

---

## Glossary

| Term | Plain-English Meaning |
|---|---|
| **Ego Engine** | The deterministic Python core of Persona0. Manages state, memory, and cognitive cycles without using an LLM. |
| `FAST_TICK` | A cognitive cycle that runs every 30 minutes. Updates drive states and affect. |
| `SLOW_TICK` | A cognitive cycle that runs every 3 hours. Generates desires and reviews goals. |
| `MACRO` | A daily cognitive cycle. Performs deep reflection and memory compaction. |
| `INTERACTION` | An on-demand cycle triggered by a user message. Retrieves memories and calls the LLM. |
| **Episodic Memory** | The agent's log of events that happened ("I argued with a colleague"). |
| **Self-model** | The agent's beliefs about itself ("I am curious", "I value honesty"). |
| **Drive State** | An internal need variable that grows over time (curiosity, social need, rest need) and is reduced by activities that satisfy it. |
| **Salience Buffer** | The working-memory list of memory IDs selected as most relevant for the current interaction context. |
| **Deterministic Mode** | A mode in which all LLM calls are replaced by scripted fallback responses. Safe for testing without an API key. |
| **Rollback** | When a cycle fails mid-execution, the orchestrator restores the state to exactly what it was before the cycle started. |
| **State Hash** | A SHA-256 fingerprint of the entire agent state at a given moment. Used to verify integrity. |
| **ISS** | Identity Stability Score — measures how consistent the agent's self-beliefs remain across cycles. Computed by `compute_iss()` in `src/eval/metrics.py`. |
| **MCS** | Memory Coherence Score — measures how consistent the retrieved memories are with the agent's current self-model. |
| **ECI** | Emotional Consistency Index — measures affect smoothness over time. Values below 0.3 indicate chaotic emotional dynamics. |
| **pgvector** | A PostgreSQL extension that adds vector similarity search. Used by `PgVectorStore` as the production memory index backend. |
| **Governance Policy** | A layer of checks that runs after every cycle to detect unsafe state mutations before they are committed. |
