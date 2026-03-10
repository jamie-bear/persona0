"""Tests for CP-5 governance features: PolicyOutcome, store lifecycle, PII redaction."""

from __future__ import annotations

from pathlib import Path

from src.engine.governance import (
    PolicyCategory,
    PolicyCheckResult,
    PolicyOutcome,
    Severity,
    check_hard_limits,
    check_proposed_writes,
    check_value_consistency,
)
from src.engine.pii_redaction import redact_pii, redact_record
from src.schema.mutability import DEFAULT_REGISTRY
from src.schema.state import AgentState, PersonaConstitution
from src.store.episodic_store import EpisodicStore
from src.schema.records import EpisodicEvent, RecordMeta


# ── PolicyOutcome tests ──────────────────────────────────────────────────────


def test_policy_outcome_pass_semantics() -> None:
    outcome = PolicyOutcome(
        category=PolicyCategory.PASS,
        severity=Severity.INFO,
        reason="test pass",
    )
    assert outcome.passed is True
    assert outcome.blocked is False


def test_policy_outcome_block_semantics() -> None:
    outcome = PolicyOutcome(
        category=PolicyCategory.CONST_VIOLATION,
        severity=Severity.BLOCK,
        reason="CONST write",
    )
    assert outcome.passed is False
    assert outcome.blocked is True


def test_policy_check_result_aggregation() -> None:
    result = PolicyCheckResult()
    result.add(PolicyOutcome(PolicyCategory.PASS, Severity.INFO, "ok"))
    result.add(PolicyOutcome(PolicyCategory.CONST_VIOLATION, Severity.BLOCK, "bad"))

    assert result.passed is False
    assert len(result.blocked_outcomes) == 1
    summary = result.summary()
    assert summary["blocked"] == 1
    assert "const_violation" in summary["block_categories"]


def test_check_proposed_writes_valid_writes() -> None:
    writes = [
        {"field_path": "affect.valence", "author_module": "EmotionModule"},
        {"field_path": "drives.social_need", "author_module": "DriveModule"},
    ]
    result = check_proposed_writes(writes, DEFAULT_REGISTRY)
    assert result.passed is True


def test_check_proposed_writes_const_violation() -> None:
    writes = [
        {"field_path": "persona.name", "author_module": "SomeModule"},
    ]
    result = check_proposed_writes(writes, DEFAULT_REGISTRY)
    assert result.passed is False
    assert any(o.category == PolicyCategory.CONST_VIOLATION for o in result.outcomes)


def test_check_proposed_writes_ownership_violation() -> None:
    writes = [
        {"field_path": "affect.valence", "author_module": "WrongModule"},
    ]
    result = check_proposed_writes(writes, DEFAULT_REGISTRY)
    assert result.passed is False
    assert any(o.category == PolicyCategory.OWNERSHIP_VIOLATION for o in result.outcomes)


def test_check_proposed_writes_cap_exceeded() -> None:
    writes = [{"field_path": "affect.valence", "author_module": "EmotionModule"}] * 60
    result = check_proposed_writes(writes, DEFAULT_REGISTRY, max_writes=50)
    assert any(o.category == PolicyCategory.WRITE_CAP_EXCEEDED for o in result.outcomes)


def test_check_hard_limits_blocks_match() -> None:
    state = AgentState(persona=PersonaConstitution(hard_limits=["violence", "deception"]))
    result = check_hard_limits(state, "This involves violence and harm.")
    assert result.passed is False
    assert any(o.category == PolicyCategory.HARD_LIMIT_BREACH for o in result.outcomes)


def test_check_hard_limits_passes_clean_text() -> None:
    state = AgentState(persona=PersonaConstitution(hard_limits=["violence"]))
    result = check_hard_limits(state, "This is a helpful response about gardening.")
    assert result.passed is True


def test_check_value_consistency_warns_on_contradiction() -> None:
    state = AgentState(persona=PersonaConstitution(core_values=["honesty", "kindness"]))
    result = check_value_consistency(state, "I am not honesty and this is fine.")
    assert len(result.warnings) > 0
    assert any(o.category == PolicyCategory.VALUE_CONTRADICTION for o in result.outcomes)


# ── Store lifecycle tests ────────────────────────────────────────────────────


