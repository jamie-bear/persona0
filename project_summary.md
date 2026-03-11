# Persona0 — Project Summary

## What It Is

**Persona0** is a lightweight "Ego Engine" architecture for persistent LLM personas. The LLM is treated as a renderer, while identity continuity is maintained in externalized state, memory stores, and deterministic cycle logic.

---

## Architecture (Current v0.17)

The system is organized into four layers:

1. **Memory Fabric**
   - Episodic log with lifecycle management (active → cooling → archived → deleted)
   - Semantic/self-model updates during macro cycles
   - Hybrid retrieval with explainability (`why_selected` metadata)

2. **Ego Engine Core**
   - Deterministic cycle orchestration with transaction rollback
   - Fast/slow/macro/interaction pipelines with single-writer contracts
   - Governance checks for write ownership, hard limits, and value consistency

3. **Adapter Layer**
   - LLM adapter hooks for response generation and appraisal
   - Embeddings adapter + vector-store adapter for retrieval candidate sourcing
   - Deterministic fallbacks for offline/test-safe execution

4. **Runtime & Operations Layer**
   - Async runtime scheduler with retries, dead-letter tracking, and probes
   - Structured telemetry counters/timers and metrics exporter
   - Container + Kubernetes deployment assets and operational runbook

---

## Current Status

Persona0 now includes the previously planned productionization increments:

- **LLM adapter wiring exists** (`src/engine/adapters/llm.py`) and interaction/fast-tick integrate adapter calls.
- **Embedding + vector retrieval path exists** (`src/engine/adapters/embeddings.py`, `src/store/vector_store.py`, interaction retrieval step).
- **Async scheduler exists** with cadence/retry/dead-letter behavior (`src/runtime/scheduler.py`).
- **Config hardening exists** with typed settings, profiles, env overrides, and secret-handling guardrails (`src/engine/modules/_config.py`, `config/profiles/*`, `config/defaults.immutable.yaml`).
- **Deployment assets exist** (`Dockerfile`, `deploy/kubernetes/*`, `docs/operations.md`).
- **Observability exists** via cycle logs, telemetry, and metrics endpoint (`src/engine/cycle_log.py`, `src/engine/telemetry.py`, `src/runtime/metrics_server.py`).
- **Deployment correctness fixed** — four production-blocking issues resolved (see Deployment Fixes below).

In short: the codebase has moved from deterministic-core-only toward an operational stack with adapters and runtime infrastructure, and is now corrected for deployment.

---

## Checkpoint Matrix

| Checkpoint | Status | Notes |
|---|---|---|
| CP-0 | Done | Schema contracts and mutability ownership checks are in place. |
| CP-1 | Done | Transaction-safe orchestrator and deterministic replay scaffolding are implemented. |
| CP-2 | Done | Hybrid retrieval ranking + context assembly and eval harness are present. |
| CP-3 | Done (adapter-backed) | Affect/drive/thought/goal pathways implemented; appraisal now supports adapter-backed outputs. |
| CP-4 | Done | Macro reflection, belief update/decay, and lifecycle review implemented. |
| CP-5 | Done | Governance outcomes, PII redaction, forget semantics, and memory lifecycle compaction implemented. |
| CP-6 | Done | Metrics, latency checks, and multi-day replay tests implemented. |
| Productionization follow-up | In progress | External provider integrations and persistent production backends remain to be finalized. |

---

## Deployment Fixes (applied)

Four issues were found and corrected that would have broken a production deployment as-is:

1. **Config path mismatch (critical)** — `healthcheck.py` called `validate_runtime_config()` (legacy path) while the scheduler uses `validate_startup_config()` (new path). Additionally, `PERSONA0_CONFIG_PROFILE` was absent from the Dockerfile and K8s configmap, causing the scheduler to silently default to the `dev` profile (mock LLM, audit-mode governance) in production. Fixed: healthcheck now uses `validate_startup_config()`; `PERSONA0_CONFIG_PROFILE=prod` added to `Dockerfile` and `deploy/kubernetes/configmap.yaml`.

2. **Duplicate memory compaction (high)** — `MACRO_STEPS` included both `MEMORY_COMPACTION` and `COMPACT_EPISODIC_MEMORY`, which are functionally identical. Both called `cool_records()` + `archive_cooled()` with the same config, effectively doubling compaction throughput and violating the `max_records_cooled_per_cycle` cap. Fixed: `MEMORY_COMPACTION` removed from the contract and `default_setup.py` registration.

3. **Scheduler clock default crashes outside async (medium)** — `RuntimeScheduler.__init__` eagerly evaluated `asyncio.get_running_loop().time`, raising `RuntimeError` if constructed outside an async context. Fixed: default changed to `time.monotonic`.

4. **Telemetry block too narrow in `salience_competition` (low)** — The actual salience logic ran outside the `with time_block(...)` context manager, so only the config load was timed. Fixed: indentation corrected.

---

## Remaining Work (Practical)

The major architectural pieces are present; remaining work is mostly integration hardening:

1. **Provider-grade LLM integration**
   - Implement non-mock providers in the LLM adapter (currently mock-first).
   - Add provider-specific resilience (timeouts, retries, rate-limit behavior).

2. **Production vector backend**
   - Replace in-memory vector adapter with persistent backend (e.g., Chroma/pgvector).
   - Add migration/bootstrap tooling for existing episodic records.

3. **Release hardening**
   - Enforce CI quality gates on every branch path used in deployment.
   - Finalize SLO thresholds/alerts for rollback rate, latency, and policy-failure spikes.

4. **Operational validation**
   - Run staging soak tests (multi-day scheduler runs, recovery drills, dead-letter replay workflow).
   - Validate deployment playbooks and rollback drills end-to-end.
