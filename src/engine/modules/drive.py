"""
DriveModule — homeostatic drive growth, satisfaction, desire generation,
and desire→goal crystallization.

Reference: drive_system.md §3-§5, cognitive_loop.md §3.1 step 3.5, §3.2 step 11
           config/defaults.yaml [drives.*]
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...schema.state import DriveState
from ._config import load_drives_config, load_goals_config

_DRIVE_NAMES = ["social_need", "mastery_need", "rest_need", "curiosity"]


class DriveModule:
    """Updates drives, generates ephemeral desires, and checks crystallization."""

    # ── Fast tick ─────────────────────────────────────────────────────────────

    def update(
        self,
        drives: DriveState,
        activity_events: List[Dict[str, Any]],
        config: Dict[str, Any] | None = None,
        rest_boost: float = 0.0,
    ) -> DriveState:
        """Apply growth rates and activity-based satisfaction for one fast tick.

        Args:
            drives: current drive state
            activity_events: list of event dicts; each must have a 'type' key
            config: override config (defaults loaded from YAML if None)
            rest_boost: additional rest_need growth from EmotionModule stress coupling
        """
        cfg = config if config is not None else load_drives_config()
        growth_rates: Dict[str, float] = cfg.get("growth_rate", {})
        satisfaction_map: Dict[str, Any] = cfg.get("satisfaction_map", {})

        values: Dict[str, float] = drives.model_dump()

        # Growth per tick
        for drive in _DRIVE_NAMES:
            values[drive] += growth_rates.get(drive, 0.0)

        # Additional rest boost from high stress
        values["rest_need"] += rest_boost

        # Satisfaction from activity events
        event_types = [str(e.get("type", "")) for e in activity_events]
        for drive in _DRIVE_NAMES:
            drive_cfg = satisfaction_map.get(drive, {})
            satisfiers: List[str] = drive_cfg.get("satisfied_by", [])
            reduction: float = float(drive_cfg.get("reduction_per_event", 0.0))
            for event_type in event_types:
                if event_type in satisfiers:
                    values[drive] -= reduction

        # Clamp all to [0, 1]
        return DriveState(**{d: _clamp(values[d]) for d in _DRIVE_NAMES})

    # ── Slow tick: desire generation ──────────────────────────────────────────

    def generate_desire(
        self,
        drive_name: str,
        drive_value: float,
        tick_counter: int,
        config: Dict[str, Any] | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a Desire-like dict if drive_value ≥ impulse_threshold, else None.

        Per drive_system.md §4: desire objects are ephemeral and never persisted
        to the episodic log.
        """
        cfg = config if config is not None else load_drives_config()
        thresholds: Dict[str, float] = cfg.get("impulse_threshold", {})
        threshold = float(thresholds.get(drive_name, 1.0))

        if drive_value < threshold:
            return None

        # Deterministic ID — replay-safe (no uuid4)
        desire_id = f"desire-{drive_name}-{tick_counter}"

        return {
            "id": desire_id,
            "source_drive": drive_name,
            "urgency": round(drive_value, 4),
            "approach": True,          # simplified: all desires start as approach
            "expires_after_ticks": 3,
            "age_in_ticks": 0,
            "created_at_tick": tick_counter,
            "content": _desire_content(drive_name, drive_value),
        }

    def generate_all_desires(
        self,
        drives: DriveState,
        tick_counter: int,
        config: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Generate desires for all drives that exceed their impulse threshold."""
        results = []
        for drive_name in _DRIVE_NAMES:
            desire = self.generate_desire(
                drive_name, getattr(drives, drive_name), tick_counter, config
            )
            if desire is not None:
                results.append(desire)
        return results

    # ── Slow tick: crystallization ────────────────────────────────────────────

    def check_crystallization(
        self,
        persisted_desires: List[Dict[str, Any]],
        current_goals: List[Any],
        config: Dict[str, Any] | None = None,
        goals_config: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Return GoalProposal dicts for desires that meet crystallization criteria.

        Rules (drive_system.md §5):
        - desire.age_in_ticks >= crystallization_threshold_ticks
        - desire.urgency >= crystallization_urgency_min
        - No existing active goal satisfies the same drive (crystallized_from_drive match)
        - Max 1 proposal per drive per call
        """
        cfg = config if config is not None else load_drives_config()
        gcfg = goals_config if goals_config is not None else load_goals_config()

        threshold_ticks: int = int(cfg.get("crystallization_threshold_ticks", 6))
        urgency_min: float = float(cfg.get("crystallization_urgency_min", 0.65))
        dampen: float = float(gcfg.get("crystallization_priority_dampen", 0.60))

        # Which drives already have an active goal?
        active_drive_goals = {
            _goal_drive(g)
            for g in current_goals
            if _goal_status(g) == "active" and _goal_drive(g)
        }

        proposals: List[Dict[str, Any]] = []
        proposed_drives: set[str] = set()

        for desire in persisted_desires:
            drive = str(desire.get("source_drive", ""))
            age = int(desire.get("age_in_ticks", 0))
            urgency = float(desire.get("urgency", 0.0))

            if drive in proposed_drives:
                continue  # rate limit: max 1 per drive per call
            if age < threshold_ticks:
                continue
            if urgency < urgency_min:
                continue
            if drive in active_drive_goals:
                continue  # existing goal satisfies this drive

            proposals.append({
                "label": f"Address {drive.replace('_', ' ')}",
                "motive": drive,
                "priority": round(urgency * dampen, 4),
                "horizon": "short",
                "progress": 0.0,
                "crystallized_from_drive": drive,
                "crystallized_at": f"tick:{desire.get('created_at_tick', 0)}",
                "source_desire_id": desire.get("id"),
            })
            proposed_drives.add(drive)

        return proposals

    # ── Slow tick: desire lifecycle ───────────────────────────────────────────

    @staticmethod
    def age_and_expire_desires(
        persisted_desires: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Increment age_in_ticks and remove expired desires."""
        aged = []
        for d in persisted_desires:
            d = dict(d)
            d["age_in_ticks"] = d.get("age_in_ticks", 0) + 1
            if d["age_in_ticks"] < d.get("expires_after_ticks", 3):
                aged.append(d)
        return aged

    @staticmethod
    def persist_new_desires(
        active_desires: List[Dict[str, Any]],
        persisted_desires: List[Dict[str, Any]],
        config: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Append high-urgency new desires to persisted list."""
        cfg = config if config is not None else load_drives_config()
        persistence_threshold = float(cfg.get("persistence_threshold", 0.50))
        to_persist = [d for d in active_desires if float(d.get("urgency", 0)) >= persistence_threshold]
        # Deduplicate by source_drive (keep highest urgency)
        by_drive: Dict[str, Dict] = {}
        for d in persisted_desires + to_persist:
            drive = d.get("source_drive", "")
            if drive not in by_drive or float(d.get("urgency", 0)) > float(by_drive[drive].get("urgency", 0)):
                by_drive[drive] = d
        return list(by_drive.values())


# ── helpers ──────────────────────────────────────────────────────────────────

def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _desire_content(drive_name: str, value: float) -> str:
    templates = {
        "social_need": "want to connect with someone",
        "mastery_need": "want to work on something meaningful",
        "rest_need": "want to slow down and rest",
        "curiosity": "want to explore something new",
    }
    content = templates.get(drive_name, f"want to address {drive_name}")
    return f"{content} (intensity {value:.2f})"


def _goal_status(goal: Any) -> str:
    if hasattr(goal, "status"):
        return str(goal.status)
    if isinstance(goal, dict):
        return str(goal.get("status", ""))
    return ""


def _goal_drive(goal: Any) -> str:
    if hasattr(goal, "crystallized_from_drive"):
        return str(goal.crystallized_from_drive or "")
    if isinstance(goal, dict):
        return str(goal.get("crystallized_from_drive") or "")
    return ""
