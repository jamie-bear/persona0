**Persona0** is a design for an ego-perspective cognitive agent architecture.

The Persona0 project aims to design, implement and assess the effectiveness of a lightweight 'ego engine' architecture for human-like AI chatbots. The Ego Engine features episodic memory, simulated affect/body states, and an off-screen life loop to create the illusion of continuity, personality, and time passage. The LLM acts only as a natural language renderer; all persistent "thinking" lives in external memory and deterministic state machines.

> **Note:**\
> Read [./project_summary.md](/project_summary.md) for a general status and overview of the development process.\
> Read [./persona0_deployment_guide_v0.10.md](/persona0_deployment_guide_v0.10.md) for guidance on how to use this repo.

---

## Repository Structure

```
persona0/
├── _knowledge/                         # Research & design documents
│   ├── execution/
│   │   └── implementation_v0.10/       # Current implementation spec
│   │       ├── acceptance_tests/
│   │       ├── checkpoints/
│   │       ├── definitions/
│   │       ├── overview/
│   │       ├── memory_lifecycle.md
│   │       └── persona_constitution.md
│   └── initial_research/
│       ├── _archive/                   # Superseded scaffold versions (v0.1–v0.16)
│       ├── scaffold_v0.17/             # Current scaffold spec
│       └── thesis_v0.10/              # Foundational thesis (PDF + DOCX)
│
├── config/                             # Runtime configuration
│   ├── defaults.yaml                   # Mutable defaults (operator-editable)
│   ├── defaults.immutable.yaml         # Locked baseline values (read-only)
│   ├── environments/                   # Legacy per-environment overrides
│   └── profiles/                       # Active deployment profiles
│       ├── dev.yaml                    # Dev: LLM disabled, deterministic mode
│       ├── staging.yaml                # Staging: LLM enabled, real provider
│       └── prod.yaml                   # Prod: strict governance, no mock
│
├── deploy/
│   └── kubernetes/                     # K8s manifests
│       ├── configmap.yaml
│       ├── deployment.yaml
│       └── kustomization.yaml
│
├── docs/
│   └── operations.md                   # Ops runbook
│
├── src/                                # Application source
│   ├── cli/
│   │   └── trace_viewer.py             # CLI tool for inspecting cycle traces
│   ├── engine/                         # Core ego engine
│   │   ├── adapters/                   # External service adapters
│   │   │   ├── embeddings.py           # Deterministic (dev) embedding generation
│   │   │   └── llm.py                  # Mock / OpenAI / Anthropic / Grok providers
│   │   ├── cycles/                     # Cognitive cycle implementations
│   │   │   ├── fast_tick.py            # High-frequency perception cycle
│   │   │   ├── slow_tick.py            # Low-frequency reflection cycle
│   │   │   ├── interaction.py          # User interaction cycle
│   │   │   ├── macro.py                # Long-horizon macro cycle
│   │   │   └── _store_helpers.py
│   │   ├── modules/                    # Cognitive state modules
│   │   │   ├── drive.py                # Drive/motivation system
│   │   │   ├── emotion.py              # Affect/emotion state
│   │   │   ├── goal.py                 # Goal tracking
│   │   │   ├── thought.py              # Thought generation
│   │   │   └── config_schema.py
│   │   ├── contracts.py                # Inter-module contracts
│   │   ├── cycle_log.py                # Cycle execution logging
│   │   ├── default_setup.py            # Engine bootstrapping
│   │   ├── governance.py               # Self-edit policy enforcement
│   │   ├── orchestrator.py             # Cycle orchestration
│   │   ├── pii_redaction.py            # PII scrubbing before storage
│   │   ├── retrieval.py                # Memory retrieval logic
│   │   └── telemetry.py                # Metrics & tracing
│   ├── eval/                           # Evaluation helpers
│   │   ├── metrics.py                  # Precision@5, belief-delta metrics
│   │   └── scenarios.py                # Eval scenario definitions
│   ├── runtime/                        # Process runtime
│   │   ├── healthcheck.py
│   │   ├── metrics_server.py
│   │   └── scheduler.py                # Cycle scheduler
│   ├── schema/                         # Data schemas & validation
│   │   ├── mutability.py               # Immutability rules
│   │   ├── records.py                  # Memory record types
│   │   ├── state.py                    # Agent state schema
│   │   └── validator.py
│   └── store/                          # Persistent storage
│       ├── episodic_store.py           # SQLite-backed episodic memory with lifecycle
│       └── vector_store.py             # In-memory (dev) + pgvector (production)
│
├── tests/                              # Test suite
│   ├── eval/                           # Eval-specific tests
│   ├── fixtures/                       # Shared test data (JSON)
│   ├── replay/                         # Determinism & multi-day replay tests
│   ├── runtime/                        # Scheduler integration tests
│   └── test_*.py                       # Unit tests per module
│
├── n8n/                                # n8n workflow integration
│   ├── README.md                       # n8n setup guide
│   ├── workflows/                      # Importable n8n workflow JSON files
│   ├── code-snippets/                  # JS equivalents of core Python modules
│   └── config/                         # Persona config and credential templates
│
├── .github/workflows/                  # CI pipelines
│   ├── lint-format.yml
│   ├── release.yml
│   ├── security-deps.yml
│   ├── tests.yml
│   └── type-check.yml
│
├── Dockerfile                          # Container image definition
├── Makefile                            # Developer task shortcuts
├── pyproject.toml                      # Project metadata & tooling config
├── requirements.txt                    # Python dependencies
└── project_summary.md                  # High-level project summary
```

## Evaluation Harness

Checkpoint-aligned evaluation helpers in `src/eval/` and pytest coverage in `tests/eval/`:

- **CP-2 retrieval:** Precision@5 ≥ 0.60; self-relevant memory in top-5 ≥ 80% of turns.
- **CP-4 self-belief safety:** confidence delta cap ≤ +0.15 per cycle; zero accepted constitution contradictions.
- **CP-6 longitudinal coherence:** Identity Stability Score (ISS), Memory Coherence Score (MCS), and Emotional Consistency Index (ECI) computed from cycle snapshots. Drift detection across replay runs via `detect_drift_alerts()`.

Threshold documentation: `tests/eval/README.md`. Run with `pytest tests/eval/ -v`.

## LLM Provider Configuration

The LLM adapter (`src/engine/adapters/llm.py`) supports four providers:

| Provider | Env var | Notes |
|----------|---------|-------|
| `mock` (default) | — | Deterministic fallback, no API key required |
| `openai` | `OPENAI_API_KEY` | `pip install openai` required |
| `anthropic` | `ANTHROPIC_API_KEY` | `pip install anthropic` required |
| `grok` | `XAI_API_KEY` | `pip install openai` required (OpenAI-compatible API) |

All real providers support streaming, exponential back-off retry, and token-bucket rate limiting. Set `PERSONA0_LLM_ADAPTER__PROVIDER` and the matching API key env var.

## Vector Store

`src/store/vector_store.py` provides two backends:

- **`VectorStore`** — in-memory cosine-similarity index (dev/test, no dependencies).
- **`PgVectorStore`** — PostgreSQL + pgvector (production). Set `PERSONA0_PGVECTOR_DSN`. Requires `pip install "psycopg[binary]" pgvector` and `CREATE EXTENSION vector;` on the database.

## Deployment and Operations

- Container build/runtime: `Dockerfile`
- Kubernetes manifests: `deploy/kubernetes/`
- Deployment profiles: `config/profiles/{dev,staging,prod}.yaml`
- Runbook: `docs/operations.md`
- n8n workflow integration (no-code deployment): `n8n/`
