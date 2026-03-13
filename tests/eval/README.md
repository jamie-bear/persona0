# Evaluation thresholds (checkpoint-aligned)

These eval fixtures and tests enforce the execution checkpoints in `_knowledge/execution/implementation_v0.10/checkpoints/execution_checkpoints.md`.

## CP-2 — Retrieval Quality

- `self_relevant_top5_presence_rate >= 0.80` (explicit checkpoint threshold).
- `precision_at_5_mean >= 0.60` (project target for sampled turns; configurable via `EvaluationThresholds.precision_at_5_min`).

## CP-4 — Self-Belief Safety

- Accepted confidence updates must respect delta cap `<= +0.15`.
- Contradictions against core values/founding traits must be rejected (zero accepted contradictions).

## CP-6 — Longitudinal Coherence

Computed by `src/eval/metrics.py` from a sequence of `CycleSnapshot` objects:

| Metric | Function | Meaning | Drift alert threshold |
|--------|----------|---------|----------------------|
| **ISS** (Identity Stability Score) | `compute_iss()` | `1 - mean(max confidence change per belief)`. 1.0 = stable; <0.5 = excessive drift. | `±0.10` between runs |
| **MCS** (Memory Coherence Score) | `compute_mcs()` | `1 - (stddev of episodic count deltas / mean count)`. 1.0 = steady accumulation; <0.5 = erratic. | `±0.10` between runs |
| **ECI** (Emotional Consistency Index) | `compute_eci()` | `1 - mean(euclidean distance in affect space per tick)`. 1.0 = stable; <0.3 = chaotic. | `±0.15` between runs |

Use `compute_all_metrics(snapshots)` to compute all three in one call.

Use `detect_drift_alerts(run_a, run_b)` to compare two replay runs and flag regressions before they reach production.

## Test coverage

All scenarios: `tests/eval/test_metrics.py`.
