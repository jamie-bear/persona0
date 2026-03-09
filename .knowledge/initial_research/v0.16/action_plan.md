# Persona0 Delivery Plan (v0.15)

* Goal: convert architecture from concept to measurable prototype in 6 weeks

---

## 1) Strategic issues identified in current project

1. Research docs are strong conceptually but weak on execution checkpoints.
2. No explicit acceptance tests for "believability" claims.
3. Missing operational definition of identity stability and memory coherence.
4. No clear red-team / failure analysis cadence.

---

## 2) Milestones

## Week 1 — Core scaffolding

Deliverables:
* state schema + validation utilities,
* append-only episodic store,
* deterministic cycle orchestrator skeleton,
* CLI trace viewer.

Exit criteria:
* one synthetic day can be replayed deterministically.

## Week 2 — Retrieval and context assembly

Deliverables:
* hybrid retrieval scorer,
* context pack builder with citation of recalled events,
* observability dashboard (jsonl + notebook).

Exit criteria:
* top-5 recall includes at least 1 self-relevant memory in >80% sampled turns.

## Week 3 — Affect and appraisal

Deliverables:
* affect update rules,
* goal-affect interaction logic,
* appraisal tags in each event commit.

Exit criteria:
* no unbounded affect runaway in 72h simulation.

## Week 4 — Reflection and self-model updates

Deliverables:
* nightly reflection job,
* self-belief confidence adjustment rules,
* contradiction detector for self-beliefs.

Exit criteria:
* contradiction alerts generated for synthetic adversarial timelines.

## Week 5 — Dialogue integration and guardrails

Deliverables:
* LLM response renderer integration,
* safety/disclosure middleware,
* failed-turn rollback behavior.

Exit criteria:
* policy check blocks unsafe memory writes reliably in tests.

## Week 6 — Evaluation sprint

Deliverables:
* blinded evaluator scripts,
* coherence and stability metrics,
* final report with gaps and next version priorities.

Exit criteria:
* baseline metric thresholds met (Section 4).

---

## 3) Test matrix

* unit tests: schema, scoring, arbitration logic,
* simulation tests: 7-day and 30-day runs,
* scenario tests: stress, rejection, conflicting goals,
* regression tests: repeated prompts across days for consistency.

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
* average latency per cycle.

---

## 5) Governance and risk control

* Weekly architecture review (technical).
* Weekly persona ethics review (strategic/product).
* Mandatory red-team scenario before each version tag.

---

## 6) Proposed next strategic changes (for your review)

1. Introduce a **persona constitution** file defining non-negotiable traits and hard boundaries.
2. Add **memory confidence lifecycle** service (promote/demote/archive).
3. Build a **counterfactual simulator** to test whether different appraisals produce coherent alternative trajectories.
4. Add **multi-horizon planning** (immediate / weekly / long-term goals) with resource budgeting.
5. Create an **offline benchmark suite** for continuity before any user-facing deployment.
