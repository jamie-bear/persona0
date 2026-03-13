# Persona0 on n8n — Workflow Automation Guide

This directory contains everything you need to run the Persona0 Ego Engine as a set of **n8n workflows**. It translates the Python-based cognitive architecture into visual, importable n8n workflow templates that anyone can deploy without writing Python.

---

## What is Persona0?

Persona0 is a cognitive architecture for **persistent LLM personas**. Instead of expecting the AI to "remember" things, it externalizes memory, emotions, drives, goals, and self-beliefs into deterministic code and persistent storage. The LLM serves only as a natural language renderer.

The system runs four cognitive cycle types:

| Cycle | Cadence | Purpose |
|-------|---------|---------|
| **Interaction** | On-demand (webhook) | Handle user conversations with memory retrieval and governance |
| **Fast Tick** | Every 30 minutes | Update emotions, drives, generate thoughts, tick goals |
| **Slow Tick** | Every 3 hours | Activity transitions, desire generation, goal crystallization |
| **Macro** | Daily (3am) | Deep reflection, belief updates, memory compaction |

---

## Directory Structure

```
n8n/
├── README.md                         # This guide
├── workflows/
│   ├── interaction_cycle.json        # Webhook-triggered conversation handler
│   ├── fast_tick_cycle.json          # 30-minute scheduled perception cycle
│   ├── slow_tick_cycle.json          # 3-hour scheduled reflection cycle
│   └── macro_cycle.json              # Daily deep reflection & memory compaction
├── code-snippets/
│   ├── state_schema.js               # Agent state schema (for reference/reuse)
│   ├── emotion_module.js             # EMA-based affect update logic
│   ├── drive_module.js               # Drive growth, satisfaction, desire generation
│   ├── retrieval.js                  # Hybrid memory retrieval ranking
│   └── governance.js                 # Policy enforcement (hard limits, values, ownership)
└── config/
    ├── persona_config.json           # Persona definition template (edit this!)
    └── credentials_template.json     # Credential setup reference (never commit real keys)
```

---

## Prerequisites

