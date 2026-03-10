# Persona0 — Project Summary

## What It Is

**Persona0** is a design specification for a lightweight "Ego Engine" — an external cognitive runtime that gives LLM-based chatbots persistent identity, autobiographical memory, and believable continuity without modifying model weights.

**Core thesis:** Human-like continuity emerges from deterministic, externalized state — not from the LLM itself. The LLM is a stateless language renderer; all persistent "thinking" lives in inspectable memory stores and deterministic state machines.

---

## Architecture (Final v0.16)

The system is divided into four layers:

### 1. Memory Fabric
Three stores with provenance tracking:
- **Episodic log** — append-only event history (full fidelity, not summaries)
- **Semantic store** — stable extracted facts
- **Self-model** — identity beliefs with confidence scores and decay

Retrieval uses a weighted hybrid score:
```
score = similarity×w₁ + recency×w₂ + importance×w₃ + emotional_resonance×w₄
```
Every retrieved memory carries `why_selected` metadata for explainability.

### 2. Ego Engine Core
Deterministic modules, each with single-writer ownership over its state variables:

| Module | Role |
|---|---|
| **Input Processor** | Converts user messages into internal events |
| **Salience Gate** | Global Workspace Theory filter — selects what enters working context (ranked by emotional intensity, goal relevance, recency, novelty) |
| **Appraisal Module** | Evaluates events against goals and identity using the EMA appraisal model; outputs structured scores (relevance, goal-congruence, threat, novelty, social/identity significance) |
| **Emotional Regulation** | Bounded, cross-coupled dynamics across 7 variables: valence, arousal, stress, energy, social_need, mastery_need, rest_need — with circadian modulation and decay |
| **Goal System** | Hierarchical goals with conflict tracking, frustration accumulation, and lifecycle transitions (active → suspended → completed/abandoned) |
| **Thought Generator** | Produces typed thoughts (reflection, planning, rumination, curiosity, self-evaluation, social) driven by current affective and goal state |

### 3. LLM Renderer
Parses user intent and affect cues from a prepared context package. Generates responses constrained by a persona constitution. **Cannot mutate persistent state directly.**

### 4. Governance Layer
- Transparency disclosure enforcement (AI identity always disclosed)
- Policy validation before response emission
- Full audit logging on every write
- PII redaction before long-term commit
- User-requested forget/delete semantics
- Transaction rollback if any check fails

---

## Cognitive Loop

Four tick types drive off-screen life simulation:

| Tick | Cadence | Work |
|---|---|---|
| **Fast** | ~30 min | Thought generation, emotion drift, state maintenance |
| **Slow** | 2–4 hr | Activity changes, routine events, goal review |
| **Daily** | Nightly | Memory consolidation, reflection, self-model update |
| **Conversation** | On-demand | User interaction integration, full cycle with rollback |

Conversations are **transaction-safe** — they either fully commit to all three memory stores or fully roll back.

---

## Evolution Across Versions

### v0.1 — Foundation
Established the core thesis: LLM as renderer, external memory as the cognitive core. Defined the ego-data specification (episodic memories, emotional reflections, goals, identity), an initial module list, and a 5-phase roadmap.

**Key gaps identified:** No cognitive loop specification, no Salience Gate or Appraisal module, no Input Processor, simplistic unbounded emotion rules, unspecified memory retrieval algorithm, contradictory ordering (data-before-architecture).

### v0.15 — Major Refinement
Closed all v0.1 gaps:
- Added Salience Gate (Global Workspace Theory)
- Added Appraisal module (EMA model)
- Added Input Processor
- Formalized the four-tick cognitive loop in `cognitive_loop.md`
- Replaced linear emotion rules with bounded, cross-variable dynamics
- Defined the memory retrieval scoring formula
- Added a conversational policy layer and ego-data consistency constraints
- Reordered development plan to architecture-first

### v0.16 — Governance & Metrics
- Strict layered model with single-writer contracts per module
- Transaction-safe interaction cycles with explicit rollback semantics
- Quantitative evaluation metrics:
  - **MCS** — Memory Coherence Score
  - **ISS** — Identity Stability Score
  - **ECI** — Emotional Consistency Index
  - **Recall Precision@k**
- Non-functional targets: P95 context-build latency < 250 ms, no loss of acknowledged writes, deterministic non-LLM outputs
- Governance envelope: disclosure enforcement, audit trail, PII lifecycle, user-delete semantics
- Concrete 6-week delivery roadmap with weekly exit criteria

---

## Key Design Principles

- **LLM is stateless** — cognitive state is external, inspectable, and editable
- **Determinism** — same input + state → same non-LLM outputs (enables testing and debugging)
- **Transaction safety** — conversations either fully commit or fully roll back
- **Observability** — every cycle produces structured logs with full state snapshots and reasoning trail

