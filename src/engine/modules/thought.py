"""
ThoughtGenerator — deterministic category selection and template-based thought text.

Reference: cognitive_loop.md §3.1 step 4 (GENERATE_THOUGHT)
           drive_system.md §7 (desire → thought category mapping)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from ...schema.state import AgentState, AffectState, DriveState

# Thought categories (from ego_data.md §2.2)
CATEGORIES = ["reflection", "planning", "rumination", "curiosity",
              "self-evaluation", "social", "fantasy"]

# Templates per category: 4 slots so we can vary by tick parity
_TEMPLATES: Dict[str, List[str]] = {
    "reflection": [
        "Thinking about what matters most right now.",
        "Sitting with a quiet sense of what today has been.",
        "Noticing patterns in how things have been going lately.",
        "Wondering what I make of recent events.",
    ],
    "planning": [
        "Thinking through what needs to happen next.",
        "Mapping out steps to move something forward.",
        "Weighing different approaches to a current challenge.",
        "Imagining what progress would look like.",
    ],
    "rumination": [
        "Turning something difficult over in my mind again.",
        "Finding it hard to set aside what's been bothering me.",
        "Dwelling on something that didn't go the way I hoped.",
        "Replaying a moment that still feels unresolved.",
    ],
    "curiosity": [
        "Wondering about something I don't fully understand yet.",
        "Feeling pulled toward a question I haven't explored.",
        "Noticing an interesting idea I'd like to think through.",
        "Something unfamiliar has caught my attention.",
    ],
    "self-evaluation": [
        "Asking myself whether I'm living up to what I care about.",
        "Reconsidering how I handled something recently.",
        "Checking in with whether I'm on the right track.",
        "Wondering if I could do better in some area.",
    ],
    "social": [
        "Thinking about someone I'd like to reach out to.",
        "Remembering a recent exchange that stayed with me.",
        "Wondering how someone I care about is doing.",
        "Feeling the pull of wanting to connect.",
    ],
    "fantasy": [
        "Imagining a quiet, low-demand stretch of time.",
        "Daydreaming about stepping back from everything for a bit.",
        "Picturing a simpler moment without any pressing demands.",
        "Wishing for a slower pace, at least for now.",
    ],
}

# Mapping from source_drive + approach to thought category (drive_system.md §7)
_DESIRE_CATEGORY_MAP: Dict[str, str] = {
    "social_need:approach":   "social",
    "social_need:avoidance":  "rumination",
    "mastery_need:approach":  "planning",
    "mastery_need:avoidance": "self-evaluation",
    "rest_need:approach":     "fantasy",
    "rest_need:avoidance":    "rumination",
    "curiosity:approach":     "curiosity",
    "curiosity:avoidance":    "rumination",
}

_GUARDRAIL_LENGTH = 3  # max consecutive same-category thoughts before override


class ThoughtGenerator:
    """Produces one typed ThoughtFragment per fast tick, deterministically."""

    def select_category(
        self,
        affect: AffectState,
        drives: DriveState,
        active_desires: List[Dict[str, Any]],
        recent_categories: List[str],
    ) -> str:
        """Select a thought category based on current state.

        Priority order (from drive_system.md §7 and cognitive_loop.md §4):
        1. Active desires (mapped via _DESIRE_CATEGORY_MAP)
        2. Low valence → rumination / self-evaluation
        3. High arousal → planning
        4. High social_need → social
        5. Default → reflection
        """
        # 1. Desire-sourced category
        if active_desires:
            d = active_desires[0]
            drive = str(d.get("source_drive", ""))
            approach = "approach" if d.get("approach", True) else "avoidance"
            key = f"{drive}:{approach}"
            candidate = _DESIRE_CATEGORY_MAP.get(key)
            if candidate:
                return self._apply_guardrail(candidate, recent_categories)

        # 2. Affect-based rules
        if affect.valence < -0.3:
            candidate = "self-evaluation" if drives.mastery_need > 0.4 else "rumination"
            return self._apply_guardrail(candidate, recent_categories)

        if affect.arousal > 0.6:
            candidate = "curiosity" if drives.curiosity > drives.mastery_need else "planning"
            return self._apply_guardrail(candidate, recent_categories)

        # 3. Drive-based social pull
        if drives.social_need > 0.5:
            return self._apply_guardrail("social", recent_categories)

        # 4. Default
        return self._apply_guardrail("reflection", recent_categories)

    def _apply_guardrail(self, candidate: str, recent_categories: List[str]) -> str:
        """Override candidate if last _GUARDRAIL_LENGTH categories are identical."""
        if (
            len(recent_categories) >= _GUARDRAIL_LENGTH
            and all(c == candidate for c in recent_categories[-_GUARDRAIL_LENGTH:])
        ):
            # Pick the next category that differs
            for alt in CATEGORIES:
                if alt != candidate:
                    return alt
        return candidate

    def generate(
        self,
        state: AgentState,
        active_desires: List[Dict[str, Any]],
        tick_counter: int,
    ) -> Dict[str, Any]:
        """Generate one ThoughtFragment-compatible dict for the current tick."""
        category = self.select_category(
            state.affect,
            state.drives,
            active_desires,
            state.consecutive_thought_categories,
        )

        trigger = "internal"
        source_desire_drive = None
        if active_desires:
            first_desire = active_desires[0]
            drive = first_desire.get("source_drive", "")
            approach = "approach" if first_desire.get("approach", True) else "avoidance"
            if _DESIRE_CATEGORY_MAP.get(f"{drive}:{approach}") == category:
                trigger = "desire"
                source_desire_drive = drive

        template_idx = tick_counter % len(_TEMPLATES[category])
        text = _TEMPLATES[category][template_idx]

        now = datetime.now(timezone.utc).isoformat()
        thought_id = str(uuid.uuid4())

        return {
            "id": thought_id,
            "meta": {
                "id": thought_id,
                "created_at": now,
                "source_type": "synthetic",
                "source_ref": f"tick:{tick_counter}",
                "confidence": 1.0,
                "privacy_tier": "low",
                "mutability_class": "SELF",
                "lifecycle_state": "active",
            },
            "trigger": trigger,
            "source_desire_drive": source_desire_drive,
            "text": text,
            "intrusiveness": round(
                min(1.0, 0.3 + abs(state.affect.valence - 0.1) * 0.3), 4
            ),
            "thought_category": category,
        }
