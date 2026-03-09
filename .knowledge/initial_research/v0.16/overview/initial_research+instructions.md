# Persona0 Research Synthesis and Build Instructions (v0.16)

This file consolidates project understanding, identifies technical/strategic errors in v0.1 research artifacts, and defines a cleaner execution path.

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

## 2) Technical errors in current v0.1 documents

### 2.1 Scope entanglement
Research citations, implementation details, and product policy are interleaved, making execution hard and versioning noisy.

### 2.2 Missing operational definitions
Terms like "believable," "continuity," and "coherence" are not bound to measurable metrics in the architecture spec itself.

### 2.3 Ambiguous write authority
The design says LLM should not own cognition, but state mutation authority is not strictly specified.

### 2.4 Weak data governance
No concrete lifecycle for memory retention, confidence decay, or deletion propagation.

### 2.5 Reflection cadence risk
Frequent reflection without constraints can produce identity drift and brittle overfitting to recent noise.

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
3. **Dialogue renderer** (LLM-bound, stateless except turn context)
4. **Governance envelope** (policy + disclosure + audit)

Reference companion docs:
* `.knowledge/initial_research/v0.16/overview/initial_research+instructions.md`
* `.knowledge/initial_research/v0.16/architecture.md`
* `.knowledge/initial_research/v0.16/ego_data.md`
* `.knowledge/initial_research/v0.16/cognitive_loop.md`
* `.knowledge/initial_research/v0.16/action_plan.md`

---

## 5) Build instructions

1. Implement schemas before generation.
2. Build deterministic loop and replay tooling.
3. Add retrieval and context assembly.
4. Integrate LLM last, behind transaction boundaries.
5. Add reflection and self-model updates only after baseline loop stabilizes.

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

* persona constitution (`persona_constitution.md`)
* memory retention policy (`memory_lifecycle.md`)
* adversarial scenario pack (`eval/adversarial_scenarios.md`)
* benchmark harness spec (`eval/continuity_benchmark.md`)
.knowledge/initial_research/v0.16/action_plan.md
