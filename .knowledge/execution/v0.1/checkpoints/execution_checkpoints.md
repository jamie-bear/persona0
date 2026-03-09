# Execution Checkpoints (v0.1)

Concrete checkpoints derived from the v0.17 milestone intent, with hard gates and required artifacts.

## CP-0: Baseline Contracts Frozen

**Objective**: lock architecture, data schema, and mutability tables as implementation inputs.

**Required artifacts**
- Versioned schema package (state + record types).
- Mutability class registry with field ownership map.
- Loop order contract for interaction/fast/slow/macro cycles.

**Exit gate**
- Schema validator passes against sample packets.
- Field ownership conflicts = 0.
- Deterministic ordering tests pass for all cycle types.

---

## CP-1: Deterministic Core + Replay

**Objective**: ensure non-LLM transition determinism.

**Required artifacts**
- Orchestrator skeleton with transactional commit/rollback.
- Cycle log writer with before-hash and delta fields.
- Synthetic day replay harness.

**Exit gate**
- Same input/state seed produces identical non-LLM outputs.
- Rollback leaves no persistent write residue.
- Replay divergence rate = 0% for baseline scenarios.

---

## CP-2: Memory Retrieval and Context Assembly

**Objective**: ship retrieval and context packaging with explainability.

**Required artifacts**
- Hybrid scorer implementation (`sim`, `recency`, `importance`, `self_relevance`).
- Top-k retrieval service with `why_selected` traces.
- Context package assembler for renderer.

**Exit gate**
- Recall Precision@5 meets target in sampled turns.
- ≥80% sampled turns include at least one self-relevant memory in top-5.
- All selected memories carry explainability metadata.

---

## CP-3: Affect + Drive Dynamics + Desire Generation

**Objective**: implement homeostatic dynamics and impulse generation.

**Required artifacts**
- Affect update rules and decay.
- Drive growth/satisfaction update implementation.
- Slow-tick desire generator with persistence/expiry handling.
- Desire-triggered thought tagging (`trigger=desire`).

**Exit gate**
- Drive values remain bounded [0,1] under simulation.
- Satisfaction events reduce mapped drives correctly.
- Desires generated only when thresholds exceeded.
- Desire objects never persist to long-term storage.

---

## CP-4: Reflection + Self-Editability Enforcement

**Objective**: make adaptive identity updates safe, evidence-backed, and rate-limited.

**Required artifacts**
- Nightly reflection clustering pipeline.
- Self-belief update engine with confidence caps.
- Pre-commit mutability validator.
- Reflection exit gate with contradiction checks.

**Exit gate**
- Writes to `CONST` fields are rejected and audit-logged.
- Confidence deltas above +0.15 are blocked.
- High-confidence belief updates require ≥2 independent reflections.
- Contradictions with core values/founding traits are rejected.

---

## CP-5: Dialogue Integration + Guardrails + Crystallization

**Objective**: integrate renderer safely and complete desire→goal flow.

**Required artifacts**
- Renderer interface (text candidate only, no writes).
- Post-render policy and consistency checks.
- Desire crystallization checker + goal proposal flow.

**Exit gate**
- Integration tests prove renderer cannot mutate persistent state.
- Unsafe writes trigger rollback reliably.
- Crystallized goals include provenance (`crystallized_from_drive`, `crystallized_at`).
- Crystallization rate-limiter enforced (max 1/drive/slow tick).

---

## CP-6: Believability Evaluation Release Gate

**Objective**: establish measurable readiness for external evaluation.

**Required artifacts**
- ISS/MCS metric jobs and dashboards.
- Believability acceptance test suite (see sibling doc).
- Red-team scenario report and regression pack.

**Exit gate**
- All P0 acceptance tests pass.
- ISS and MCS exceed minimum thresholds for 30-day simulation.
- Critical policy violations = 0.
- Release report includes known limitations and next-iteration backlog.
