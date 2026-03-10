# Persona0 Implementation Review (Current Snapshot)

## Scope and Method

Full code review of `src/`, `tests/`, and `config/defaults.yaml` cross-checked against `project_summary.md` claims and the design spec. All 126 tests pass. No TODO/FIXME/HACK comments in the codebase.

## What Is Healthy

1. **All 126 tests pass** across 13 test modules (1,669 lines of test code). Coverage spans schema validation, contracts, orchestrator rollback/commit, retrieval pipeline, fast/slow tick dynamics, macro-cycle scaffolding, and default setup registration.

2. **CP-0 through CP-3 are fully implemented and verified.** CP-4 macro-cycle scaffolding is in place with 8 deterministic step implementations and corresponding tests.

3. **Deterministic orchestration architecture is solid.** Ordered contracts per cycle are centralized in `src/engine/contracts.py` with 7 ordering invariants validated. Non-LLM behavior remains deterministic and testable.

4. **Transaction safety is intact.** Snapshot/commit/rollback semantics in the orchestrator, CONST field protection, and single-writer ownership enforcement all work correctly.

5. **Configuration is well-structured.** `config/defaults.yaml` covers all tunable parameters with clear comments and references to spec sections.

---

## Bugs and Issues Found

### Bug 1: `GoalStatus` class is broken (low severity)

**File:** `src/schema/state.py:98-102`

```python
class GoalStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
```

This inherits from `str` but defines class attributes, not enum members. `GoalStatus.ACTIVE` evaluates to `"active"` only by coincidence of Python class-level attribute semantics — it is **not** a proper enum. `GoalStatus("active") == GoalStatus.ACTIVE` is `True` but `isinstance(GoalStatus.ACTIVE, GoalStatus)` is `False`. The class is not used anywhere in the codebase (all status checks use raw string literals), making it dead code.

**Fix:** Either convert to `class GoalStatus(str, Enum)` and use it throughout, or remove it entirely. Given the project's convention of using raw strings for `goal.status`, removing it is cleanest.

### Bug 2: Macro cycle doesn't clear `persisted_desires` or `consecutive_thought_categories` (medium severity)

**File:** `src/schema/state.py:156-163` documents that both fields are "Cleared at nightly macro cycle." However, no macro-cycle step clears them.

- `persisted_desires`: "Cleared at nightly macro cycle. Never written to episodic log."
- `consecutive_thought_categories`: "Capped at length 3. Cleared at macro cycle."

The `clear_ephemeral()` method only clears `attention` and `active_desires`. If macro cycles run without clearing these fields, desires will persist indefinitely and the thought-category guardrail will carry stale history across days.

**Fix:** Add a `clear_nightly_ephemeral()` method or extend the macro cycle's final step to reset both fields and append the appropriate pending writes.

### Bug 3: `max_new_statements_per_cycle` config is not enforced (medium severity)

**File:** `src/engine/cycles/macro.py` — `update_self_beliefs()`
**Config:** `config/defaults.yaml` line `reflection.max_new_statements_per_cycle: 3`

The `update_self_beliefs` function creates new `SelfBelief` objects without counting how many new beliefs are being created in the current cycle. With enough clusters producing unique statements, this could exceed the configured limit of 3 new beliefs per macro cycle.

**Fix:** Track a `new_statements_created` counter in `update_self_beliefs` and stop creating new beliefs once it reaches the configured cap.

### Bug 4: Confidence decay for unreinforced beliefs is not implemented (low severity, CP-4 gap)

**Config:** `reflection.confidence_decay_rate_per_cycle: 0.02` and `reflection.confidence_decay_threshold_days: 14`

No code implements the specified confidence decay for beliefs that haven't been reinforced within the configured window. All beliefs created by the macro cycle will retain their confidence indefinitely.

**Fix:** Add a decay step to the macro cycle (between `update_self_beliefs` and `archive_reflection` or as a new step) that reduces confidence of beliefs with no recent supporting episode.

---

## Code Quality Issues

### Issue 1: Duplicate `_try_store_append` logic

`fast_tick.py:150-184` (`_try_store_append`) and `slow_tick.py:144-178` (`_try_store_append_raw`) are nearly identical functions that construct an `EpisodicEvent` and append it to the store. This violates DRY and means any fix to the append logic must be applied in two places.

**Fix:** Extract a shared helper into `src/store/` or `src/engine/cycles/__init__.py`.

### Issue 2: Stale test count in previous review

The previous `project_review.md` stated "120 passed" but the current test suite has 126 tests. The summary correctly states 126.

### Issue 3: `LOG_CYCLE` in macro contract uses fast_tick's no-op

The macro cycle contract includes `LOG_CYCLE` as its final step, which is registered as `fast_tick.log_cycle` — a documented no-op. This works correctly (the orchestrator handles logging externally), but it's semantically confusing that the macro cycle's log step points to a fast_tick function. A trivial `macro.log_cycle` alias would improve readability.

---

## Recommended Next Execution Steps

### Step 1 — Fix identified bugs (immediate, this PR)

1. **Remove or fix `GoalStatus` class** in `src/schema/state.py`
2. **Add nightly clearing of `persisted_desires` and `consecutive_thought_categories`** to the macro cycle pipeline
3. **Enforce `max_new_statements_per_cycle`** in `update_self_beliefs()`
4. **Add tests** for each fix

### Step 2 — CP-4 hardening (next PR)

1. **Implement confidence decay** for unreinforced beliefs in the macro cycle
2. **Add recency window filter** to `select_high_signal_episodes` — currently loads up to 100 episodes with no time-based filter, meaning very old episodes can dominate. Add a configurable window (e.g., 48-72h of simulated time) to focus on recent experience.
3. **Improve `goal_review`** to perform actual goal lifecycle operations: check for stale goals (> `goal_staleness_days`), archive dormant ones, and log review decisions for auditability
4. **Extract `_try_store_append` duplication** into a shared helper
5. **Expand macro-cycle replay determinism tests** to validate that identical episode inputs produce identical belief/reflection outputs across runs

### Step 3 — CP-4 observability

1. Add macro-cycle internals to cycle logs: selected episode IDs, cluster composition, reflection IDs, evidence scores, accepted/rejected decisions
2. Add a `macro.log_cycle` step that captures macro-specific audit payload rather than reusing the fast_tick no-op

### Step 4 — CP-5 governance hardening

1. Introduce explicit policy outcome objects for interaction checks (machine-auditable refusal/rollback reason categories)
2. Implement forget/delete lifecycle operations in the episodic store
3. Add PII redaction hooks before long-term commit
4. Build out `src/cli/trace_viewer.py` for audit log ergonomics

### Step 5 — CP-6 evaluation sprint

1. Extend replay/continuity benchmarks with multi-day simulation (macro cycle included)
2. Implement MCS/ISS/ECI metric computation from cycle logs
3. Add operational readiness checks: P95 context-build latency, write durability, determinism assertions over 144+ tick simulations

## Prioritization Rationale

- **Why bug fixes first:** Bugs 2 and 3 violate documented contracts (the summary promises these behaviors exist). Fixing them now prevents false confidence in CP-4 correctness.
- **Why CP-4 hardening next:** The scaffold is in place but the reflection pipeline needs quality controls (recency, decay, caps) before it can produce reliable self-model updates.
- **Why observability before governance:** Macro-cycle visibility is needed to validate that hardening changes work correctly; governance is a separate concern that doesn't block CP-4 completion.
