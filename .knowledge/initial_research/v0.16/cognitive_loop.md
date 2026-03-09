# Persona0 Cognitive Loop Specification (v0.15)

This document defines the missing runtime core that connects architecture, memory, and dialogue.

---

## 1) Why this file exists

The previous docs describe modules but not a strict loop contract. Without a loop contract, behavior drifts and testability suffers.

---

## 2) Cycle types

1. **Interaction cycle**: runs per user turn.
2. **Background micro-cycle**: runs every N minutes for off-screen cognition.
3. **Reflection macro-cycle**: runs daily/overnight to update higher-level beliefs.

---

## 3) Interaction cycle (authoritative order)

```text
A. ingest_turn
B. parse_intent_affect
C. retrieve_memory_candidates
D. salience_competition
E. appraisal_update
F. build_context_package
G. render_response
H. policy_and_consistency_check
I. commit_or_rollback
```

Rules:
* no persistent writes before step I,
* every selected memory must include `why_selected`,
* if consistency check fails, rollback all turn-derived writes.

---

## 4) Background micro-cycle

Purpose: simulate life between conversations.

Steps:
1. decay/recover homeostatic variables,
2. sample routine event from schedule,
3. optional impulse thought generation,
4. update goal progress estimates,
5. append low-importance episode if threshold met.

Guardrails:
* cap generated episodes per day,
* cap repetitive thought templates,
* avoid writing semantically duplicate events.

---

## 5) Reflection macro-cycle

Purpose: transform noisy episodes into stable but revisable self-knowledge.

Steps:
1. select high-signal episodes from prior window,
2. cluster by topic/goal/affect trajectory,
3. produce candidate reflections,
4. score evidence sufficiency,
5. update self-beliefs with confidence deltas,
6. archive reflection audit trail.

Constraint: no self-belief confidence jump > 0.15 in one macro-cycle.

---

## 6) Data contracts between modules

* parser -> appraisal: `intent`, `topic`, `affect_cues`
* retrieval -> salience: `candidate_id`, `scores`, `recency`, `importance`
* appraisal -> context builder: `dominant_concerns`, `goal_tensions`
* loop -> memory: transaction packet with all derived artifacts

---

## 7) Failure modes and mitigations

1. **Memory flooding** -> importance thresholds + nightly compaction.
2. **Identity oscillation** -> confidence inertia + contradiction checks.
3. **Affect runaway** -> clamped update rules + recovery baselines.
4. **Prompt hijack of persona** -> constitution checks before response emit.

---

## 8) Observability requirements

Per cycle emit structured logs:

```yaml
cycle_log:
  cycle_id: uuid
  cycle_type: interaction|micro|macro
  state_before_hash: string
  selected_memories: [id]
  dominant_goal: goal_id|null
  affect_delta: {}
  write_count: int
  rollback: bool
  duration_ms: int
```

These logs are mandatory for reproducibility and postmortem analysis.

---

## 9) Minimal pseudocode

```python
for cycle in scheduler:
    packet = build_cycle_packet(cycle)
    state_before = snapshot(state)
    derived = run_pipeline(packet, state, memory)

    if not passes_policy(derived) or not passes_consistency(derived, state):
        rollback(state_before)
        log(cycle, rollback=True)
        continue

    commit(derived)
    log(cycle, rollback=False)
```