- **n8n** installed and running (self-hosted or n8n Cloud)
  - Self-hosted: `npx n8n` or Docker: `docker run -it --rm -p 5678:5678 n8nio/n8n`
  - See [n8n installation docs](https://docs.n8n.io/hosting/)
- **LLM API key** (OpenAI or Anthropic) — optional for testing, required for production
- Basic familiarity with the n8n interface (nodes, connections, workflows)

---

## Quick Start (Step by Step)

### Step 1: Install and Start n8n

The fastest way to get n8n running locally:

```bash
# Option A: npx (requires Node.js 18+)
npx n8n

# Option B: Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

Open your browser to `http://localhost:5678` and create your admin account.

### Step 2: Import the Interaction Cycle Workflow

1. In the n8n UI, click **"Add workflow"** (top right)
2. Click the **three-dot menu** (⋯) → **"Import from File"**
3. Select `n8n/workflows/interaction_cycle.json`
4. The workflow canvas will show 11 connected nodes

You should see a flow like:

```
Webhook → Ingest Turn → Parse Intent → Retrieve Memory → Salience →
Appraisal → Build Context → Render Prompt → Mock LLM → Policy Check → Commit/Rollback
```

### Step 3: Test the Interaction Cycle

1. Click **"Test workflow"** (or press Ctrl+Enter)
2. The Webhook node will show a test URL. Copy it.
3. Send a test request:

```bash
curl -X POST http://localhost:5678/webhook-test/persona0-interact \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! How are you doing today?", "session_id": "test-1"}'
```

4. You should get a JSON response with the persona's reply, affect state, and governance results.

### Step 4: Import the Scheduled Cycles

Repeat the import process for each scheduled cycle:

1. **Fast Tick**: Import `workflows/fast_tick_cycle.json` — runs every 30 minutes
2. **Slow Tick**: Import `workflows/slow_tick_cycle.json` — runs every 3 hours
3. **Macro**: Import `workflows/macro_cycle.json` — runs daily at 3am

After importing, **activate** each workflow by toggling the switch in the top right of each workflow editor. The scheduled triggers will begin running automatically.

### Step 5: Customize Your Persona

Edit `config/persona_config.json` to define your persona's identity:

```json
{
  "persona": {
    "name": "Ada",
    "core_values": ["honesty", "curiosity", "empathy"],
    "hard_limits": ["never impersonate a real person"],
    "founding_traits": [
      { "statement": "I am curious and love exploring ideas.", "initial_confidence": 0.60 }
    ],
    "voice_style": { "tone": "warm", "formality": "conversational" }
  }
}
```

Then update the **Ingest Turn** node in the Interaction Cycle workflow to load this config as the bootstrap state.

---

## Architecture Mapping: Python → n8n

This table shows how each Persona0 Python component maps to n8n:

| Python Component | n8n Equivalent | Notes |
|-----------------|---------------|-------|
| `RuntimeScheduler` | Schedule Trigger nodes | Three separate workflows with 30min/3hr/daily triggers |
| `EgoOrchestrator` | Workflow execution order | n8n's sequential node execution replaces the orchestrator |
| `EmotionModule` | Code node (emotion_module.js) | EMA decay + circadian + appraisal logic |
| `DriveModule` | Code node (drive_module.js) | Growth rates, satisfaction, desire generation |
| `GoalSystem` | Code node (inline) | Frustration tracking, crystallization |
| `ThoughtGenerator` | Code node (inline) | Category selection + template rendering |
| `EpisodicStore` (SQLite) | n8n Static Data / external DB | Use `$getWorkflowStaticData('global')` for dev |
| `VectorStore` | HTTP Request → embedding API | Add Pinecone/Chroma/pgvector via HTTP nodes |
| `RetrievalRanking` | Code node (retrieval.js) | Weighted hybrid scoring |
| `Governance` | Code node (governance.js) | Hard limits, value consistency, ownership |
| `LLM Adapter` | HTTP Request or AI Agent node | Swap mock for real LLM calls |
| `Contracts` (step ordering) | Node connection order | Enforced by workflow structure |
| `CycleLogger` | n8n execution history | Built-in logging + final output node |
| Config YAML files | persona_config.json | Loaded via Code nodes at workflow start |

---

## Workflow Details

### Interaction Cycle (`interaction_cycle.json`)

Triggered by a POST webhook. Follows the exact 9-step contract from the Python implementation:

1. **Ingest Turn** — Receives user message, loads persisted state
2. **Parse Intent & Affect** — Basic intent detection (question/request/farewell) and sentiment estimation
3. **Retrieve Memory Candidates** — Queries episodic log with hybrid ranking (similarity + recency + importance + self-relevance)
4. **Salience Competition** — Selects top-5 memories for context (configurable via `salience_buffer_capacity`)
5. **Appraisal Update** — Updates affect state via EMA decay + appraisal deltas
6. **Build Context Package** — Assembles persona identity, beliefs, memories, affect into prompt context
7. **Render Response Prompt** — Constructs system + user prompts for the LLM
8. **LLM Call** — Mock by default; swap to real API (see "Connecting a Real LLM" below)
9. **Policy Check** — Validates response against hard limits and core values
10. **Commit or Rollback** — Persists state on pass, returns safe fallback on policy failure

### Fast Tick Cycle (`fast_tick_cycle.json`)

Runs every 30 minutes on a schedule:

1. **World Ingest** — Gathers events since last tick (user interactions, external events)
2. **Appraise** — Evaluates events against goals (positive → valence boost, threats → stress)
3. **Update Emotion** — EMA decay toward baseline + circadian energy wave + appraisal deltas
4. **Update Drives** — Natural growth + activity satisfaction + stress→rest coupling
5. **Generate Thought** — Selects thought category based on affect/drives, generates template text
6. **Salience Filter** — Sets current attention focus
7. **Update Goals** — Ticks progress (+0.01/tick), tracks frustration, suspends blocked goals
8. **Write Memory** — Persists thought as episodic event, saves state

### Slow Tick Cycle (`slow_tick_cycle.json`)

Runs every 3 hours. Includes all fast-tick steps plus:

9. **Activity Transition** — Changes current activity based on dominant drive
10. **Routine Event** — Generates synthetic events matching current activity
11. **Desire Generation** — Creates ephemeral desires when drives exceed impulse thresholds
12. **Desire Lifecycle** — Ages desires, persists high-urgency ones, crystallizes into goals

### Macro Cycle (`macro_cycle.json`)

Runs daily at 3am. Deep reflection and maintenance:

1. **Select High-Signal Episodes** — Finds the 10 most important episodes from the past day
2. **Cluster Episodes** — Groups episodes by theme/category
3. **Produce Candidate Reflections** — Generates belief statements from clusters (2+ episodes required)
4. **Score Evidence Sufficiency** — Filters reflections with insufficient evidence
5. **Update Self-Beliefs** — Updates confidence (capped at +0.15/cycle), creates new beliefs (max 3/cycle)
6. **Decay Unreinforced Beliefs** — Reduces confidence of beliefs not reinforced in 14 days
7. **Goal Review** — Archives goals stale for 30+ days
8. **Drive Review** — Drifts drives toward baseline
9. **Compact Memory** — Lifecycle transitions: active → cooling → archived → deleted

---

## Connecting a Real LLM

The workflows ship with a **Mock LLM Response** node enabled by default. To connect a real LLM:

### Option A: HTTP Request Node (Direct API)

1. In the Interaction Cycle workflow, **enable** the "LLM API Call" node (currently disabled)
2. **Disable** the "Mock LLM Response" node
3. Rewire: "Render Response Prompt" → "LLM API Call" → "Policy Check"
4. Set up credentials:
   - Go to **Settings → Credentials → Add Credential**
   - Select **Header Auth** and add your API key
   - Name it `OpenAI API Key` or `Anthropic API Key`
5. Update the HTTP Request node URL and body to match your provider

### Option B: n8n AI Agent Node (Recommended)

1. Delete the "LLM API Call" and "Mock LLM Response" nodes
2. Add an **AI Agent** node from the node panel
3. Add a **Chat Model** sub-node (OpenAI, Anthropic, etc.)
4. Configure credentials via n8n's built-in credential manager
5. Wire: "Render Response Prompt" → "AI Agent" → "Policy Check"

---

## Production LLM Configuration

The Python backend now supports three LLM providers natively:

| Provider | Config Value | Required Env Var | Notes |
|----------|-------------|-----------------|-------|
| Mock | `mock` (default) | None | Deterministic responses for dev/test |
| OpenAI | `openai` | `OPENAI_API_KEY` | Supports streaming, rate limiting |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Supports streaming, rate limiting |

All providers include:
- **Exponential backoff** on transient failures (1s, 2s, 4s...)
- **Rate limiting** via token-bucket (configurable RPM)
- **Streaming support** for lower time-to-first-token
- **Response validation** ensuring well-formed outputs

Set `llm_adapter.provider` and `llm_adapter.model` in `config/persona_config.json`, and provide the API key via environment variable.

---

## Production Vector Store

The Python backend supports two vector store backends:

| Backend | Config Value | Requirements | Notes |
|---------|-------------|-------------|-------|
| In-memory | `memory` (default) | None | Fast, no persistence, dev/test only |
| pgvector | `pgvector` | PostgreSQL + pgvector extension | Persistent, batch upsert, index lifecycle |

For pgvector, set `PERSONA0_PGVECTOR_DSN` and run `CREATE EXTENSION vector;` on your database. The store automatically creates tables and indexes on first use.

For n8n workflows, connect to external vector services via HTTP Request nodes (see "Upgrading Storage" below).

---

## Persistent Storage

By default, the workflows use **n8n's Static Data** (`$getWorkflowStaticData('global')`) to store agent state and episodic memory. This works for development but has limitations:

- Data is lost if the n8n instance restarts (unless using a persistent n8n database)
- No vector search capabilities (pure in-memory)

### Upgrading Storage

For production, replace the storage calls in the Code nodes:

| Storage Need | Recommended Solution | n8n Node |
|-------------|---------------------|----------|
| Agent state | PostgreSQL or Redis | Postgres / Redis node |
| Episodic log | PostgreSQL | Postgres node with `episodic_events` table |
| Vector search | Pinecone, Qdrant, or pgvector | HTTP Request node to vector API |
| Embeddings | OpenAI `text-embedding-3-small` | HTTP Request node |

Example: Replace `$getWorkflowStaticData('global').agentState` reads/writes with Postgres queries using the n8n Postgres node.

---

## Configuration Reference

All tunable parameters are in `config/persona_config.json`. Key settings:

### Tick Cadences
| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast_interval_seconds` | 1800 | Fast tick interval (30 min) |
| `slow_interval_seconds` | 10800 | Slow tick interval (3 hours) |
| `macro_interval_seconds` | 86400 | Macro cycle interval (24 hours) |

### Drive System
| Parameter | Default | Description |
|-----------|---------|-------------|
| `growth_rate.*` | 0.01–0.04 | Per-tick natural growth for each drive |
| `impulse_threshold.*` | 0.65–0.75 | Drive level that triggers desire generation |
| `crystallization_threshold_ticks` | 6 | Ticks before a desire can become a goal |

### Affect Dynamics
| Parameter | Default | Description |
|-----------|---------|-------------|
| `baseline.*` | varies | Resting affect values (valence, arousal, stress, energy) |
| `decay_rate.*` | 0.04–0.08 | EMA decay rate toward baseline per tick |
| `energy_modulation_amplitude` | 0.15 | Circadian energy wave amplitude |

### Reflection Policy
| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_confidence_delta_per_cycle` | 0.15 | Max belief confidence change per macro cycle |
| `max_new_statements_per_cycle` | 3 | Max new self-beliefs created per macro cycle |
| `confidence_decay_rate_per_cycle` | 0.02 | Decay rate for unreinforced beliefs |

---

## Code Snippets

The `code-snippets/` directory contains standalone JavaScript modules that can be pasted into n8n Code nodes:

- **`state_schema.js`** — Functions to create default state, seed beliefs, clear ephemeral data
- **`emotion_module.js`** — Full EMA-based affect update with circadian modulation (drop-in replacement for inline emotion code)
- **`drive_module.js`** — Drive growth, satisfaction, desire generation, and crystallization logic
- **`retrieval.js`** — Hybrid memory ranking with weighted scoring and explainability
- **`governance.js`** — Policy enforcement: hard limits, value consistency, field ownership validation

These snippets are self-contained — each one has its own n8n entry point that reads from `$input` and returns results. You can replace the inline Code node logic in the workflows with these more complete implementations.

---

## Troubleshooting

### Workflow won't trigger
- Ensure the workflow is **activated** (toggle in top right)
- For webhooks: use the **production URL** (not the test URL) when the workflow is active
- For schedules: check that your n8n instance timezone matches your expectations

### State resets between runs
- n8n Static Data persists across executions but **not across restarts** unless n8n uses a persistent database
- For durability, switch to PostgreSQL or Redis storage (see "Upgrading Storage" above)

### Mock LLM responses
- The interaction workflow uses a mock LLM by default — this is intentional for testing
- See "Connecting a Real LLM" above to switch to a real provider

### Memory retrieval returns empty
- The episodic log starts empty — interact with the persona a few times first
- Check that the Fast Tick and Slow Tick workflows are active and running

---

## Differences from the Python Implementation

| Feature | Python (original) | n8n (this adaptation) |
|---------|-------------------|----------------------|
| Transaction safety | Full snapshot + rollback | Simplified (state copy + conditional persist) |
| Field ownership enforcement | `FieldOwnershipRegistry` class | Governance Code node checks |
| Vector search | Dedicated `VectorStore` class | Placeholder (add via HTTP Request node) |
| LLM provider | Mock + real adapter hooks | Mock default + HTTP Request or AI Agent node |
| State persistence | SQLite + in-memory | n8n Static Data (upgrade to Postgres/Redis) |
| Telemetry | Prometheus-style counters | n8n built-in execution history |
| Step contracts | `contracts.py` enum validation | Enforced by workflow node connection order |
| PII redaction | `pii_redaction.py` module | Not included (add as Code node if needed) |

The n8n adaptation preserves the core cognitive architecture — the four cycle types, step ordering invariants, affect/drive/goal/belief systems, and governance checks — while simplifying deployment and making the system accessible through n8n's visual workflow interface.