**Anti-patterns explicitly called out:**
- LLM mutating persistent state directly
- Storing only summaries (full event history needed for reconstructability)
- Reflecting on every turn (causes identity drift)
- Unconstrained synthetic memory generation

---

## Current Status

Persona0 is in an **active implementation phase** — CP-0 through CP-5 are complete, and CP-6 evaluation is well underway. All four cognitive cycle types (interaction, fast, slow, macro) have behavior-complete step implementations with full test coverage.

- **CP-0 (done):** Schema and contracts — `AgentState`, mutability registry, single-writer ownership enforcement, deterministic cycle ordering contracts.
- **CP-1 (done):** Transaction-safe orchestrator, SHA-256 state hashing, cycle logging, append-only SQLite episodic store, replay determinism harness, interaction retrieval/salience/context pipeline.
- **CP-2 (done):** Hybrid memory retrieval scorer with `why_selected` explainability, interaction cycle steps C/D/F (retrieve → salience → context), `FoundingTraitSeed` constitution bootstrap, evaluation harness (`evaluate_retrieval_precision`, `evaluate_self_belief_safety`).
- **CP-3 (done):** Affect + drive dynamics + desire generation — all fast-tick and slow-tick steps are behavior-complete. All CP-3 exit gates verified (see below).
- **CP-4 (done):** Complete nightly macro-cycle — episode selection with recency window filter (72h default), deterministic clustering, evidence scoring, `update_self_beliefs` with `max_new_statements_per_cycle` cap (3), `decay_unreinforced_beliefs` step applying −0.02/cycle after 14 days of no reinforcement (CONST_SEED beliefs exempt), goal lifecycle management (staleness abandonment after 30 days, frustration-based suspension at ≥0.75), nightly clearing of `persisted_desires` and `consecutive_thought_categories`, and macro determinism replay verification.
- **CP-5 (done):** Governance hardening — `PolicyOutcome`/`PolicyCheckResult` for machine-auditable checks (categories: `CONST_VIOLATION`, `OWNERSHIP_VIOLATION`, `HARD_LIMIT_BREACH`, `VALUE_CONTRADICTION`, `WRITE_CAP_EXCEEDED`, `PII_DETECTED`), `policy_and_consistency_check` wired in interaction cycle, episodic store lifecycle management (`transition_lifecycle`, `cool_records`, `archive_cooled`, `forget`, `forget_bulk`), PII redaction hooks (email, phone, SSN, CC, IPv4) applied before every long-term store commit, `memory_compaction` macro step wired to run `cool_records`/`archive_cooled` each nightly cycle, `trace_viewer.py` extended with policy outcome and macro-cycle detail rendering.
- **CP-6 (in progress):** Evaluation harness — `CycleSnapshot` dataclass, `compute_mcs`/`compute_iss`/`compute_eci`/`rollback_rate` metric functions implemented, multi-day replay test suite (24-cycle 3-day simulation with metric threshold validation), determinism bug fixed (desire/goal IDs made replay-safe by replacing `uuid4()` with tick-derived deterministic IDs).

**168 tests passing** across `test_schema`, `test_contracts`, `test_orchestrator`, `tests/replay` (including `test_multi_day`), `tests/eval`, `test_retrieval_and_interaction`, `test_fast_tick`, `test_slow_tick`, `test_default_setup`, `test_macro_tick`, and `test_governance`.

### Modules Implemented

| Module | File | Role |
|---|---|---|
| `EmotionModule` | `src/engine/modules/emotion.py` | EMA decay toward baseline, circadian energy cosine wave, appraisal-driven deltas, clamping |
| `DriveModule` | `src/engine/modules/drive.py` | Homeostatic growth, activity-event satisfaction, desire generation, crystallization, desire aging/expiry |
| `ThoughtGenerator` | `src/engine/modules/thought.py` | Deterministic category selection (desire → affect → drive priority), 3-consecutive guardrail, template-based text |
| `GoalSystem` | `src/engine/modules/goal.py` | Per-tick progress/frustration ticking, suspension threshold, crystallization proposal acceptance |
| `EpisodicStore` | `src/store/episodic_store.py` | SQLite append-only store with full lifecycle: active→cooling→archived→deleted, `forget`/`forget_bulk` |
| `governance` | `src/engine/governance.py` | `PolicyOutcome`/`PolicyCheckResult` — machine-auditable write, hard-limit, and value-consistency checks |
| `pii_redaction` | `src/engine/pii_redaction.py` | Pattern-based PII redaction (email, phone, SSN, CC, IPv4) applied before every long-term store commit |
| `_store_helpers` | `src/engine/cycles/_store_helpers.py` | Shared EpisodicEvent construction + PII redaction used by fast_tick and slow_tick |
| `macro` cycle | `src/engine/cycles/macro.py` | 11-step nightly reflection: episode selection, clustering, evidence scoring, belief update+decay, memory compaction, goal lifecycle, drive review, nightly clearing |
| `trace_viewer` | `src/cli/trace_viewer.py` | Human-readable rendering of cycle logs, policy outcomes, and macro-cycle details |
| `metrics` | `src/eval/metrics.py` | `CycleSnapshot`-based MCS/ISS/ECI computation, `rollback_rate`, `compute_all_metrics` |
| Config loader | `src/engine/modules/_config.py` | Cached YAML section loader (includes `load_reflection_config`, `load_goals_config`, etc.) |
| Step factory | `src/engine/default_setup.py` | `register_default_steps()` — wires all cycle steps including `decay_unreinforced_beliefs` onto an `EgoOrchestrator` |

