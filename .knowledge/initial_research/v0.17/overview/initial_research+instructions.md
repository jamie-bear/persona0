# Persona0 Research Synthesis and Build Instructions (v0.17)

This file consolidates project understanding, identifies technical/strategic errors across prior versions, and defines the execution path.

---

## 1) Project understanding (deep summary)

Persona0 is best interpreted as a **stateful cognitive architecture project**, not a pure prompting project.

Core thesis:

> Human-like continuity emerges from externalized autobiographical state, affective regulation, and time-based cognitive updates; language models should express this state, not own it.

Distinctive intent:
* preserve continuity across sessions,
* simulate "off-screen" life between interactions,
* maintain a first-person self-model with change over time,
* remain lightweight enough for rapid iteration.

---

## 2) Technical errors identified across versions

### 2.1 Scope entanglement (v0.1)
Research citations, implementation details, and product policy are interleaved, making execution hard and versioning noisy.

### 2.2 Missing operational definitions (v0.1)
Terms like "believable," "continuity," and "coherence" are not bound to measurable metrics in the architecture spec itself.

### 2.3 Ambiguous write authority (v0.1–v0.15)
The design says LLM should not own cognition, but state mutation authority is not strictly specified.

### 2.4 Weak data governance (v0.1–v0.15)
No concrete lifecycle for memory retention, confidence decay, or deletion propagation.

### 2.5 Reflection cadence risk (v0.1–v0.15)
Frequent reflection without constraints can produce identity drift and brittle overfitting to recent noise.

### 2.6 Drive variables without module ownership (v0.16)
Drive variables (`social_need`, `mastery_need`, `rest_need`, `curiosity`) appeared in the state schema but had:
* no satisfaction model (what reduces a drive),
* no formal desire objects (ephemeral, affect-driven wants distinct from goals),
* no crystallization pathway (how persistent desires become goals),
* no self-editability boundary specification (which fields the agent can change about itself).

v0.17 addresses all four with `drive_system.md` and `self_editability_policy.md`.

---

## 3) Strategic errors

1. Over-indexing on dataset quantity too early; should prioritize loop instrumentation and evaluation harness.
2. Insufficient emphasis on adversarial testing (contradictions, manipulative inputs, memory poisoning).
3. No explicit release gates linking architecture maturity to deployment readiness.
4. Missing separate product doctrine for transparency and user trust.

---

## 4) Refined architecture direction

Use a strict layered model:

1. **Cognitive loop runtime** (deterministic transitions)
2. **Memory fabric** (episodic/semantic/self-model + provenance)
3. **Drive/Motivation system** (drive satisfaction, desire generation, goal crystallization)
4. **Dialogue renderer** (LLM-bound, stateless except turn context)
5. **Governance envelope** (policy + disclosure + audit + mutability enforcement)

Reference companion docs:
* `v0.17/architecture.md`
* `v0.17/ego_data.md`
* `v0.17/cognitive_loop.md`
* `v0.17/drive_system.md`
* `v0.17/self_editability_policy.md`
* `v0.17/action_plan.md`

---

## 5) Build instructions

1. Implement schemas before generation.
2. Build deterministic loop and replay tooling.
3. Add retrieval and context assembly.
4. Implement drive satisfaction dynamics and desire generation as part of the affect system (see `drive_system.md`).
5. Integrate LLM last, behind transaction boundaries.
6. Add reflection and self-model updates only after baseline loop stabilizes; enforce mutability classes per `self_editability_policy.md`.

---

## 6) Evaluation doctrine

Do not claim progress from anecdotal chats alone.

Require all of:
* quantitative continuity/coherence metrics,
* scripted scenario passes,
* human blind ratings,
* regression results across version tags.

---

## 7) Recommended immediate next artifacts

* persona constitution (`persona_constitution.md`) — the `CONST`-class fields defined in `self_editability_policy.md` need a concrete instance with values for the first persona
* memory retention policy (`memory_lifecycle.md`) — full lifecycle: promote/demote/archive/delete with TTL enforcement
* adversarial scenario pack (`eval/adversarial_scenarios.md`)
* benchmark harness spec (`eval/continuity_benchmark.md`)
* configuration defaults (`config/defaults.yaml`) — all tunable parameters including drive growth rates, satisfaction reductions, impulse thresholds, and crystallization rules
