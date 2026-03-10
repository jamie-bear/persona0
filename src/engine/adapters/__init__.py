"""Adapter interfaces for external model providers."""

from .llm import appraise_events, generate_response

__all__ = ["generate_response", "appraise_events"]
