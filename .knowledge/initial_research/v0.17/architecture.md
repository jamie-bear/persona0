# Persona0 Ego Engine Architecture

* Version: 0.17
* Status: research-grade specification for an executable prototype
* Scope: architecture only (data spec, cognitive loop, drive system, and self-editability policy are in sibling docs)

---

## 1) System objective

Persona0 should produce a **consistent first-person identity over time** while keeping the LLM in a bounded role:

* LLM = language rendering + semantic parsing
* Ego Engine = memory, appraisal, salience, goal arbitration, drive/motivation dynamics, and state transitions

This keeps cognition inspectable, debuggable, and persistent across model swaps.

---

## 2) Corrections from prior versions

### 2.1 Overextended claims vs. testability
v0.1 mixes literature review, implementation details, and product policy in each file. v0.15+ separates concerns into:

1. architecture contract,
2. data contract,
3. cognitive loop runtime,
4. delivery plan.

### 2.2 Ambiguous module boundaries
v0.1 implies modules, but ownership of state transitions is unclear. v0.15+ defines **single-writer ownership**:

* Emotion module writes affect state only.
* Memory module writes episodic/semantic/self layers only.
* Goal module writes priorities and progress only.
* Drive module writes drive variables and generates desires only.
* Cognitive loop orchestrator writes cycle metadata and enforces ordering.

### 2.3 Missing safety and disclosure path
v0.15+ includes required product-level constraints:

* disclose AI identity,
* no anthropomorphic deception,
* bounded memory retention policy,
* user-requested forget/delete semantics.

### 2.4 Drive variables lacked module ownership (v0.16 gap)
In v0.16, drive variables (`social_need`, `mastery_need`, `rest_need`, `curiosity`) appeared in the state schema but had no dedicated module specifying growth, satisfaction, or desire generation. The `IMPULSE_CHECK` step from v0.15 was absent from v0.16's cognitive loop. v0.17 addresses this with the formal Drive module (see `drive_system.md`).

### 2.5 No self-editability boundary specification (v0.16 gap)
Single-writer ownership was declared as a principle but never enumerated per field. v0.17 addresses this with a full mutability table (see `self_editability_policy.md`).

---

## 3) Runtime layers

### 3.1 Interaction layer
Input: user message + metadata (time, channel, trust level).
Output: response draft + tool actions.

Responsibilities:
* detect intent, emotional cues, and memory hooks,
* request context from the Ego Engine,
* render final response under style/persona constraints.

### 3.2 Ego Engine core
Deterministic orchestrator that executes the cognitive cycle defined in `cognitive_loop.md`.

Responsibilities:
* update homeostatic variables (affect + drives),
* appraise events,
* rank salience candidates,
* update drive variables and generate desires (see `drive_system.md`),
* propose goal crystallizations from persistent desires,
* schedule reflection,
* commit memory writes transactionally.

### 3.3 Memory fabric
Three stores + one index:

1. `episodic_log` (append-only events)
2. `semantic_store` (stable extracted facts)
3. `self_model` (identity beliefs with confidence and revision history)
4. `retrieval_index` (vector + symbolic keys)

Retrieval score should be hybrid:
`score = sim * w_sim + recency * w_r + importance * w_i + self_relevance * w_s`.

### 3.4 Governance layer
Cross-cutting controls:
* disclosure enforcement,
* policy checks,
* PII redaction before long-term commit,
* audit log for every write,
* **mutability enforcement** per `self_editability_policy.md` — validates that each write targets a field within the writing module's mutability class (`CONST` fields are rejected at runtime; `SELF` fields are rate-limited).

---

## 4) Canonical state schema (minimum)

```yaml
agent_state:
  timestamp_utc: ISO8601
  affect:                          # Mutability: SELF (Emotion module)
    valence: -1.0..1.0
    arousal: 0.0..1.0
    stress: 0.0..1.0
    energy: 0.0..1.0
  drives:                          # Mutability: SELF (Drive module)
    social_need: 0.0..1.0
    mastery_need: 0.0..1.0
    rest_need: 0.0..1.0
    curiosity: 0.0..1.0
  desires:                         # Mutability: EPH (Drive module, per-tick)
    active_desires: []             # ephemeral desire objects; see drive_system.md §4
    persisted_desires: []          # carried across slow ticks until expiry or crystallization
  goals:                           # Mutability: SELF (Goal module)
    active_goal_ids: []
  attention:                       # Mutability: EPH (Salience Gate)
    current_focus: string
    salience_buffer: []
  activity:                        # Mutability: SELF (Activity Selector, slow tick)
    current_activity: string
  safety:                          # Mutability: CONST (Governance layer)
    disclosure_last_shown_at: ISO8601|null
```

Design rule: each state field must have exactly one updater module. Mutability classes are defined in `self_editability_policy.md §3`.

---

## 5) Conversation transaction contract

1. Parse user turn into `event_candidate`.
2. Retrieve top-k memories (hybrid retrieval).
3. Run appraisal against active goals and affect.
4. Apply drive satisfaction for conversation events (e.g., social interaction reduces `social_need`; see `drive_system.md §3`).
5. Build response context package.
6. LLM renders candidate reply.
7. Post-check for policy, consistency, disclosure, and mutability class enforcement.
8. Commit resulting event + derived updates (or rollback if step 7 fails).

If step 7 fails, do not commit writes from this turn.

---

## 6) Non-functional targets

* P95 context build latency: < 250 ms (excluding LLM generation).
* Memory write durability: no acknowledged write loss.
* Determinism: same input + same state -> same non-LLM transition outputs.
* Explainability: every surfaced memory has `why_selected` metadata.

---

## 7) Anti-patterns to avoid

* letting the LLM mutate persistent state directly,
* storing only summaries (loses reconstructability),
* reflection on every turn (causes identity drift),
* unconstrained synthetic memory generation,
* drive satisfaction without a mapped activity event (see `drive_system.md §9`),
* persisting desire objects to long-term memory (only impulse thoughts are stored),
* allowing writes to `CONST`-class fields at runtime (see `self_editability_policy.md §5`).

---

## 8) Immediate implementation recommendation

Build a thin vertical slice first:

* single-user profile,
* one active goal,
* episodic writes + retrieval,
* basic affect updates,
* drive growth + satisfaction dynamics (see `drive_system.md`),
* nightly reflection batch.

Then add richer drives, multi-goal arbitration, desire generation, and goal crystallization.

---

## 9) Companion documents (v0.17)

| Document | Purpose |
|---|---|
| `cognitive_loop.md` | Tick-by-tick execution cycle of the Ego Engine |
| `drive_system.md` | Drive/Motivation module: satisfaction, desires, crystallization |
| `self_editability_policy.md` | State mutability classes and enforcement policy |
| `ego_data.md` | Data schemas for all record types |
| `action_plan.md` | 6-week delivery plan with milestones |
| `overview/initial_research+instructions.md` | Research synthesis, error analysis, build instructions |
