"""
GoalSystem — per-tick goal updates, status transitions, and proposal acceptance.

Reference: cognitive_loop.md §3.1 step 6 (UPDATE_GOALS)
           self_editability_policy.md §3.2 (goals mutability)
           config/defaults.yaml [goals.*]
"""
from __future__ import annotations


from typing import Any, Dict, List, Optional

from ...schema.state import GoalRecord
from ._config import load_goals_config


class GoalSystem:
    """Ticks goal progress/frustration and manages status transitions."""

    def tick_goals(
        self,
        goals: List[GoalRecord],
        config: Dict[str, Any] | None = None,
    ) -> List[GoalRecord]:
        """Apply one fast-tick update to all goals.

        Per spec (self_editability_policy.md §3.2):
        - Active goals: passive progress drift (+0.01 if no blockers)
        - Active goals with blockers: frustration grows
        - Active goals without blockers: frustration decays
        - Frustration ≥ suspension_threshold → status = 'suspended'
        """
        cfg = config if config is not None else load_goals_config()
        suspension_threshold = float(cfg.get("frustration_threshold_suspension", 0.75))
        frustration_growth = float(cfg.get("frustration_growth_per_stalled_tick", 0.05))
        frustration_decay = float(cfg.get("frustration_decay_per_progressing_tick", 0.10))

        updated: List[GoalRecord] = []
        for goal in goals:
            if goal.status != "active":
                updated.append(goal)
                continue

            # Copy mutable fields
            progress = goal.progress
            frustration = goal.frustration
            status = goal.status

            stalled = bool(goal.blocked_by)
            if stalled:
                frustration = min(1.0, frustration + frustration_growth)
            else:
                progress = min(1.0, progress + 0.01)
                frustration = max(0.0, frustration - frustration_decay)

            if frustration >= suspension_threshold:
                status = "suspended"

            updated.append(goal.model_copy(update={
                "progress": round(progress, 4),
                "frustration": round(frustration, 4),
                "status": status,
            }))
        return updated

    def accept_proposal(
        self,
        proposal: Dict[str, Any],
        current_goals: List[GoalRecord],
        config: Dict[str, Any] | None = None,
    ) -> Optional[GoalRecord]:
        """Accept or reject a crystallization goal proposal.

        Rejects if:
        - An active goal already has the same crystallized_from_drive
        - The active goal count is at or above max_active_goals
        """
        cfg = config if config is not None else load_goals_config()
        max_goals = int(cfg.get("max_active_goals", 8))

        active_goals = [g for g in current_goals if g.status == "active"]

        if len(active_goals) >= max_goals:
            return None

        drive = str(proposal.get("crystallized_from_drive", ""))
        if drive:
            existing_drives = {
                str(g.crystallized_from_drive or "")
                for g in active_goals
                if g.crystallized_from_drive
            }
            if drive in existing_drives:
                return None

        # Deterministic ID — replay-safe (no uuid4)
        source_desire_id = str(proposal.get("source_desire_id", "unknown"))
        goal_id = f"goal-{drive or 'none'}-{source_desire_id}"
        crystallized_at = str(proposal.get("crystallized_at", ""))
        return GoalRecord(
            id=goal_id,
            label=str(proposal.get("label", "Unnamed goal")),
            motive=str(proposal.get("motive", "")),
            priority=float(proposal.get("priority", 0.40)),
            horizon=str(proposal.get("horizon", "short")),
            progress=0.0,
            frustration=0.0,
            status="active",
            crystallized_from_drive=drive or None,
            crystallized_at=crystallized_at or None,
            created_at=crystallized_at or None,
        )
