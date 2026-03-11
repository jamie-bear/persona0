# Evaluation thresholds (checkpoint-aligned)

These eval fixtures and tests enforce the execution checkpoints in `_knowledge/execution/implementation_v0.10/checkpoints/execution_checkpoints.md`:

- **CP-2 retrieval checks**
  - `self_relevant_top5_presence_rate >= 0.80` (explicit checkpoint threshold).
  - `precision_at_5_mean >= 0.60` (project target for sampled turns; configurable via `EvaluationThresholds.precision_at_5_min`).
- **CP-4 self-belief safety checks**
  - Accepted confidence updates must respect delta cap `<= +0.15`.
  - Contradictions against core values/founding traits must be rejected (zero accepted contradictions).

Pytest coverage for these scenarios lives in `tests/eval/test_metrics.py`.
