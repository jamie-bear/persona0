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

Persona0 is now in an **early implementation phase**, not design-only.

- **CP-0 implemented (behavior-complete):** foundational schema/contracts are live in `src/schema` and `src/engine/contracts.py`, with deterministic/ownership validation covered by `tests/test_schema.py` and `tests/test_contracts.py`.
- **CP-1 implemented (behavior-complete):** transactional orchestration, cycle logging, replay determinism checks, append-only episodic persistence, and interaction retrieval flow are implemented in `src/engine/orchestrator.py`, `src/engine/cycle_log.py`, `src/store/episodic_store.py`, `src/engine/retrieval.py`, and `src/engine/cycles/interaction.py`, with exit-gate coverage in `tests/test_orchestrator.py`, `tests/replay/test_determinism.py`, and `tests/test_retrieval_and_interaction.py`.
- **Scaffolded vs complete:** cycle modules under `src/engine/cycles/fast_tick.py`, `slow_tick.py`, and `macro.py` are mostly stubbed function scaffolds (contracts and signatures in place), while CP-0/CP-1 modules above are behavior-complete for their checkpoint goals.

**Suggested stack (v0.16):** SQLite (state store), ChromaDB (vector retrieval), asyncio scheduler, all-MiniLM-L6-v2 embeddings, local LLM inference via llama.cpp/vLLM.

## Checkpoint Matrix (CP-0..CP-6)

| Checkpoint | Status | Scope | Owning modules/files |
|---|---|---|---|
| **CP-0** | **Done** | Schema/state contracts, single-writer ownership, deterministic cycle ordering contracts | `src/schema/state.py`, `src/schema/mutability.py`, `src/schema/validator.py`, `src/engine/contracts.py`, `tests/test_schema.py`, `tests/test_contracts.py` |
| **CP-1** | **Done** | Transaction-safe orchestrator, cycle logging/hash deltas, append-only episodic store, interaction retrieval/salience/context packaging, replay determinism | `src/engine/orchestrator.py`, `src/engine/cycle_log.py`, `src/store/episodic_store.py`, `src/engine/retrieval.py`, `src/engine/cycles/interaction.py`, `tests/test_orchestrator.py`, `tests/replay/test_determinism.py`, `tests/test_retrieval_and_interaction.py` |
| **CP-2** | **In progress** | Fast-tick cognition behavior implementation beyond stubs | `src/engine/cycles/fast_tick.py`, `src/engine/orchestrator.py` |
| **CP-3** | **Not started** | Slow-tick activity/routine/desire behavior completion | `src/engine/cycles/slow_tick.py` |
| **CP-4** | **Not started** | Macro/nightly reflection and self-model update behavior completion | `src/engine/cycles/macro.py` |
| **CP-5** | **Not started** | Governance/policy hardening and user lifecycle operations (forget/delete, redaction lifecycle) | `src/engine/cycles/interaction.py`, `src/store`, `src/cli/trace_viewer.py` |
| **CP-6** | **Not started** | Evaluation harness, benchmarks, and operational readiness hardening | `tests/`, `src/cli`, `config/defaults.yaml` |

## Roadmap Focus (Post CP-1)

1. **Behavioralize existing cycle scaffolds** (`fast_tick`, then `slow_tick`, then `macro`) while keeping deterministic contract ordering intact.
2. **Expand governance completeness** in interaction/store layers (policy checks, delete/forget lifecycle, audit ergonomics).
3. **Operationalize evaluation** by extending replay/continuity benchmarks and adding CP-2..CP-6 exit-gate test coverage.
