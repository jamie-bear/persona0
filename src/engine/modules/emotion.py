"""
EmotionModule — deterministic EMA-based affect updates.

Reference: cognitive_loop.md §3.1 step 3 (UPDATE_EMOTION)
           architecture.md §2 (Emotional Regulation module)
           config/defaults.yaml [affect.*]
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from ...schema.state import AffectState
from ._config import load_affect_config, load_tick_config


class EmotionModule:
    """Applies EMA decay, circadian modulation, and appraisal-driven affect deltas."""

    def update(
        self,
        affect: AffectState,
        appraisal_results: List[Dict[str, Any]],
        tick_counter: int,
        config: Dict[str, Any] | None = None,
    ) -> AffectState:
        """Return a new AffectState after one fast-tick update.

        Steps (per spec):
        1. EMA decay toward baseline for each variable
        2. Circadian energy modulation (cosine wave)
        3. Appraisal-driven deltas (goal-congruence → valence, threat → stress)
        4. Clamp all values to [-1.0, 1.0]

        Args:
            affect: current affect state
            appraisal_results: list of appraisal dicts from APPRAISE step; may be empty
            tick_counter: monotonic tick index (used for circadian phase)
            config: override config dict (defaults loaded from YAML if None)
        """
        cfg = config if config is not None else load_affect_config()
        tick_cfg = load_tick_config()

        baseline: Dict[str, float] = cfg.get("baseline", {})
        decay: Dict[str, float] = cfg.get("decay_rate", {})
        bounds: Dict[str, float] = cfg.get("bounds", {"min": -1.0, "max": 1.0})
        circ: Dict[str, Any] = cfg.get("circadian", {})
        lo, hi = float(bounds.get("min", -1.0)), float(bounds.get("max", 1.0))

        # -- 1. EMA decay toward baseline --
        valence = _ema(affect.valence, baseline.get("valence", 0.10), decay.get("valence", 0.05))
        arousal = _ema(affect.arousal, baseline.get("arousal", 0.30), decay.get("arousal", 0.08))
        stress  = _ema(affect.stress,  baseline.get("stress",  0.10), decay.get("stress",  0.06))
        energy  = _ema(affect.energy,  baseline.get("energy",  0.70), decay.get("energy",  0.04))

        # -- 2. Circadian energy modulation --
        fast_interval_s = float(tick_cfg.get("fast_interval_seconds", 1800))
        ticks_per_day = max(1, round(86400 / fast_interval_s))
        amplitude = float(circ.get("energy_modulation_amplitude", 0.15))
        peak_tick = int(circ.get("energy_peak_hour", 10)) * round(ticks_per_day / 24)
        phase = 2 * math.pi * ((tick_counter % ticks_per_day) - peak_tick) / ticks_per_day
        energy += amplitude * math.cos(phase)

        # -- 3. Appraisal-driven deltas --
        for appraisal in appraisal_results:
            goal_congruence = float(appraisal.get("goal_congruence", 0.0))
            threat          = float(appraisal.get("threat", 0.0))
            arousal_cue     = float(appraisal.get("arousal_cue", 0.0))
            valence += goal_congruence * 0.10
            stress  += threat * 0.10
            arousal += arousal_cue * 0.05

        # -- 4. Clamp --
        return AffectState(
            valence=_clamp(valence, lo, hi),
            arousal=_clamp(arousal, lo, hi),
            stress=_clamp(stress, lo, hi),
            energy=_clamp(energy, lo, hi),
        )

    def stress_rest_boost(
        self,
        stress: float,
        config: Dict[str, Any] | None = None,
    ) -> float:
        """Return additional rest_need growth when stress is high.

        Called by DriveModule after UPDATE_EMOTION to implement the cross-coupling
        between high stress and elevated rest need (cognitive_loop.md §7 failure modes).
        """
        cfg = config if config is not None else load_affect_config()
        threshold = float(cfg.get("stress_high_threshold", 0.70))
        boost = float(cfg.get("stress_rest_need_boost", 0.01))
        return boost if stress > threshold else 0.0


# ── helpers ──────────────────────────────────────────────────────────────────

def _ema(value: float, baseline: float, rate: float) -> float:
    """Pull value toward baseline by rate (EMA step)."""
    return value + (baseline - value) * rate


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
