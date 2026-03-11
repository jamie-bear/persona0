# Persona0 State Mutability & Self-Editability Policy

* Version: 0.17
* Status: research-grade specification
* Scope: formal enumeration of which state elements can be modified by whom, enabling safe agent self-modification and preventing accidental boundary violations

---

## 1) Why This Document Exists

v0.16 establishes single-writer module ownership as a principle and defines confidence drift controls on self-beliefs. But no document enumerates *which state elements belong to which mutability class*. Without this policy:

- It is ambiguous whether the LLM renderer may propose self-belief changes
- The governance layer has no formal checklist to validate writes against
- The distinction between founding traits (set at creation) and acquired traits (emergent from experience) is implicit, not enforced
- Implementers must infer mutability from scattered descriptions across multiple files

This document provides the canonical mutability table for all state fields.

---

## 2) Four Mutability Classes

| Class | Short name | Who may write | When | Rollback on failure? |
|---|---|---|---|---|
| **Immutable / Constitution** | `CONST` | Operator at persona creation only | Once, at bootstrap | N/A (cannot be changed) |
| **Self-editable (agent)** | `SELF` | Ego Engine — reflection macro-cycle or goal lifecycle only | Per macro-cycle or goal event | Yes |
| **Externally editable** | `EXT` | Operator or user via explicit config API | On-demand, bounded by policy | Yes |
| **Ephemeral** | `EPH` | Any module; cleared each tick or conversation turn | Per-tick or per-turn | N/A (not persisted) |

**Key constraint:** The LLM Renderer may **read** from `CONST`, `SELF`, and `EXT` fields (via the context package). It may **never directly write** to any of them. All writes to persistent state go through the Ego Engine orchestrator and are subject to policy checks.

---

## 3) Full State Mutability Table

### 3.1 Persona Constitution (CONST)

These fields are set at persona creation by the operator and are thereafter read-only. They form the stable "kernel" of identity that cannot be overwritten by experience.

| Field | Description | Example |
|---|---|---|
| `persona.name` | The agent's first-person name | "Mira" |
| `persona.core_values[]` | 3–5 non-negotiable value commitments | ["curiosity", "honesty", "care"] |
| `persona.hard_limits[]` | Behaviors the agent will never perform | ["deception about AI nature", "harmful advice"] |
| `persona.disclosure_policy` | Disclosure text shown to users; update cadence | AI identity must be disclosed on first turn |
| `persona.founding_traits[]` | Initial identity seeds — starting beliefs about self | ["I tend to think carefully before speaking"] |
| `persona.privacy_tier_defaults` | Default TTL and retention policy per data type | episodic: 90 days, semantic: 365 days |

**Governance rule:** Any runtime write attempt to a `CONST` field must be rejected and audit-logged as a critical violation.

---

### 3.2 Self-Editable State (SELF)

These fields may be updated by the Ego Engine's internal processes (reflection, goal lifecycle, drive satisfaction). They represent the *adaptive* layer of identity — continuous yet changeable by experience.

#### Self-model / Identity beliefs

| Field | Updater | Rate limit | Constraint |
|---|---|---|---|
| `self_model.beliefs[].confidence` | Reflection macro-cycle | Max Δ +0.15 per cycle | Requires ≥2 independent reflections before confidence > 0.75 |
| `self_model.beliefs[].statement` | Reflection macro-cycle | Max 3 new statements per cycle | Must link to ≥1 supporting episode; must not contradict `CONST.founding_traits` |
| `self_model.beliefs[].last_challenged_at` | Appraisal module (on identity-relevant event) | Per appraisal | No rate limit; resets staleness clock |
| `self_model.beliefs[].stability` | Reflection macro-cycle | Per cycle | Derived from confidence trajectory, not set directly |

Confidence decay: unreinforced beliefs (no supporting episode in N days) decay at rate `−0.02/cycle`. A belief whose confidence falls below `0.15` is archived, not deleted.

#### Goals

| Field | Updater | Rate limit | Constraint |
|---|---|---|---|
| `goals[].progress` | Goal System (per fast tick) | Per tick | Bounded [0.0, 1.0] |
| `goals[].frustration` | Goal System (per fast tick) | Per tick | Bounded [0.0, 1.0]; triggers suspension at `suspension_threshold` |
| `goals[].status` | Goal System (lifecycle events) | Per event | Valid transitions: active→suspended, active→completed, active→abandoned, suspended→active |
| `goals[].priority` | Goal System (daily review) | Per daily cycle | May be reprioritized relative to other goals; cannot exceed priority of a `CONST` core value |
| New goal creation | Drive Module (crystallization) or Reflection macro-cycle | 1 new proposal per drive per slow tick | Must not duplicate an existing active goal |