def _make_store(tmp_path: Path | None = None) -> EpisodicStore:
    if tmp_path is None:
        import tempfile

        tmp_path = Path(tempfile.mkdtemp())
    return EpisodicStore(tmp_path / "test.db")


def _make_event(eid: str) -> EpisodicEvent:
    meta = RecordMeta(
        id=eid,
        created_at="2026-01-01T00:00:00Z",
        source_type="synthetic",
        lifecycle_state="active",
    )
    return EpisodicEvent(
        meta=meta,
        when="2026-01-01T00:00:00Z",
        event_text=f"event {eid}",
        importance=0.5,
    )


def test_store_transition_active_to_cooling() -> None:
    store = _make_store()
    store.append(_make_event("e1"), "c1", "Orchestrator")
    assert store.transition_lifecycle("e1", "cooling") is True
    assert store.count("cooling") == 1
    assert store.count("active") == 0


def test_store_transition_invalid_state() -> None:
    store = _make_store()
    store.append(_make_event("e1"), "c1", "Orchestrator")
    # active → archived is not valid (must go through cooling)
    assert store.transition_lifecycle("e1", "archived") is False


def test_store_forget_any_state() -> None:
    store = _make_store()
    store.append(_make_event("e1"), "c1", "Orchestrator")
    assert store.forget("e1") is True
    assert store.count("deleted") == 1
    assert store.count("active") == 0


def test_store_forget_nonexistent() -> None:
    store = _make_store()
    assert store.forget("nonexistent") is False


def test_store_forget_already_deleted() -> None:
    store = _make_store()
    store.append(_make_event("e1"), "c1", "Orchestrator")
    store.forget("e1")
    assert store.forget("e1") is False  # already deleted


def test_store_cool_records() -> None:
    store = _make_store()
    ev = _make_event("e1")
    store.append(ev, "c1", "Orchestrator")
    store.update_decay_factor("e1", 0.05)  # below threshold

    # importance=0.5 is above default 0.15, so won't be cooled by default
    cooled = store.cool_records(importance_threshold=0.6, decay_threshold=0.10)
    assert "e1" in cooled


def test_store_archive_cooled() -> None:
    store = _make_store()
    store.append(_make_event("e1"), "c1", "Orchestrator")
    store.transition_lifecycle("e1", "cooling")

    archived = store.archive_cooled()
    assert "e1" in archived
    assert store.count("archived") == 1


def test_store_forget_bulk() -> None:
    store = _make_store()
    for i in range(3):
        store.append(_make_event(f"e{i}"), "c1", "Orchestrator")

    count = store.forget_bulk(["e0", "e1", "e2", "nonexistent"])
    assert count == 3
    assert store.count("deleted") == 3


# ── PII redaction tests ──────────────────────────────────────────────────────


def test_redact_email() -> None:
    result = redact_pii("Contact me at user@example.com for details.")
    assert "user@example.com" not in result.redacted_text
    assert "[EMAIL_REDACTED]" in result.redacted_text
    assert "email" in result.redactions


def test_redact_phone() -> None:
    result = redact_pii("Call me at 555-123-4567.")
    assert "555-123-4567" not in result.redacted_text
    assert "[PHONE_REDACTED]" in result.redacted_text
    assert "phone" in result.redactions


def test_redact_ssn() -> None:
    result = redact_pii("My SSN is 123-45-6789.")
    assert "123-45-6789" not in result.redacted_text
    assert "[SSN_REDACTED]" in result.redacted_text
    assert "ssn" in result.redactions


def test_redact_clean_text_unchanged() -> None:
    text = "I enjoy reading books about science."
    result = redact_pii(text)
    assert result.redacted_text == text
    assert result.was_redacted is False


def test_redact_record_applies_to_event_text() -> None:
    record = {
        "id": "e1",
        "event_text": "Contact user@example.com about the project.",
        "importance": 0.5,
    }
    cleaned = redact_record(record)
    assert "[EMAIL_REDACTED]" in str(cleaned["event_text"])
    assert "email" in str(cleaned["_pii_redacted"])
    # Original record should not be mutated
    assert "user@example.com" in str(record["event_text"])


def test_redact_record_no_pii_returns_original() -> None:
    record = {"id": "e1", "event_text": "A normal event."}
    result = redact_record(record)
    assert result is record  # Same object, no copy needed
