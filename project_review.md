# Persona0 Implementation Review (Current Snapshot)

## Scope and Method

This review cross-checks the implementation in `src/` and tests in `tests/` against the claims in `project_summary.md`.

## What Is Healthy

1. **Baseline quality gates are strong and passing**
   - Entire test suite passes (`120 passed`).
   - Contracts, schema validation, orchestrator rollback/commit semantics, retrieval pipeline, and fast/slow dynamics all have test coverage.

2. **Summary status is mostly accurate**
   - CP-0 through CP-3 are represented in code and validated by tests.
   - CP-4/CP-5/CP-6 remain intentionally unfinished.

3. **Deterministic orchestration architecture remains intact**
   - Ordered contracts per cycle are centralized in `src/engine/contracts.py`.
   - Non-LLM behavior remains deterministic and testable.

## Gaps and Improvement Opportunities

### 1) Macro-cycle plumbing gap in default setup

`project_summary.md` flags CP-4 as not started, which is accurate. However, there is still a useful wiring improvement: `register_default_steps()` currently registers interaction/fast/slow steps but not macro stubs. This means a macro cycle can run (via orchestrator no-op fallback), but it is not explicitly wired in the same way as the other cycles.

**Impact:** low functional risk today, medium maintainability/readiness risk for CP-4 kickoff.

**Fix implemented in this changeset:** register all macro-cycle step stubs in `register_default_steps()` so macro wiring is explicit and discoverable.

### 2) Missing guard test for default macro registration

There was no regression test guaranteeing macro steps are present in the default setup registry.

**Fix implemented in this changeset:** added a targeted test to ensure all macro contract steps are registered after `register_default_steps()`.

## Recommended Next Execution Steps

### Step 1 (immediate, done here)
- Explicitly register macro cycle stubs in default setup.
- Add regression coverage to protect that registration.

### Step 2 (next PR)
- Start CP-4 with deterministic, non-LLM-safe building blocks in `src/engine/cycles/macro.py`:
  - `select_high_signal_episodes`
  - `cluster_episodes` (rule-based fallback before embeddings)
  - `score_evidence_sufficiency`
- Add minimal fixtures + tests proving stable output ordering and bounded confidence updates.

### Step 3
- Add observability for macro cycle internals to cycle logs (selected episode IDs, reflection IDs, evidence scores).

### Step 4
- Begin CP-5 governance hardening by introducing explicit policy outcome objects for interaction checks, so refusal/rollback reason categories are machine-auditable.

### Step 5
- Expand CP-6 evaluation suite with longitudinal continuity checks (multi-day replay + ISS/ECI drift alerts), not only per-cycle correctness.

## Prioritization Rationale

- **Why macro plumbing first:** tiny change, low risk, immediately improves CP-4 readiness.
- **Why deterministic CP-4 scaffolding next:** preserves architecture principles and keeps tests meaningful before adding any probabilistic components.
