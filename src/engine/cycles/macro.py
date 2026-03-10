"""
Macro (nightly reflection) cycle step implementations.

This module intentionally stays deterministic and non-LLM-driven so CP-4 can
be validated with stable fixtures.

Reference: cognitive_loop.md §4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ...schema.state import AgentState, SelfBelief
from ._store_helpers import attach_embedding_metadata
from ..modules._config import load_memory_config, load_reflection_config


def select_high_signal_episodes(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """1. Select high-signal episodes from the prior window.

    Sources are checked in priority order:
    - event['_macro_source_episodes'] (explicit fixture/testing injection)
    - event['_pending_episodic'] (in-flight episodic records)
    - event['_store'].query(...) when a store is injected

    A recency window (event['_macro_recency_window_hours'], default 72) filters
    out episodes older than the window when a reference timestamp is available.
    """
    episodes = _load_candidate_episodes(event)
    top_k = int(event.get("_macro_top_k", 12))
    recency_hours = float(event.get("_macro_recency_window_hours", 72))

    # Apply recency window filter
    episodes = _filter_by_recency(episodes, recency_hours)

    scored = []
    for record in episodes:
        score = _episode_signal_score(record)
        scored.append((score, record))

    scored.sort(
        key=lambda item: (
            -item[0],
            str(item[1].get("created_at", "")),
            str(_episode_id(item[1])),
        )
    )
    selected = [record for _, record in scored[:top_k]]
    event["_macro_selected_episodes"] = selected


def cluster_episodes(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """2. Cluster selected episodes by deterministic topic key."""
    selected = list(event.get("_macro_selected_episodes", []))
    buckets: Dict[str, List[Dict[str, Any]]] = {}

    for record in selected:
        key = _cluster_key(record)
        buckets.setdefault(key, []).append(record)

    clusters = []
    for idx, key in enumerate(sorted(buckets.keys()), start=1):
        episodes = sorted(
            buckets[key],
            key=lambda r: (str(r.get("created_at", "")), str(_episode_id(r))),
        )
        clusters.append(
            {
                "cluster_id": f"cluster-{idx:03d}",
                "topic_key": key,
                "episodes": episodes,
                "episode_ids": [_episode_id(r) for r in episodes],
            }
        )

    event["_macro_clusters"] = clusters


def produce_candidate_reflections(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """3. Produce deterministic candidate reflections per cluster."""
    clusters = list(event.get("_macro_clusters", []))
    tick = state.tick_counter
    reflections = []

    for idx, cluster in enumerate(clusters, start=1):
        count = len(cluster.get("episodes", []))
        if count == 0:
            continue

        topic = cluster.get("topic_key", "general")
        delta = min(0.15, round(0.05 + (count - 1) * 0.02, 4))
        reflections.append(
            {
                "reflection_id": f"refl-{tick:06d}-{idx:03d}",
                "source_episode_ids": list(cluster.get("episode_ids", [])),
                "pattern_statement": f"Pattern observed around '{topic}' across {count} episode(s).",
                "confidence_delta": delta,
                "proposed_self_belief_update": f"I repeatedly engage with {topic}.",
            }
        )

    event["_macro_candidate_reflections"] = reflections


def score_evidence_sufficiency(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """4. Score evidence sufficiency for each candidate reflection."""
    selected = {str(_episode_id(r)): r for r in event.get("_macro_selected_episodes", [])}
    scored = []

    for reflection in event.get("_macro_candidate_reflections", []):
        episodes = [selected.get(eid, {}) for eid in reflection.get("source_episode_ids", [])]
        episodes = [e for e in episodes if e]
        count = len(episodes)
        avg_importance = (
            sum(float(e.get("importance", 0.0)) for e in episodes) / count if count else 0.0
        )
        unique_days = {
            str(e.get("created_at", ""))[:10] for e in episodes if str(e.get("created_at", ""))
        }
        day_coverage = min(1.0, len(unique_days) / 2.0)

        score = min(1.0, round((count / 3.0) * 0.5 + avg_importance * 0.3 + day_coverage * 0.2, 4))
        scored.append({**reflection, "evidence_score": score})

    event["_macro_scored_reflections"] = scored


def update_self_beliefs(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """5. Update self-beliefs with confidence deltas from sufficient evidence.

    Max Δ confidence: +0.15 per cycle.
    Requires ≥2 independent reflections before confidence > 0.75.
    """
    threshold = float(event.get("_macro_evidence_threshold", 0.55))
    accepted = [
        r
        for r in event.get("_macro_scored_reflections", [])
        if float(r.get("evidence_score", 0.0)) >= threshold
    ]
    if not accepted:
        event["_macro_accepted_reflections"] = []
        return

    reflection_cfg = load_reflection_config()
    max_new = int(reflection_cfg.get("max_new_statements_per_cycle", 3))

    beliefs_by_statement = {b.statement: b for b in state.self_model.beliefs}
    changed = False
    new_statements_created = 0

    for reflection in accepted:
        statement = str(reflection.get("proposed_self_belief_update", "")).strip()
        if not _belief_statement_safe(statement, state):
            continue

        reflection_id = str(reflection.get("reflection_id", ""))
        delta = min(0.15, max(0.0, float(reflection.get("confidence_delta", 0.0))))

        belief = beliefs_by_statement.get(statement)
        if belief is None:
            if new_statements_created >= max_new:
                continue
            belief = SelfBelief(
                id=f"macro-belief-{len(state.self_model.beliefs) + 1:03d}",
                statement=statement,
                confidence=0.55,
                source_type="REFLECTION",
            )
            state.self_model.beliefs.append(belief)
            beliefs_by_statement[statement] = belief
            new_statements_created += 1
            changed = True

        if reflection_id and reflection_id not in belief.supporting_reflections:
            belief.supporting_reflections.append(reflection_id)
            changed = True

        new_confidence = min(1.0, round(belief.confidence + delta, 4))
        if new_confidence > 0.75 and len(set(belief.supporting_reflections)) < 2:
            new_confidence = 0.75

        if new_confidence != belief.confidence:
            belief.confidence = new_confidence
            changed = True

    event["_macro_accepted_reflections"] = accepted
    if changed:
        pending_writes.append(
            {"field_path": "self_model.beliefs", "author_module": "ReflectionEngine"}
        )


def decay_unreinforced_beliefs(
    state: AgentState, event: Dict[str, Any], pending_writes: List
) -> None:
    """5b. Decay confidence of beliefs not reinforced within the configured window.

    Reference: config/defaults.yaml reflection.confidence_decay_rate_per_cycle,
    reflection.confidence_decay_threshold_days, reflection.confidence_archival_threshold
    """
    cfg = load_reflection_config()
    decay_rate = float(cfg.get("confidence_decay_rate_per_cycle", 0.02))
    threshold_days = int(cfg.get("confidence_decay_threshold_days", 14))
    archival_threshold = float(cfg.get("confidence_archival_threshold", 0.15))

    # Build set of statements that were just reinforced this cycle
    reinforced_statements: set = set()
    for r in event.get("_macro_accepted_reflections", []):
        stmt = str(r.get("proposed_self_belief_update", "")).strip()
        if stmt:
            reinforced_statements.add(stmt)

    # Simulated "now" from tick_counter: each macro cycle ≈ 1 day
    current_day = state.tick_counter

    changed = False
    for belief in state.self_model.beliefs:
        # CONST_SEED beliefs don't decay
        if belief.source_type == "CONST_SEED":
            continue
        # Beliefs reinforced this cycle don't decay
        if belief.statement in reinforced_statements:
            continue

        last_ref_day = _last_reinforcement_day(belief, current_day)
        days_unreinforced = current_day - last_ref_day

        if days_unreinforced < threshold_days:
            continue

        new_confidence = max(0.0, round(belief.confidence - decay_rate, 4))
        if new_confidence != belief.confidence:
            belief.confidence = new_confidence
            changed = True

    # Track beliefs below archival threshold for observability
    archival_candidates = [
        b.id
        for b in state.self_model.beliefs
        if b.source_type != "CONST_SEED" and b.confidence < archival_threshold
    ]
    event["_macro_archival_candidates"] = archival_candidates

    if changed:
        pending_writes.append(
            {"field_path": "self_model.beliefs", "author_module": "ReflectionEngine"}
        )


def _last_reinforcement_day(belief: SelfBelief, current_day: int) -> int:
    """Estimate the last reinforcement day from supporting_reflections.

    Reflection IDs follow the pattern 'refl-TTTTTT-NNN' where TTTTTT is the
    tick_counter at creation time. Falls back to 0 if no reflections exist.
    """
    latest = 0
    for ref_id in belief.supporting_reflections:
        parts = str(ref_id).split("-")
        if len(parts) >= 2:
            try:
                tick = int(parts[1])
                if tick > latest:
                    latest = tick
            except (ValueError, IndexError):
                pass
    return latest


def archive_reflection(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """6. Archive accepted reflections and produce an audit-friendly payload."""
    accepted = list(event.get("_macro_accepted_reflections", []))
    if not accepted:
        event["_pending_reflections"] = []
        return

    now = datetime.now(timezone.utc).isoformat()
    archived = []
    for item in accepted:
        reflection_record = {
            "id": item.get("reflection_id"),
            "created_at": now,
            "source_episode_ids": list(item.get("source_episode_ids", [])),
            "pattern_statement": item.get("pattern_statement", ""),
            "confidence_delta": item.get("confidence_delta", 0.0),
            "evidence_score": item.get("evidence_score", 0.0),
        }
        attach_embedding_metadata(
            reflection_record,
            reflection_record.get("pattern_statement", ""),
            content_type="semantic_reflection",
        )
        archived.append(reflection_record)

    event["_pending_reflections"] = archived
    pending_writes.append({"field_path": "semantic_store", "author_module": "ReflectionEngine"})


def memory_compaction(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """6b. Memory compaction — cool and archive low-signal episodic records.

    Calls cool_records() and archive_cooled() on the injected EpisodicStore.
    Reference: config/defaults.yaml memory.* parameters
    """
    store = event.get("_store")
    if store is None or not hasattr(store, "cool_records"):
        event["_macro_compaction"] = {"cooled": 0, "archived": 0, "skipped": True}
        return

    from ..modules._config import load_memory_config

    mem_cfg = load_memory_config()

    importance_threshold = float(mem_cfg.get("importance_cooling_threshold", 0.15))
    decay_threshold = float(mem_cfg.get("decay_cooling_threshold", 0.10))
    max_cooled = int(mem_cfg.get("max_records_cooled_per_cycle", 100))
    max_archived = int(mem_cfg.get("max_records_archived_per_cycle", 50))

    cooled = store.cool_records(
        max_records=max_cooled,
        importance_threshold=importance_threshold,
        decay_threshold=decay_threshold,
    )
    archived = store.archive_cooled(max_records=max_archived)

    event["_macro_compaction"] = {
        "cooled": len(cooled),
        "archived": len(archived),
        "cooled_ids": cooled,
        "archived_ids": archived,
    }


def goal_review(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """7. Goal review — staleness check, frustration archival, observability summary.

    Reference: config/defaults.yaml goals.goal_staleness_days
    """
    from ..modules._config import load_goals_config

    goals_cfg = load_goals_config()
    staleness_days = int(goals_cfg.get("goal_staleness_days", 30))
    changed = False

    stale_ids = []
    abandoned_ids = []

    for goal in state.goals:
        if goal.status != "active":
            continue

        # Staleness check: goals created more than staleness_days ticks ago
        # with no progress are candidates for abandonment
        if goal.created_at:
            try:
                created = datetime.fromisoformat(goal.created_at.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created).days
                if age_days >= staleness_days and goal.progress < 0.05:
                    goal.status = "abandoned"
                    abandoned_ids.append(goal.id)
                    changed = True
                    continue
            except (ValueError, TypeError):
                pass

        # High-frustration goals that hit suspension threshold are suspended
        if goal.frustration >= 0.75 and goal.status == "active":
            goal.status = "suspended"
            stale_ids.append(goal.id)
            changed = True

    event["_macro_goal_review"] = {
        "active_goal_count": len([g for g in state.goals if g.status == "active"]),
        "accepted_reflection_count": len(event.get("_macro_accepted_reflections", [])),
        "abandoned_goal_ids": abandoned_ids,
        "suspended_goal_ids": stale_ids,
    }

    if changed:
        pending_writes.append({"field_path": "goals", "author_module": "GoalSystem"})


def drive_review(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """8. Drive review — log unmet high-pressure drives and clear nightly ephemeral state.

    Also clears persisted_desires and consecutive_thought_categories as
    documented in the AgentState schema (both are specified as cleared at
    the nightly macro cycle).
    """
    drives = state.drives.model_dump()
    unmet = [
        {"drive": name, "value": round(float(value), 4)}
        for name, value in sorted(drives.items())
        if float(value) >= float(event.get("_macro_unmet_drive_threshold", 0.70))
    ]
    event["_macro_unmet_drives"] = unmet

    # Clear nightly ephemeral fields (AgentState docstrings: "Cleared at nightly macro cycle")
    if state.persisted_desires:
        state.persisted_desires = []
        pending_writes.append({"field_path": "persisted_desires", "author_module": "DriveModule"})
    if state.consecutive_thought_categories:
        state.consecutive_thought_categories = []
        pending_writes.append(
            {"field_path": "consecutive_thought_categories", "author_module": "ThoughtGenerator"}
        )


def compact_episodic_memory(state: AgentState, event: Dict[str, Any], pending_writes: List) -> None:
    """9. Compact episodic store lifecycle state (active→cooling→archived).

    This step is best-effort and no-op when no ``_store`` is injected.
    It records an observability payload in ``event['_macro_memory_compaction']``.
    """
    store = event.get("_store")
    if store is None:
        event["_macro_memory_compaction"] = {
            "enabled": False,
            "cooled_ids": [],
            "archived_ids": [],
        }
        return

    cfg = load_memory_config()
    cooled = store.cool_records(
        max_records=int(cfg.get("max_records_cooled_per_cycle", 100)),
        importance_threshold=float(cfg.get("importance_cooling_threshold", 0.15)),
        decay_threshold=float(cfg.get("decay_cooling_threshold", 0.10)),
    )
    archived = store.archive_cooled(max_records=int(cfg.get("max_records_archived_per_cycle", 50)))

    event["_macro_memory_compaction"] = {
        "enabled": True,
        "cooled_ids": cooled,
        "archived_ids": archived,
        "cooled_count": len(cooled),
        "archived_count": len(archived),
    }


def _load_candidate_episodes(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "_macro_source_episodes" in event:
        return list(event.get("_macro_source_episodes", []))

    pending = list(event.get("_pending_episodic", []))
    if pending:
        return pending

    store = event.get("_store")
    if store is not None and hasattr(store, "query"):
        try:
            return list(store.query(limit=int(event.get("_macro_store_limit", 100))))
        except Exception:
            return []

    return []


def _filter_by_recency(episodes: List[Dict[str, Any]], window_hours: float) -> List[Dict[str, Any]]:
    """Filter episodes to those within the recency window.

    Uses the latest created_at among all episodes as the reference point.
    Episodes without a parseable created_at are kept (fail-open).
    """
    if not episodes or window_hours <= 0:
        return episodes

    # Find the latest timestamp as reference
    latest_ts = ""
    for ep in episodes:
        ts = str(ep.get("created_at", ""))
        if ts > latest_ts:
            latest_ts = ts

    if not latest_ts:
        return episodes

    try:
        ref = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return episodes

    from datetime import timedelta

    cutoff = ref - timedelta(hours=window_hours)
    cutoff_iso = cutoff.isoformat()

    filtered = []
    for ep in episodes:
        ts = str(ep.get("created_at", ""))
        if not ts or ts >= cutoff_iso:
            filtered.append(ep)

    return filtered


def _episode_signal_score(record: Dict[str, Any]) -> float:
    importance = float(record.get("importance", 0.0))
    affect = record.get("affect_snapshot") or {}
    emotional = max(abs(float(affect.get("valence", 0.0))), abs(float(affect.get("stress", 0.0))))
    goal_weight = 1.0 if record.get("goal_links") else 0.0
    return round(importance * 0.6 + emotional * 0.3 + goal_weight * 0.1, 4)


def _cluster_key(record: Dict[str, Any]) -> str:
    goal_links = record.get("goal_links") or []
    if goal_links:
        return f"goal:{goal_links[0]}"

    context = record.get("context") or {}
    location = str(context.get("location", "")).strip()
    if location:
        return f"location:{location.lower()}"

    record_type = str(record.get("record_type", "")).strip()
    if record_type:
        return f"type:{record_type.lower()}"

    text = str(record.get("event_text", "")).strip().lower()
    if text:
        return f"text:{text.split()[0]}"

    return "general"


def _episode_id(record: Dict[str, Any]) -> str:
    meta = record.get("meta") or {}
    return str(record.get("id") or meta.get("id") or "")


def _belief_statement_safe(statement: str, state: AgentState) -> bool:
    if not statement:
        return False

    lowered = statement.lower()
    for value in state.persona.core_values:
        value_l = value.lower().strip()
        if value_l and f"not {value_l}" in lowered:
            return False
    return True