### CP-3 Exit Gates (all verified)

1. Drive values remain bounded [0.0, 1.0] under 144-tick (72-hour) simulation with no satisfaction events
2. Satisfaction events reduce the correct mapped drives per `config/defaults.yaml` satisfaction_map
3. Desires are generated only when drive value ≥ `impulse_threshold`
4. Desire objects never appear in the episodic store — only the thoughts they trigger are persisted

**Suggested stack (v0.16):** SQLite (state store), ChromaDB (vector retrieval), asyncio scheduler, all-MiniLM-L6-v2 embeddings, local LLM inference via llama.cpp/vLLM.

## Checkpoint Matrix (CP-0..CP-6)

| Checkpoint | Status | Scope | Owning modules/files |
|---|---|---|---|
| **CP-0** | **Done** | Schema/state contracts, single-writer ownership, deterministic cycle ordering contracts | `src/schema/state.py`, `src/schema/mutability.py`, `src/schema/validator.py`, `src/engine/contracts.py`, `tests/test_schema.py`, `tests/test_contracts.py` |
| **CP-1** | **Done** | Transaction-safe orchestrator, cycle logging/hash deltas, append-only episodic store, interaction retrieval/salience/context packaging, replay determinism | `src/engine/orchestrator.py`, `src/engine/cycle_log.py`, `src/store/episodic_store.py`, `src/engine/retrieval.py`, `src/engine/cycles/interaction.py`, `tests/test_orchestrator.py`, `tests/replay/test_determinism.py`, `tests/test_retrieval_and_interaction.py` |
| **CP-2** | **Done** | Hybrid retrieval scorer with explainability, interaction steps C/D/F, constitution belief bootstrap, evaluation metrics | `src/engine/retrieval.py`, `src/engine/cycles/interaction.py`, `src/schema/state.py`, `src/eval/metrics.py`, `tests/eval/test_metrics.py`, `tests/test_retrieval_and_interaction.py` |
| **CP-3** | **Done** | Affect + drive dynamics, desire generation/crystallization, fast-tick and slow-tick pipelines behavior-complete | `src/engine/modules/`, `src/engine/cycles/fast_tick.py`, `src/engine/cycles/slow_tick.py`, `src/engine/default_setup.py`, `tests/test_fast_tick.py`, `tests/test_slow_tick.py` |
| **CP-4** | **Done** | Full macro-cycle: episode selection + recency filter, evidence scoring, belief update with new-statement cap, confidence decay for unreinforced beliefs, goal lifecycle (staleness/abandonment/suspension), nightly ephemeral clearing, determinism replay test | `src/engine/cycles/macro.py`, `src/engine/contracts.py`, `src/engine/default_setup.py`, `tests/test_macro_tick.py`, `tests/test_default_setup.py` |
| **CP-5** | **Done** | `PolicyOutcome` governance objects, interaction `policy_and_consistency_check` wired, episodic store lifecycle transitions, user-initiated `forget`/`forget_bulk`, PII redaction before long-term commit, macro-cycle memory compaction, trace viewer | `src/engine/governance.py`, `src/engine/pii_redaction.py`, `src/engine/cycles/_store_helpers.py`, `src/engine/cycles/interaction.py`, `src/store/episodic_store.py`, `src/cli/trace_viewer.py`, `tests/test_governance.py` |
| **CP-6** | **In progress** | MCS/ISS/ECI metrics implemented, multi-day replay harness with 7 tests, determinism fix for desire/goal IDs | `src/eval/metrics.py`, `tests/replay/test_multi_day.py`, `tests/fixtures/multi_day.json` |

## Remaining Work

### CP-6 — Evaluation (remaining items)

- **Longitudinal drift alerts:** ISS/ECI delta thresholds across replay runs to flag identity drift
- **Operational readiness:** P95 context-build latency target < 250 ms (excluding LLM)
- **Interaction cycle render stub:** `render_response` remains LLM-dependent; the hard-limit and value checks in `policy_and_consistency_check` operate on real candidate text once wired to an LLM