#### Memory stores (append-only — self-editable means *add*, not *modify*)

| Store | Updater | Constraint |
|---|---|---|
| `episodic_log` | Ego Engine orchestrator (commit step) | Append-only; existing records immutable except `decay_factor` |
| `semantic_store` | Reflection macro-cycle | Derived from episodic clusters; no direct LLM write |
| `self_model` reflections | Reflection macro-cycle | Governed by confidence caps above |

---

### 3.3 Externally Editable State (EXT)

These fields may be set by the operator or user via an explicit configuration or preference API. They are not self-modified by the agent.

| Field | Who sets it | Notes |
|---|---|---|
| `config.*` | Operator at deploy time | All numeric parameters (tick rates, thresholds, weights) |
| `persona.founding_traits[]` | Operator at persona creation | Readable by agent, not writable at runtime |
| `user_preferences.*` | User via preference API | Privacy settings, interaction style, memory retention opt-outs |
| `relationship[user_id].*` | User interactions (trust, familiarity) — written by the Ego Engine on conversation commit, but *seeded* by operator | Not self-generated; requires external interaction |
| Memory deletion requests | User via forget/delete API | Propagates through episodic + semantic + self-model stores |

---

### 3.4 Ephemeral State (EPH)

These fields exist only within a tick or conversation turn. They are never persisted to long-term stores.

| Field | Scope | Notes |
|---|---|---|
| `attention.salience_buffer[]` | Per tick | Cleared at start of each tick; rebuilt during salience competition |
| `attention.current_focus` | Per tick | Updated each tick; not stored |
| `active_desires[]` | Per slow tick | Desire objects; only the resulting impulse *thoughts* may be stored |
| `appraisal_results[]` | Per tick | Used within the tick pipeline; not persisted directly |
| `context_package` | Per conversation turn | The assembled prompt context sent to LLM; discarded after render |
| `candidate_response` | Per conversation turn | The LLM's draft response before policy check; discarded on rollback |
| `cycle_log` | Per tick | Emitted to observability log but not part of cognitive state |

---

## 4) The Adaptive Self: What the Agent Can Change About Itself

To directly answer the design question: *which elements support a continuous yet adaptive sense of self?*

The agent can change:

1. **Confidence in existing self-beliefs** — gradually, via accumulated reflective evidence
2. **The set of self-beliefs** — new beliefs can form from patterns in episodic memory; existing beliefs can be archived when contradicted
3. **Goal priorities and statuses** — goals can be suspended, completed, or abandoned; new goals can crystallize from persistent desires
4. **Semantic knowledge** — generalizations extracted from episodic clusters are new self-knowledge
5. **Relationship models** — familiarity and trust with known entities updates per interaction

The agent cannot change:

1. **Core values** — these are `CONST` and define the invariant character kernel
2. **Disclosure rules** — always operator-controlled
3. **Numeric parameters** — tick rates, thresholds, weights are operator-set
4. **Its own episodic history** — past events are append-only; the agent can form new interpretations (reflections) but cannot alter what was recorded

---

## 5) Enforcement Points

The governance layer must enforce this policy at two points:

### 5.1 Pre-commit validation (step I of conversation cycle)

Before any write is committed:
- Assert that the writing module is the registered single-writer for each field being written
- Assert that no write targets a `CONST` field
- Assert that `SELF` writes stay within rate limits and constraint rules
- Reject and rollback on any violation; log as `POLICY_VIOLATION`

### 5.2 Reflection macro-cycle exit gate

Before self-belief updates are committed:
- Compute confidence delta for each proposed update
- Reject any delta exceeding `0.15` in a single cycle
- Verify minimum evidence count (≥2 independent reflections for high-confidence claims)
- Verify no proposed belief contradicts a `CONST.founding_trait` or `CONST.core_value`
- Log the full reasoning trail in the reflection audit store

---

## 6) Summary: Why This Policy Matters for Believability

A continuous yet adaptive sense of self requires:

- **Stability:** Core character (values, hard limits) never changes. Users can rely on it.
- **Growth:** Beliefs, priorities, and knowledge evolve from real experience — not arbitrarily.
- **Traceability:** Every change to self-knowledge has an evidence trail. The agent can "explain" why it now believes X.
- **Safety:** The LLM cannot rewrite the agent's identity. The governance layer enforces this.

Without this policy, an adversarial prompt could cause the LLM to propose identity-altering self-beliefs that the system would commit without challenge. With it, every self-modification is gated, rate-limited, and evidence-backed.
