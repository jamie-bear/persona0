# Persona0 Ego Engine Architecture (Refined)

* Version: 0.15
* Status: research-grade specification for an executable prototype
* Scope: architecture only (data spec and rollout plan are in sibling docs)

---

## 1) System objective

Persona0 should produce a **consistent first-person identity over time** while keeping the LLM in a bounded role:

* LLM = language rendering + semantic parsing
* Ego Engine = memory, appraisal, salience, goal arbitration, and state transitions

This keeps cognition inspectable, debuggable, and persistent across model swaps.

---

## 2) Corrections from v0.1

### 2.1 Overextended claims vs. testability
v0.1 mixes literature review, implementation guidance, and aspirational claims in each file. v0.15 separates concerns into:

1. architecture contract,
2. data contract,
3. cognitive loop runtime,
4. delivery plan.

### 2.2 Ambiguous module boundaries
v0.1 implies modules, but ownership of state transitions is unclear. v0.15 defines **single-writer ownership**:

* Emotion module writes affect state only.
* Memory module writes episodic/semantic/self layers only.
* Goal module writes priorities and progress only.
* Cognitive loop orchestrator writes cycle metadata and enforces ordering.

### 2.3 Missing safety and disclosure path
v0.15 includes required product-level constraints:

* disclose AI identity,
* no anthropomorphic deception,
* bounded memory retention policy,
* user-requested forget/delete semantics.

---

## 3) Runtime layers

## 3.1 Interaction layer
Input: user message + metadata (time, channel, trust level).
Output: response draft + tool actions.

Responsibilities:
* detect intent, emotional cues, and memory hooks,
* request context from the Ego Engine,
* render final response under style/persona constraints.

## 3.2 Ego Engine core
Deterministic orchestrator that executes the cognitive cycle defined in `cognitive_loop.md`.

Responsibilities:
* update homeostatic variables,
* appraise events,
* rank salience candidates,
* schedule reflection,
* commit memory writes transactionally.

## 3.3 Memory fabric
Three stores + one index:

1. `episodic_log` (append-only events)
2. `semantic_store` (stable extracted facts)
3. `self_model` (identity beliefs with confidence and revision history)
4. `retrieval_index` (vector + symbolic keys)

Retrieval score should be hybrid:
`score = sim * w_sim + recency * w_r + importance * w_i + self_relevance * w_s`.

## 3.4 Governance layer
Cross-cutting controls:
* disclosure enforcement,
* policy checks,
* PII redaction before long-term commit,
* audit log for every write.

---

## 4) Canonical state schema (minimum)

```yaml
agent_state:
  timestamp_utc: ISO8601
  affect:
    valence: -1.0..1.0
    arousal: 0.0..1.0
    stress: 0.0..1.0
    energy: 0.0..1.0
  drives:
    social_need: 0.0..1.0
    mastery_need: 0.0..1.0
    rest_need: 0.0..1.0
  goals:
    active_goal_ids: []
  attention:
    current_focus: string
    salience_buffer: []
  safety:
    disclosure_last_shown_at: ISO8601|null
```

Design rule: each state field must have exactly one updater module.

---

## 5) Conversation transaction contract

1. Parse user turn into `event_candidate`.
2. Retrieve top-k memories (hybrid retrieval).
3. Run appraisal against active goals and affect.
4. Build response context package.
5. LLM renders candidate reply.
6. Post-check for policy, consistency, and disclosure.
7. Commit resulting event + derived updates.

If step 6 fails, do not commit writes from this turn.

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
* unconstrained synthetic memory generation.

---

## 8) Immediate implementation recommendation

Build a thin vertical slice first:

* single-user profile,
* one active goal,
* episodic writes + retrieval,
* basic affect updates,
* nightly reflection batch.

Then add richer drives and multi-goal arbitration.
