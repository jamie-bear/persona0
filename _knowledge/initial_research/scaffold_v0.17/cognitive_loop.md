# Persona0 Cognitive Loop Specification

* Version: 0.17
* Status: research-grade specification
* Changes from v0.16: integrates Drive module (`UPDATE_DRIVES` step), replaces informal `IMPULSE_CHECK` with formal `DESIRE_GENERATION`, adds desire-to-thought data contract

---

## 1) Cycle Types

| Cycle | Cadence | Purpose |
|---|---|---|
| **Interaction cycle** | Per user turn | Conversation integration, transactional |
| **Background micro-cycle** | ~30 min (fast tick) + ~2–4 hr (slow tick) | Off-screen cognition, drive updates, thought generation |
| **Reflection macro-cycle** | Daily/nightly | Memory consolidation, self-belief updates |

---

## 2) Interaction Cycle (authoritative order)

```
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
- No persistent writes before step I
- Every selected memory must include `why_selected`
- If step H fails, rollback all turn-derived writes
- LLM renderer (step G) may not produce writes; it returns a candidate string only
- Drive satisfaction events from conversation (e.g., social interaction) are applied at step I as part of the commit packet

---

## 3) Background Micro-Cycle

### 3.1 Fast Tick (~30 min)

Purpose: maintain ongoing internal life — thought, emotion drift, drive decay, state maintenance.

```
1. WORLD_INGEST
   - Query world state adapter for new events since last tick

2. APPRAISE
   - Evaluate each event against active goals, self-model, current emotion
   - Produce appraisal_results[]

3. UPDATE_EMOTION
   - Apply appraisal-driven affect updates
   - Apply time-based decay (stress recovery, energy drain)
   - Apply circadian modulation

3.5. UPDATE_DRIVES  [NEW in v0.17]
   - For each drive variable, apply natural growth rate
   - For each activity event in current tick, apply satisfaction reduction if event.type is in satisfaction_map[drive]
   - Clamp all drives to [0.0, 1.0]
   - See drive_system.md §3 for rates and satisfaction map

4. GENERATE_THOUGHT
   - Select thought category based on emotion, goals, recent_thoughts
   - If active_desires is non-empty, bias category selection toward desire-mapped categories
     (see drive_system.md §7 for drive→category mapping)
   - Retrieve context memories
   - Generate thought; tag with trigger=internal or trigger=desire if desire-sourced

5. SALIENCE_FILTER
   - Collect candidates: events, appraisals, generated thought
   - Filter by emotional intensity, goal relevance, recency, novelty
   - Capacity: 5 items

6. UPDATE_GOALS
   - Tick goal progress/frustration based on appraisals
   - Check suspension/abandonment thresholds

7. WRITE_MEMORY
   - Append generated thought as episodic record
   - Append significant appraisals as episodic records
   - Note: desire objects are NOT written; only the thought they influenced is written

8. LOG
   - Emit structured cycle log (see §6)
```

### 3.2 Slow Tick (~2–4 hr)

Runs all fast tick steps first, then adds:

```
9. ACTIVITY_TRANSITION
   - Select activity appropriate to circadian phase, energy, goals, day pattern
   - Generate activity event; update current_state.current_activity

10. ROUTINE_EVENT
    - Generate a routine experience based on current activity
    - Store as episodic memory

11. DESIRE_GENERATION  [replaces informal IMPULSE_CHECK from v0.15]
    active_desires = []
    for each drive in agent_state.drives:
      if drive.value >= impulse_threshold[drive.name]:
        desire = drive_module.generate_desire(
          drive=drive.name,
          value=drive.value,
          current_goals=active_goals,
          current_activity=current_activity
        )
        active_desires.append(desire)
    current_state.active_desires = active_desires

    # Crystallization check
    for each desire in persisted_desires (carried from previous slow ticks):
      if desire.age_in_ticks >= crystallization_threshold:
        if desire.urgency >= crystallization_urgency_min:
          goal_system.propose(goal_from_desire(desire))
    # Max 1 new goal proposal per drive per slow tick

    # Desire objects older than expires_after_ticks are discarded
    current_state.persisted_desires = [d for d in persisted_desires if not d.expired]
    current_state.persisted_desires += [d for d in active_desires if d.urgency >= persistence_threshold]
```

Guardrails:
- Cap generated episodes per day
- Cap repetitive thought templates (no more than 3 consecutive same-category thoughts)
- Avoid writing semantically duplicate events

---

## 4) Reflection Macro-Cycle (nightly)

Purpose: transform noisy episodes into stable but revisable self-knowledge.

```
1. Select high-signal episodes from prior 24-hour window
2. Cluster by topic / goal / affect trajectory (embedding similarity)
3. Produce candidate reflections per cluster
4. Score evidence sufficiency per reflection
5. Update self-beliefs with confidence deltas
   - Max Δ confidence: +0.15 per cycle
   - Requires ≥2 independent reflections before confidence > 0.75
   - Check proposed belief against CONST.founding_traits and CONST.core_values
     — reject if contradiction detected
6. Archive reflection and audit trail
7. Goal review: reprioritize, suspend, complete, or abandon goals
8. Drive review: log unmet drives; escalate persistent desires if crystallization criteria met
```

Constraint: the full evidence chain for every self-belief update must be stored in the reflection audit trail. This supports the traceability requirement in `self_editability_policy.md §5.2`.

---

## 5) Data Contracts Between Modules

```
drive_module -> thought_generator: active_desires[] (trigger, source_drive, urgency, approach)
parser -> appraisal: intent, topic, affect_cues
retrieval -> salience: candidate_id, scores, recency, importance
appraisal -> context_builder: dominant_concerns, goal_tensions
drive_module -> goal_system: GoalProposal (from crystallization)
loop -> memory: transaction packet with all derived artifacts
```

---

## 6) Observability: Cycle Log Schema

```yaml
cycle_log:
  cycle_id: uuid
  cycle_type: interaction|fast|slow|macro
  state_before_hash: string
  selected_memories: [id]
  dominant_goal: goal_id|null
  affect_delta: {}
  drive_delta: {}          # NEW: drive state changes this cycle
  desires_generated: int   # NEW: count of desire objects created
  desires_crystallized: int # NEW: count of goals proposed from desires
  write_count: int
  rollback: bool
  duration_ms: int
```

---

## 7) Failure Modes and Mitigations

| Failure mode | Mitigation |
|---|---|
| Memory flooding | Importance thresholds + nightly compaction |
| Identity oscillation | Confidence inertia + contradiction checks against CONST fields |
| Affect runaway | Clamped update rules + recovery baselines |
| Drive flooding (all drives high simultaneously) | Total drive update is capped per tick; drives share a budget |
| Desire-to-goal flooding | One crystallization proposal per drive per slow tick max |
| Prompt hijack of persona | Constitution checks before response emit; CONST fields non-writable |
| LLM writing self-beliefs | Governance pre-commit check; LLM renders text only, never writes state |

---

## 8) Pseudocode (top-level orchestrator)

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

The drive and desire pipeline runs inside `run_pipeline`. Drive satisfaction events from the interaction cycle are included in the transaction packet at commit time.
