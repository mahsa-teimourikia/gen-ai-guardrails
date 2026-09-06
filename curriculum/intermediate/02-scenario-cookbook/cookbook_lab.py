"""Deterministic extraction, agent-write, and moderation cookbook recipes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


@dataclass
class GuardOutcome:
    decision: Decision
    reason_codes: list[str]


T = TypeVar("T")


class Extracted(BaseModel, Generic[T]):
    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    span: tuple[int, int]


class LineItem(BaseModel):
    description: Extracted[str]
    amount: Extracted[float]


class ExpenseClaimV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["expense-claim.v2"]
    employee_hash: str
    currency: Extracted[str]
    claim_date: Extracted[date]
    total: Extracted[float]
    line_items: list[LineItem]


def _extracted_fields(value: Any) -> list[Extracted[Any]]:
    if isinstance(value, Extracted):
        return [value]
    if isinstance(value, BaseModel):
        fields: list[Extracted[Any]] = []
        for nested in value.__dict__.values():
            fields.extend(_extracted_fields(nested))
        return fields
    if isinstance(value, list | tuple):
        fields = []
        for nested in value:
            fields.extend(_extracted_fields(nested))
        return fields
    return []


def min_confidence(claim: ExpenseClaimV2) -> float:
    fields = _extracted_fields(claim)
    return min(field.confidence for field in fields) if fields else 0.0


def check_invariants(
    claim: ExpenseClaimV2,
    today: date,
    currencies: tuple[str, ...] = ("EUR", "USD"),
) -> list[str]:
    issues: list[str] = []
    if not claim.line_items:
        issues.append("no_line_items")
    if abs(sum(item.amount.value for item in claim.line_items) - claim.total.value) > 0.005:
        issues.append("total_mismatch")
    if claim.currency.value not in currencies:
        issues.append("currency_not_allowed")
    if claim.claim_date.value > today:
        issues.append("date_in_future")
    return issues


def route_extraction(candidate: dict[str, Any], policy: dict[str, Any], today: date) -> GuardOutcome:
    try:
        claim = ExpenseClaimV2.model_validate(candidate)
    except ValidationError:
        return GuardOutcome(Decision.BLOCK, ["schema_invalid"])
    invariant_issues = check_invariants(claim, today)
    if invariant_issues:
        return GuardOutcome(
            Decision.ESCALATE,
            [f"invariant_failed:{issue}" for issue in invariant_issues],
        )
    if min_confidence(claim) < float(policy["min_field_confidence"]):
        return GuardOutcome(Decision.ESCALATE, ["low_confidence"])
    return GuardOutcome(Decision.ALLOW, ["persist"])


def identity_hash(identity: dict[str, Any]) -> str:
    return hashlib.sha256(str(identity.get("user_id", "")).encode("utf-8")).hexdigest()


@dataclass
class ProposedAction:
    action_id: str
    tool: str
    arguments: dict[str, Any]
    requester: dict[str, Any]
    approver: dict[str, Any] | None
    idempotency_key: str


_ROLE_RANK = {"employee": 0, "manager": 1, "hr_admin": 2}
_READ_TOOLS = {"read_ticket"}
_WRITE_TOOLS = {"create_ticket", "close_ticket", "issue_payroll_adjustment"}


def dry_run(action: ProposedAction, policy: dict[str, Any]) -> dict[str, Any]:
    rule = policy.get("allowlist", {}).get(action.tool, {})
    return {
        "tool": action.tool,
        "arguments": dict(action.arguments),
        "reversible": action.tool not in {"close_ticket", "issue_payroll_adjustment"},
        "requires_approval": bool(rule.get("approval_required", False)),
    }


def approve_gate(action: ProposedAction, policy: dict[str, Any]) -> GuardOutcome:
    if policy.get("kill_switch") and action.tool in _WRITE_TOOLS:
        return GuardOutcome(Decision.BLOCK, ["kill_switch"])
    rule = policy.get("allowlist", {}).get(action.tool)
    if rule is None:
        return GuardOutcome(Decision.BLOCK, ["tool_not_allowed"])
    requester_role = action.requester.get("role", "")
    if _ROLE_RANK.get(requester_role, -1) < _ROLE_RANK.get(rule.get("role", ""), 99):
        return GuardOutcome(Decision.BLOCK, ["role_not_authorized"])
    if rule.get("approval_required"):
        if action.approver is None:
            return GuardOutcome(Decision.ESCALATE, ["approval_required"])
        if action.approver.get("user_id") == action.requester.get("user_id"):
            return GuardOutcome(Decision.BLOCK, ["self_approval"])
        if _ROLE_RANK.get(action.approver.get("role", ""), -1) < _ROLE_RANK.get(rule.get("role", ""), 99):
            return GuardOutcome(Decision.BLOCK, ["approver_not_authorized"])
    return GuardOutcome(Decision.ALLOW, ["approved"])


class BudgetExceeded(RuntimeError):
    pass


class Executor:
    def __init__(self, budget_writes: int) -> None:
        self.budget_writes = budget_writes
        self.write_count = 0
        self._receipts: dict[str, dict[str, Any]] = {}

    def execute(self, action: ProposedAction) -> dict[str, Any]:
        if action.idempotency_key in self._receipts:
            return dict(self._receipts[action.idempotency_key])
        is_write = action.tool in _WRITE_TOOLS
        if is_write and self.write_count >= self.budget_writes:
            raise BudgetExceeded("max_writes_per_session")
        if is_write:
            self.write_count += 1
        receipt = {
            "action_id": action.action_id,
            "idempotency_key": action.idempotency_key,
            "tool": action.tool,
            "state": {"tool": action.tool, **action.arguments},
            "status": "completed",
        }
        self._receipts[action.idempotency_key] = receipt
        return dict(receipt)

    def verify(self, receipt: dict[str, Any], expected_state: dict[str, Any]) -> GuardOutcome:
        if receipt.get("state") == expected_state:
            return GuardOutcome(Decision.ALLOW, ["verified"])
        return GuardOutcome(Decision.ESCALATE, ["reconcile_required"])


def run_write_recipe(
    action: ProposedAction,
    policy: dict[str, Any],
    executor: Executor,
    expected_state: dict[str, Any],
) -> list[GuardOutcome]:
    outcomes = [approve_gate(action, policy)]
    if outcomes[-1].decision is not Decision.ALLOW:
        return outcomes
    try:
        receipt = executor.execute(action)
    except BudgetExceeded:
        outcomes.append(GuardOutcome(Decision.BLOCK, ["budget_exceeded"]))
        return outcomes
    outcomes.append(GuardOutcome(Decision.ALLOW, ["executed"]))
    outcomes.append(executor.verify(receipt, expected_state))
    return outcomes


def precheck(post: dict[str, Any], policy: dict[str, Any]) -> GuardOutcome:
    if len(post.get("text", "")) > policy["max_chars"]:
        return GuardOutcome(Decision.BLOCK, ["too_large"])
    if post.get("mime") not in policy["allowed_mime"]:
        return GuardOutcome(Decision.BLOCK, ["unsupported_type"])
    if not post.get("tenant_id"):
        return GuardOutcome(Decision.BLOCK, ["tenant_required"])
    if post.get("posts_in_window", 0) > policy["max_posts_in_window"]:
        return GuardOutcome(Decision.BLOCK, ["rate_limited"])
    return GuardOutcome(Decision.ALLOW, ["precheck_passed"])


def classify_outcome(
    scores: dict[str, float],
    thresholds: dict[str, dict[str, float]],
) -> GuardOutcome:
    candidates: list[tuple[int, str, Decision, str]] = []
    severity = (("block", 3, Decision.BLOCK), ("escalate", 2, Decision.ESCALATE), ("warn", 1, Decision.TRANSFORM))
    for category, score in scores.items():
        for level, rank, decision in severity:
            if score >= thresholds.get(category, {}).get(level, float("inf")):
                candidates.append((rank, category, decision, f"category:{level}"))
                break
    if not candidates:
        return GuardOutcome(Decision.ALLOW, [])
    _, category, decision, reason = max(candidates, key=lambda item: (item[0], item[1]))
    return GuardOutcome(decision, [reason, f"category_name:{category}"])


def moderate(post: dict[str, Any], policy: dict[str, Any]) -> GuardOutcome:
    checked = precheck(post, policy)
    if checked.decision is not Decision.ALLOW:
        return checked
    return classify_outcome(post.get("scores", {}), policy["thresholds"])


def evaluate_by_category(
    posts: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, dict[str, int]]:
    categories = tuple(policy["thresholds"])
    counts = {
        category: {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for category in categories
    }
    for post in posts:
        outcome = moderate(post, policy)
        driven = next(
            (reason.split(":", 1)[1] for reason in outcome.reason_codes if reason.startswith("category_name:")),
            None,
        )
        for category in categories:
            actual = category in post.get("labels", [])
            predicted = driven == category and outcome.decision is not Decision.ALLOW
            key = ("tp" if actual and predicted else "fn" if actual else "fp" if predicted else "tn")
            counts[category][key] += 1
    return counts


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
