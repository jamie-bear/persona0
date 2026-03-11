**Persona0** is a design for an ego-perspective cognitive agent architecture.

---

A lightweight "Ego Engine" architecture for humanlike AI chatbots. Featuring episodic memory, simulated affect/body states, and an off-screen life loop to create the illusion of continuity, personality, and time passage. The LLM acts only as a natural language renderer; all persistent "thinking" lives in external memory and deterministic state machines.

**Note:**
Read [./project_summary.md](/project_summary.md) for a basic overview of the development process for this project.

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
│   ├── defaults.yaml                   # Mutable defaults
│   ├── defaults.immutable.yaml         # Locked baseline values
│   ├── environments/                   # Per-environment overrides
│   │   ├── dev.yaml
│   │   ├── staging.yaml
│   │   └── prod.yaml
│   └── profiles/                       # Deployment profiles
│       ├── dev.yaml
│       ├── staging.yaml
│       └── prod.yaml
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
│   │   │   ├── embeddings.py
│   │   │   └── llm.py
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
│       ├── episodic_store.py           # Episodic memory store
│       └── vector_store.py             # Vector/embedding store
│
├── tests/                              # Test suite
│   ├── eval/                           # Eval-specific tests
│   ├── fixtures/                       # Shared test data (JSON)
│   ├── replay/                         # Determinism & multi-day replay tests
│   ├── runtime/                        # Scheduler integration tests
│   └── test_*.py                       # Unit tests per module
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

## Evaluation harness

This repo includes checkpoint-aligned evaluation helpers in `src/eval/` and pytest coverage in `tests/eval/`.

- Retrieval evaluation checks Precision@5 and top-5 self-relevant memory presence (CP-2).
- Self-belief safety evaluation checks confidence delta cap (`+0.15`) and contradiction rejection against core values/founding traits (CP-4).
- Threshold documentation is in `tests/eval/README.md`.

## Deployment and Operations

- Container build/runtime: `Dockerfile`
- Kubernetes manifests: `deploy/kubernetes/`
- Environment overlays: `config/environments/{dev,staging,prod}.yaml`
- Runbook: `docs/operations.md`
