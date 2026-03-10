"""Strict runtime configuration schema."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TickConfig(_StrictModel):
    fast_interval_seconds: float = Field(gt=0)
    slow_interval_seconds: float = Field(gt=0)
    macro_interval_seconds: float = Field(gt=0)


class DriveGrowth(_StrictModel):
    social_need: float
    mastery_need: float
    rest_need: float
    curiosity: float


class DriveThreshold(_StrictModel):
    social_need: float
    mastery_need: float
    rest_need: float
    curiosity: float


class SatisfactionRule(_StrictModel):
    satisfied_by: list[str]
    reduction_per_event: float


class DriveSatisfactionMap(_StrictModel):
    social_need: SatisfactionRule
    mastery_need: SatisfactionRule
    rest_need: SatisfactionRule
    curiosity: SatisfactionRule


class DrivesConfig(_StrictModel):
    growth_rate: DriveGrowth
    impulse_threshold: DriveThreshold
    satisfaction_map: DriveSatisfactionMap
    crystallization_threshold_ticks: int = Field(ge=1)
    crystallization_urgency_min: float
    max_proposals_per_drive_per_tick: int = Field(ge=1)
    persistence_threshold: float


class AffectState(_StrictModel):
    valence: float
    arousal: float
    stress: float
    energy: float


class AffectBounds(_StrictModel):
    min: float
    max: float


class AffectCircadian(_StrictModel):
    energy_peak_hour: int = Field(ge=0, le=23)
    energy_trough_hour: int = Field(ge=0, le=23)
    energy_modulation_amplitude: float


class AffectConfig(_StrictModel):
    baseline: AffectState
    decay_rate: AffectState
    bounds: AffectBounds
    circadian: AffectCircadian
    stress_high_threshold: float
    stress_rest_need_boost: float


class GoalsConfig(_StrictModel):
    frustration_threshold_suspension: float
    frustration_growth_per_stalled_tick: float
    frustration_decay_per_progressing_tick: float
    crystallization_priority_dampen: float
    max_active_goals: int = Field(ge=1)
    goal_staleness_days: int = Field(ge=1)


class ReflectionConfig(_StrictModel):
    max_confidence_delta_per_cycle: float
    high_confidence_threshold: float
    high_confidence_min_reflections: int = Field(ge=1)
    max_new_statements_per_cycle: int = Field(ge=1)
    confidence_decay_rate_per_cycle: float
    confidence_decay_threshold_days: int = Field(ge=1)
    confidence_archival_threshold: float


class RetrievalConfig(_StrictModel):
    recency_weight: float
    importance_weight: float
    semantic_similarity_weight: float
    self_relevance_weight: float
    goal_relevance_weight: float | None = None
    candidate_limit: int = Field(ge=1)
    salience_buffer_capacity: int = Field(ge=1)
    min_importance_threshold: float


class MemoryConfig(_StrictModel):
    decay_rate_per_cycle: float
    decay_cooling_threshold: float
    importance_cooling_threshold: float
    importance_cooling_cycles: int = Field(ge=1)
    max_records_cooled_per_cycle: int = Field(ge=1)
    max_records_archived_per_cycle: int = Field(ge=1)
    max_episodes_generated_per_day: int = Field(ge=1)
    max_consecutive_same_category_thoughts: int = Field(ge=1)


class GovernanceConfig(_StrictModel):
    enforcement_mode: Literal["strict", "audit"]
    const_write_hard_fail: bool
    audit_log_retention_days: int = Field(ge=1)
    max_writes_per_transaction: int = Field(ge=1)


class ObservabilityConfig(_StrictModel):
    cycle_log_format: Literal["jsonl", "sqlite"]
    cycle_log_max_size_mb: int = Field(ge=1)
    cycle_log_rotation: Literal["daily"]
    emit_full_state_snapshot: bool


class LLMAdapterConfig(_StrictModel):
    enabled: bool
    provider: str
    model: str
    timeout_seconds: float = Field(gt=0)
    retries: int = Field(ge=0)
    deterministic_mode: bool


class RuntimeConfig(_StrictModel):
    tick: TickConfig
    drives: DrivesConfig
    affect: AffectConfig
    goals: GoalsConfig
    reflection: ReflectionConfig
    retrieval: RetrievalConfig
    memory: MemoryConfig
    governance: GovernanceConfig
    observability: ObservabilityConfig
    llm_adapter: LLMAdapterConfig
