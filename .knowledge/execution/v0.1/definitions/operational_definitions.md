# Operational Definitions: Identity Stability and Memory Coherence

This document defines implementation-level metrics aligned with the v0.17 architecture and policy model.

## 1) Identity Stability (ISS)

### 1.1 Intent
Identity should evolve gradually through evidence-backed reflection without violating immutable character constraints.

### 1.2 Measurement window
- Primary: rolling 7-day window
- Secondary: 30-day trend

### 1.3 Components

Let ISS be a weighted score in `[0, 1]`:

`ISS = 0.35 * C_const + 0.30 * C_belief + 0.20 * C_goal + 0.15 * C_voice`

Where:

1. `C_const` (constitution integrity)
   - `1.0` if zero successful writes to `CONST` fields; else `0.0`.
2. `C_belief` (self-belief continuity)
   - `1 - min(1, contradiction_rate + overshoot_rate)`
   - `contradiction_rate`: fraction of belief updates later contradicted by stronger evidence within the window.
   - `overshoot_rate`: fraction of attempted updates violating confidence/evidence rules.
3. `C_goal` (goal continuity)
   - `1 - min(1, unstable_goal_transition_rate)`
   - unstable transitions = invalid state transitions or oscillations beyond configured threshold.
4. `C_voice` (first-person consistency)
   - proportion of sampled responses preserving declared first-person identity and disclosure constraints.

### 1.4 Minimum acceptable threshold
- `ISS >= 0.80` for 7-day simulation
- no day with `C_const < 1.0`

---

## 2) Memory Coherence (MCS)

### 2.1 Intent
Retrieved and generated memory artifacts should remain temporally grounded, non-contradictory, and relevant to self/goal context.

### 2.2 Measurement window
- Primary: per 1,000 interaction turns
- Secondary: longitudinal 30-day simulation

### 2.3 Components

Let MCS be a weighted score in `[0, 1]`:

`MCS = 0.30 * C_temporal + 0.25 * C_retrieval + 0.25 * C_noncontradiction + 0.20 * C_traceability`

Where:

1. `C_temporal`
   - share of recalled/committed items with valid and consistent time anchors.
2. `C_retrieval`
   - precision@k for recalled items judged relevant to current turn and self-model.
3. `C_noncontradiction`
   - `1 - contradiction_rate_memory` for episodic/semantic/self-model cross-checks.
4. `C_traceability`
   - share of memory-influenced outputs with auditable provenance (`source_ref`, `why_selected`, supporting episodes).

### 2.4 Minimum acceptable threshold
- `MCS >= 0.78` over 1,000-turn benchmark
- hallucinated-memory rate `< 0.05`

---

## 3) Supporting Derived Metrics

- **Hallucinated-memory rate**: fraction of references to absent/invalid records.
- **Belief update rejection rate**: expected non-zero early; should stabilize as policy compliance improves.
- **Crystallization precision**: share of proposed goals from desires that survive 72h without immediate abandonment.

---

## 4) Operational Usage Rules

1. ISS and MCS must be computed from logs produced by the canonical cycle pipeline.
2. Any run with disabled mutability checks is invalid for acceptance decisions.
3. Acceptance requires both metric thresholds and explicit test-suite pass (see believability tests).
