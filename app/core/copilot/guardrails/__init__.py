"""Guardrails package for IPLMS AI Copilot."""
from app.core.copilot.guardrails.guardrail_manager import (
    GuardrailResult,
    guardrail_manager,
)

__all__ = ["guardrail_manager", "GuardrailResult"]
