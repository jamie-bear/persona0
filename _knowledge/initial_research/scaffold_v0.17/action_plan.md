# Persona0 Delivery Plan

* Version: 0.17
* Goal: convert architecture from concept to measurable prototype in 6 weeks

---

## 1) Strategic issues identified in current project

1. Research docs are strong conceptually but weak on execution checkpoints.
2. No explicit acceptance tests for "believability" claims.
3. Missing operational definition of identity stability and memory coherence.
4. No clear red-team / failure analysis cadence.
5. Drive variables existed in schema without satisfaction dynamics or module ownership (addressed in v0.17).
6. No formal self-editability boundary — risk of accidental writes to immutable state during implementation (addressed in v0.17).

---

## 2) Milestones

### Week 1 — Core scaffolding

Deliverables:
* state schema + validation utilities (including mutability class annotations per `self_editability_policy.md`),
* append-only episodic store,
* deterministic cycle orchestrator skeleton,
* CLI trace viewer.

Exit criteria:
* one synthetic day can be replayed deterministically.

### Week 2 — Retrieval and context assembly

Deliverables:
* hybrid retrieval scorer,
* context pack builder with citation of recalled events,
* observability dashboard (jsonl + notebook).

Exit criteria:
* top-5 recall includes at least 1 self-relevant memory in >80% sampled turns.

### Week 3 — Affect, appraisal, and drives

Deliverables:
* affect update rules,
* goal-affect interaction logic,
* appraisal tags in each event commit,
* **Drive module implementation** (see `drive_system.md`):
  * drive growth rates per fast tick,
  * drive satisfaction map (activity type → drive reduction),
  * `UPDATE_DRIVES` step integrated into fast tick pipeline,
  * desire generation logic for slow tick (`DESIRE_GENERATION` step).

Exit criteria:
* no unbounded affect runaway in 72h simulation,
* drive satisfaction events correctly reduce drive variables in 48h simulation,
* desires are generated when drives exceed configured impulse thresholds.

### Week 4 — Reflection, self-model updates, and mutability enforcement

Deliverables:
* nightly reflection job,
* self-belief confidence adjustment rules,
* contradiction detector for self-beliefs,
* **Mutability enforcement** (see `self_editability_policy.md`):
  * pre-commit validator that checks mutability class per field,
  * `CONST` field write rejection with audit logging,
  * `SELF` field rate-limit enforcement (max +0.15 confidence delta, max 3 new beliefs per cycle),
  * reflection exit gate (evidence count, founding-trait contradiction check).

Exit criteria:
* contradiction alerts generated for synthetic adversarial timelines,
* pre-commit validation rejects writes to `CONST` fields in test scenarios,
* self-belief updates are correctly rate-limited in 7-day simulation.

### Week 5 — Dialogue integration, guardrails, and crystallization

Deliverables:
* LLM response renderer integration,
* safety/disclosure middleware,
* failed-turn rollback behavior,
* **Desire→goal crystallization integration**:
  * crystallization threshold check in slow tick,
  * goal proposal submission to goal system,
  * rate limiting (1 proposal per drive per slow tick),
  * crystallization provenance fields on goal records (`crystallized_from_drive`, `crystallized_at`).

Exit criteria:
* policy check blocks unsafe memory writes reliably in tests,
* crystallized goals appear in goal register after sustained unmet drives in 72h simulation,
* LLM renderer cannot produce writes to persistent state (verified by integration tests).

### Week 6 — Evaluation sprint

Deliverables:
* blinded evaluator scripts,
* coherence and stability metrics,
* drive satisfaction dynamics validation (drives rise/fall appropriately over 30-day simulation),
* mutability class violation audit report,
* final report with gaps and next version priorities.

Exit criteria:
* baseline metric thresholds met (Section 4).

---

## 3) Test matrix

* unit tests: schema, scoring, arbitration logic, mutability class validation, drive satisfaction map,
* simulation tests: 7-day and 30-day runs (including drive dynamics and desire/crystallization cycles),
* scenario tests: stress, rejection, conflicting goals, drive flooding, desire-to-goal overflow,
* regression tests: repeated prompts across days for consistency,
* adversarial tests: attempts to write `CONST` fields via LLM output, prompt injection targeting self-beliefs.

---

## 4) Metrics to track

Primary:
* Memory Coherence Score (MCS)
* Identity Stability Score (ISS)
* Emotional Consistency Index (ECI)
* Contextual Recall Precision@k

Secondary:
* hallucinated-memory rate,
* contradiction rate in self-model,
* average latency per cycle,
* drive satisfaction balance (ratio of satisfied vs. unmet drives over time),
* crystallization rate (goals proposed from desires per day),
* `CONST` violation attempt rate (should be zero after Week 4).

---

## 5) Governance and risk control

* Weekly architecture review (technical).
* Weekly persona ethics review (strategic/product).
* Mandatory red-team scenario before each version tag.
* Mutability class audit on all state writes (automated per `self_editability_policy.md §5`).

---

## 6) Proposed next strategic changes (for your review)

1. **Formalize persona constitution** as a `CONST`-class document consumed at bootstrap — instantiate the fields defined in `self_editability_policy.md §3.1` with concrete values for the first persona.
2. Add **memory confidence lifecycle** service (promote/demote/archive).
3. Build a **counterfactual simulator** to test whether different appraisals produce coherent alternative trajectories.
4. Add **multi-horizon planning** (immediate / weekly / long-term goals) with resource budgeting.
5. Create an **offline benchmark suite** for continuity before any user-facing deployment.
6. Extend **drive system** with additional drive types (e.g., `autonomy_need`, `creativity_need`) once core satisfaction dynamics are validated.
