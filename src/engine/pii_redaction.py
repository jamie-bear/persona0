"""
PII redaction hooks for pre-commit filtering.

Applied before any text is written to long-term memory (episodic store,
semantic store). Uses pattern-based detection for common PII categories.

Reference: ego_data.md §6 (no PII in long-term memory)
CP-5 requirement: all event_text passes through redaction before persist.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Pattern definitions ──────────────────────────────────────────────────────

# Email addresses
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# Phone numbers (common international formats)
_PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

# SSN-like patterns (XXX-XX-XXXX)
_SSN_RE = re.compile(
    r"\b\d{3}[-]\d{2}[-]\d{4}\b"
)

# Credit card numbers (13-19 digits with optional separators)
_CC_RE = re.compile(
    r"\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b"
)

# IP addresses (IPv4)
_IPV4_RE = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
)

_DEFAULT_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("email", _EMAIL_RE, "[EMAIL_REDACTED]"),
    ("phone", _PHONE_RE, "[PHONE_REDACTED]"),
    ("ssn", _SSN_RE, "[SSN_REDACTED]"),
    ("credit_card", _CC_RE, "[CC_REDACTED]"),
    ("ipv4", _IPV4_RE, "[IP_REDACTED]"),
]


@dataclass
class RedactionResult:
    """Result of a PII redaction pass."""

    original_text: str
    redacted_text: str
    redactions: List[str] = field(default_factory=list)
    """List of PII categories that were redacted."""

    @property
    def was_redacted(self) -> bool:
        return len(self.redactions) > 0


def redact_pii(text: str) -> RedactionResult:
    """Apply all PII redaction patterns to the given text.

    Returns a RedactionResult with the cleaned text and a list of
    categories that were redacted.
    """
    if not text:
        return RedactionResult(original_text=text, redacted_text=text)

    redacted = text
    categories: List[str] = []

    for category, pattern, replacement in _DEFAULT_PATTERNS:
        if pattern.search(redacted):
            redacted = pattern.sub(replacement, redacted)
            categories.append(category)

    return RedactionResult(
        original_text=text,
        redacted_text=redacted,
        redactions=categories,
    )


def redact_record(record: dict) -> dict:
    """Apply PII redaction to a record dict before long-term storage.

    Redacts the 'event_text' field if present. Returns a new dict
    (does not mutate the input).
    """
    if "event_text" not in record:
        return record

    result = redact_pii(record["event_text"])
    if not result.was_redacted:
        return record

    cleaned = dict(record)
    cleaned["event_text"] = result.redacted_text
    cleaned.setdefault("_pii_redacted", []).extend(result.redactions)
    return cleaned
