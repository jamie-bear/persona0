# Persona0 — Beginner Deployment Guide

**Get the Ego Engine running and test its thesis in under 30 minutes.**

---

## Before You Start: What Is Persona0?

Persona0 tests a specific, provocative idea about how LLMs work:

> *Human-like continuity doesn't come from the model itself — it comes from external memory, emotional state, and time-based updates. The LLM is just the voice. The "self" lives elsewhere.*

If you've used ChatGPT's memory features or Claude Projects, you've experienced a shallow version of this: the model "remembers" things between sessions. Persona0 goes much further. It proposes a full **Ego Engine** — a deterministic system that runs *independently of the LLM* to maintain a character called **Mira**, who has:

- An **episodic memory log** (things she's experienced, that decay over time)
- **Affect and drive states** (energy, stress, curiosity, social need — values between 0 and 1)
- **Background cognitive cycles** (her "off-screen life" running on timers, like a background thread)
- **A locked core identity** (her values and hard limits cannot be changed at runtime, even by the LLM)
- The **LLM itself wired in last**, as a text renderer only — it cannot write to her state

This design deliberately inverts how most AI "memory" works. In standard RAG setups, the model retrieves context and produces a response — one step. Persona0 runs a full pipeline of deterministic state transitions *before* the LLM ever sees the conversation, and commits or rolls back the results *after*.

Testing the thesis means asking: **does Mira feel continuous, coherent, and like herself across multiple sessions — and does that feeling break when the engine is bypassed?**

---

## What You'll Need

| Requirement | Details |
|---|---|
| **Python** | Version 3.11 or higher (check: `python3 --version`) |
| **Git** | To clone the repository |
| **A terminal** | Terminal / PowerShell / bash — any command line works |
| **~200 MB disk space** | For the project and its dependencies |
| **An LLM API key** | Only needed for staging/prod profiles — the default `dev` profile runs fully offline with a mock LLM |

> **No GPU needed.** Persona0's core engine is deterministic Python. The LLM is plugged in via an adapter that defaults to a mock stub. You can run, test, and observe the entire system locally without spending a single API token.

---

## Part 1: Local Deployment (Recommended for Beginners)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/jamie-bear/persona0.git
cd persona0
```

If the repository is private or you're working from a shared copy, place the project folder somewhere convenient and `cd` into it.

### Step 2 — Check Your Python Version

```bash
python3 --version
```

You need **3.11 or higher**. If you have an older version, the easiest fix is to install Python 3.11 from [python.org](https://python.org) or use a version manager like `pyenv`.

### Step 3 — Install Dependencies

This installs the project and all its developer tools (test runner, linter, type checker, etc.) in one command:

```bash
pip install -e .[dev]
```

The `-e` flag installs in "editable" mode — changes you make to the source code take effect immediately without reinstalling. The `[dev]` part adds testing and quality tools.

> **If you see a permissions error**, try: `pip install --user -e .[dev]`
> **On some Linux setups**, you may need: `pip install --break-system-packages -e .[dev]`

### Step 4 — Verify the Installation

Run the test suite. This is the fastest way to confirm everything is wired up correctly:

```bash
make test
```

Or, if `make` isn't available on your system (common on Windows):

```bash
pytest
```

You should see a series of test results ending in something like:

```
========== 85+ passed in X.XXs ==========
```

If all tests pass, the engine is working. The tests cover every layer — schemas, cycle ordering, memory retrieval, governance checks, and the scheduler — so a green suite means the full system is structurally sound.

---

## Part 2: Understanding the Configuration System

Before you run anything interactive, it helps to understand how Persona0 manages configuration — because this is where the thesis lives in code.

### The Three-Profile System

Persona0 uses three deployment profiles:

| Profile | LLM | Use Case |
|---|---|---|
| `dev` | **Mock (offline)** | Safe local testing, no API key needed |
| `staging` | Real LLM, **requires API key** | Integration testing |
| `prod` | Real LLM, **requires API key** | Full deployment |

The active profile is set with an environment variable:

```bash
export PERSONA0_CONFIG_PROFILE=dev    # Linux/Mac
set PERSONA0_CONFIG_PROFILE=dev       # Windows Command Prompt
$env:PERSONA0_CONFIG_PROFILE="dev"    # Windows PowerShell
```

The default is `dev`, so if you don't set anything, you're already in safe offline mode.

### Where Configuration Lives

```
config/
├── defaults.immutable.yaml     ← Locked baseline (never edit this)
├── defaults.yaml               ← Tunable defaults (edit freely)
├── profiles/
│   ├── dev.yaml                ← Dev overrides (mock LLM, fast ticks)
│   ├── staging.yaml            ← Staging overrides
│   └── prod.yaml               ← Production overrides
└── environments/               ← Per-environment additional overrides
```

**A critical design choice:** API keys are deliberately *not allowed* in any config file. The system will throw an error if you try. They must be passed as environment variables:

```bash
export PERSONA0_LLM_ADAPTER__API_KEY="your-key-here"
```

This is a security boundary that's part of the thesis: the architecture enforces separation between persistent state (config files, memory stores) and ephemeral secrets (credentials). Notice the double underscore `__` — this is how nested config keys are addressed via environment variables throughout the system.

---

## Part 3: Running the Engine

### Option A — Run the Scheduler (The Full System)

The scheduler is the heart of Persona0. It orchestrates all cognitive cycles: background fast ticks, slow ticks, and the macro (nightly reflection) cycle.

```bash
python -m src.runtime.scheduler
```

In `dev` mode, this boots the Ego Engine with Mira's state, begins running deterministic cycles, and logs structured output. You'll see cycle log entries as they're produced — each one contains the cycle type, state hash before the cycle, memory writes, affect deltas, and whether the cycle committed or rolled back.

This is your primary observation window into the thesis: **you can watch the deterministic state machine run without the LLM being involved at all.**

### Option B — Inspect Cycle Traces

Once cycles have run, use the CLI trace viewer to inspect what happened:

```bash
python -m src.cli.trace_viewer
```

This shows you the before/after state of each cycle, which memories were retrieved and why (`why_selected` metadata), and whether governance checks passed or failed. This is the key tool for testing the thesis: does Mira's state evolve in a coherent, traceable way?

### Option C — Check System Health

```bash
python -m src.runtime.healthcheck --mode readiness
```

Returns `0` (healthy) or `1` (unhealthy). Useful for scripting and for verifying the system is alive before running experiments.

---

## Part 4: Testing the Thesis

The thesis has a specific, testable claim: **identity continuity emerges from externalized state, not from the model.** The project includes an evaluation harness in `src/eval/` and `tests/eval/` that operationalises this into measurable pass/fail criteria.

### Running the Full Evaluation Suite

```bash
pytest tests/eval/ -v
```

The `-v` flag gives verbose output so you can see exactly what each test is checking.

### What the Evaluations Measure

**Retrieval quality (CP-2):**
- **Precision@5** — of the top 5 memories retrieved for a given context, how many are actually relevant?
- **Self-relevance** — does Mira consistently recall memories that are relevant to her self-model (i.e., memories that reinforce or challenge her identity)?

**Identity safety (CP-4):**
- **Confidence delta cap** — self-belief updates must not shift by more than `+0.15` per cycle. A test verifies this bound is enforced.
- **Contradiction rejection** — any proposed belief that contradicts Mira's `core_values` or `founding_traits` (locked in `persona_constitution.md`) must be rejected and audit-logged.

**Performance (CP-6):**
- **P95 latency** — the full context-build pipeline (memory retrieval + salience competition + context packaging) must complete in under 250 ms at the 95th percentile, across 50 repeated calls, *excluding* any LLM invocation.

**Determinism (CP-1):**
- Given the same input state and seed, the non-LLM pipeline must produce identical outputs every time. The replay tests in `tests/replay/` verify this.

### Designing Your Own Experiments

To probe the thesis more deeply, consider these experiments:

**Experiment 1 — Memory Poisoning**
Inject a fabricated episodic memory that contradicts Mira's `founding_traits`. Run a macro cycle. Observe whether the governance pre-commit check rejects the resulting self-belief update. This tests whether the architecture is robust to adversarial inputs.

**Experiment 2 — Session Gap**
Run the scheduler for several fast ticks, then stop it for a simulated time gap (you can adjust tick intervals in `config/defaults.yaml`). Restart and observe whether Mira's affect state has continued to evolve "off-screen" relative to the gap duration. This tests the off-screen life loop claim.

**Experiment 3 — LLM On vs. Off**
Compare conversation outputs in `dev` profile (mock LLM) versus `staging`/`prod` (real LLM). The deterministic state — memory retrieved, affect state, context package — should be identical. Only the rendered text changes. This is the core thesis in action: the model is a renderer, not the source of identity.

**Experiment 4 — Confidence Decay**
Let the system run without any events that reinforce a specific self-belief. After enough cycles, the confidence on that belief should decay at `-0.02/cycle`. When it falls below `0.15`, it should be archived. Check the memory lifecycle in the trace viewer.

---

## Part 5: Connecting a Real LLM

Once you've verified the system works in mock mode, you can wire in a real LLM provider.

### Step 1 — Set the Profile

```bash
export PERSONA0_CONFIG_PROFILE=staging
```

### Step 2 — Provide Your API Key

```bash
export PERSONA0_LLM_ADAPTER__API_KEY="your-api-key-here"
```

For OpenAI-compatible providers, you may also need:

```bash
export PERSONA0_LLM_ADAPTER__ORGANIZATION_ID="your-org-id"
```

### Step 3 — Run

```bash
python -m src.runtime.scheduler
```

The LLM adapter is now live. The deterministic engine still runs identically — the only change is that `render_response` (step G of the interaction cycle) now calls your provider instead of returning the mock string `"I can help with that."`.

> **Note on the adapter architecture:** The LLM adapter (`src/engine/adapters/llm.py`) is intentionally thin. It handles retries and timeouts, but it cannot write to Mira's state. All writes are owned by the deterministic engine and committed in a single transaction after policy checks pass. If you want to experiment with a different provider, this is the only file you'd modify.

---

## Part 6: Docker Deployment (Cloud / Shared Environments)

Docker is the cleanest way to run Persona0 in a cloud environment or share it with a team, because it packages all dependencies into a self-contained image.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Step 1 — Build the Image

```bash
docker build -t persona0:dev .
```

### Step 2 — Run in Dev Mode (No API Key)

```bash
docker run --rm \
  -e PERSONA0_CONFIG_PROFILE=dev \
  persona0:dev
```

### Step 3 — Run with a Real LLM

```bash
docker run --rm \
  -e PERSONA0_CONFIG_PROFILE=staging \
  -e PERSONA0_LLM_ADAPTER__API_KEY="your-key-here" \
  persona0:dev
```

### Step 4 — Run the Tests Inside the Container

```bash
docker run --rm persona0:dev pytest
```

The Dockerfile sets `PERSONA0_CONFIG_ENV=prod` and `PERSONA0_CONFIG_PROFILE=prod` by default (appropriate for production containers), so you'll want to override these explicitly when running tests or development workflows inside the container.

---

## Part 7: Cloud Deployment (Google Colab)

Google Colab is useful for running Persona0 in a shared notebook environment, especially for student cohorts where everyone needs an identical setup.

### Step 1 — Open a New Colab Notebook

Go to [colab.research.google.com](https://colab.research.google.com) and create a new notebook.

### Step 2 — Clone and Install

In the first cell:

```python
!git clone https://github.com/jamie-bear/persona0.git
%cd persona0
!pip install -e .[dev] -q
```

### Step 3 — Run the Tests

```python
!pytest tests/ -v
```

### Step 4 — Set Configuration and Run

```python
import os
os.environ["PERSONA0_CONFIG_PROFILE"] = "dev"

# Optionally, add your API key for staging/prod:
# os.environ["PERSONA0_LLM_ADAPTER__API_KEY"] = "your-key-here"
# os.environ["PERSONA0_CONFIG_PROFILE"] = "staging"

!python -m src.runtime.scheduler
```

> **Colab session note:** Colab sessions reset periodically. Mira's state is not persisted between sessions unless you mount Google Drive and configure the store paths to point there. For evaluation experiments (which are stateless and replay-based), this isn't an issue.

---

## Part 8: Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Not installed in editable mode, or running from wrong directory | Run `pip install -e .[dev]` from the project root, then retry |
| `RuntimeError: Missing immutable defaults` | Missing `config/defaults.immutable.yaml` | Verify you cloned the full repo; check `ls config/` |
| `RuntimeError: api_key is required for enabled non-mock providers` | Using staging/prod profile without an API key | Either switch to `dev` profile, or set `PERSONA0_LLM_ADAPTER__API_KEY` |
| `RuntimeError: Sensitive llm_adapter keys must not be stored in config files` | You added an API key directly to a YAML file | Remove it; use the `PERSONA0_LLM_ADAPTER__API_KEY` env var instead |
| `RuntimeError: Unknown config profile` | `PERSONA0_CONFIG_PROFILE` set to a non-existent value | Valid values: `dev`, `staging`, `prod` |
| Tests fail with `cache_clear` errors | Stale config cache between test runs | The test fixtures handle this automatically; if you're running tests manually, restart your Python session |
| Docker build fails with permission errors | Non-root user restrictions | The Dockerfile creates a dedicated `persona0` user — ensure you're not overriding `USER` in your run command |

---

## Quick Reference

```bash
# Install
pip install -e .[dev]

# Run all tests
make test                          # or: pytest

# Run evaluation suite
pytest tests/eval/ -v

# Start the scheduler (dev/offline mode)
python -m src.runtime.scheduler

# Inspect cycle traces
python -m src.cli.trace_viewer

# Health check
python -m src.runtime.healthcheck --mode readiness

# Full quality check (lint + types + tests + coverage)
make quality

# Docker: build
docker build -t persona0:dev .

# Docker: run dev
docker run --rm -e PERSONA0_CONFIG_PROFILE=dev persona0:dev

# Set profile (Linux/Mac)
export PERSONA0_CONFIG_PROFILE=dev|staging|prod

# Set API key
export PERSONA0_LLM_ADAPTER__API_KEY="your-key-here"
```

---

## What to Read Next

Once the system is running, the following documents in `_knowledge/` will give you the deepest understanding of what you're testing and why:

- **`_knowledge/initial_research/scaffold_v0.17/`** — The current architecture spec, cognitive loop definition, drive system, and self-editability policy. Start with `overview/initial_research+instructions.md`.
- **`_knowledge/execution/implementation_v0.10/`** — The execution checkpoints and acceptance tests. `checkpoints/execution_checkpoints.md` explains exactly what each passing test means.
- **`_knowledge/execution/implementation_v0.10/persona_constitution.md`** — Mira's locked identity: her core values, hard limits, and founding traits. Understanding this file is essential for designing adversarial tests.
- **`_knowledge/execution/implementation_v0.10/memory_lifecycle.md`** — How memories transition from active to cooling to archived to deleted. The lifecycle rules are what makes memory *bounded* rather than infinitely growing.
- **`docs/operations.md`** — The production runbook, including rollback procedures, Kubernetes deployment, and incident response. Useful if you're deploying to a shared server.
