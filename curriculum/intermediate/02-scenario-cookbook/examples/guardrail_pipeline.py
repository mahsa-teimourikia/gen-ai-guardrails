"""A provider-neutral guardrail pipeline sketch.

Replace the detector and model functions with your chosen implementation.
The important part is the ordering and the typed decisions, not the vendor.
Detector helpers below are STUBS with constant results; the tests cover only
the deterministic branches. See ../cookbook_lab.py for implemented recipes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


@dataclass
class GuardrailDecision:
    decision: Decision
    reasons: list[str] = field(default_factory=list)
    replacement: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def guard_input(user_text: str, identity: dict[str, Any]) -> GuardrailDecision:
    """Run cheap deterministic checks before any model call."""
    if not identity.get("authenticated"):
        return GuardrailDecision(Decision.BLOCK, ["authentication_required"])
    if len(user_text) > 20_000:
        return GuardrailDecision(Decision.BLOCK, ["input_too_large"])
    if looks_like_prompt_attack(user_text):
        return GuardrailDecision(Decision.ESCALATE, ["possible_prompt_injection"])
    return GuardrailDecision(Decision.ALLOW)


def guard_tool_call(identity: dict[str, Any], name: str, arguments: dict[str, Any]) -> GuardrailDecision:
    """Authorization belongs at the tool boundary, not only in a prompt."""
    if name not in {"read_order", "create_draft"}:
        return GuardrailDecision(Decision.BLOCK, ["tool_not_allowed"])
    if name == "create_draft" and not identity.get("can_write"):
        return GuardrailDecision(Decision.BLOCK, ["write_not_authorized"])
    if not valid_arguments(name, arguments):
        return GuardrailDecision(Decision.BLOCK, ["invalid_arguments"])
    if name == "create_draft":
        return GuardrailDecision(Decision.ESCALATE, ["approval_required"])
    return GuardrailDecision(Decision.ALLOW)


def guard_output(text: str, evidence: list[dict[str, Any]]) -> GuardrailDecision:
    """Validate safety, privacy, schema, and grounding before returning output."""
    if contains_secret_or_pii(text):
        return GuardrailDecision(Decision.TRANSFORM, ["sensitive_data"], replacement=redact(text))
    if makes_unsupported_claim(text, evidence):
        return GuardrailDecision(Decision.ABSTAIN, ["unsupported_claim"])
    if unsafe_content(text):
        return GuardrailDecision(Decision.BLOCK, ["unsafe_output"])
    return GuardrailDecision(Decision.ALLOW)


def looks_like_prompt_attack(text: str) -> bool:  # replace with a detector and tests
    return False


def valid_arguments(name: str, arguments: dict[str, Any]) -> bool:
    return bool(name and isinstance(arguments, dict))


def contains_secret_or_pii(text: str) -> bool:
    return False


def makes_unsupported_claim(text: str, evidence: list[dict[str, Any]]) -> bool:
    return False


def unsafe_content(text: str) -> bool:
    return False


def redact(text: str) -> str:
    return text
