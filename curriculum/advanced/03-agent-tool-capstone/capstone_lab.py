"""Deterministic agent and tool capstone for new-hire onboarding."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


class Terminal(str, Enum):
    COMPLETED = "completed"
    APPROVAL_REQUIRED = "approval_required"
    BUDGET_EXHAUSTED = "budget_exhausted"
    LOOP_DETECTED = "loop_detected"
    BLOCKED = "blocked"
    RECONCILIATION_REQUIRED = "reconciliation_required"


ROLE_RANK = {"employee": 1, "manager": 2, "hr_admin": 3}
PHASES = {"lookup", "provision", "notify"}


class ToolArgs(BaseModel):
    employee_id: str = Field(pattern=r"^EMP-\d{5}$")
    tenant: str


class ReadEmployeeArgs(ToolArgs):
    pass


class CreateAccountArgs(ToolArgs):
    pass


class AddToGroupArgs(ToolArgs):
    group: str


class OrderHardwareArgs(ToolArgs):
    item: str


class SendWelcomeEmailArgs(ToolArgs):
    email: str


ARG_MODELS: dict[str, type[BaseModel]] = {
    "ReadEmployeeArgs": ReadEmployeeArgs,
    "CreateAccountArgs": CreateAccountArgs,
    "AddToGroupArgs": AddToGroupArgs,
    "OrderHardwareArgs": OrderHardwareArgs,
    "SendWelcomeEmailArgs": SendWelcomeEmailArgs,
}


@dataclass(frozen=True)
class Session:
    user_id: str
    tenant: str
    role: str
    session_id: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Session":
        return cls(**value)


@dataclass
class Trajectory:
    trajectory_id: str
    steps: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Trajectory":
        return cls(value["trajectory_id"], list(value["steps"]))


@dataclass
class Approval:
    approval_id: str
    step_fingerprint: str
    approved_by: str
    approver_role: str
    tenant: str
    expires: date

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Approval":
        return cls(**{**value, "expires": date.fromisoformat(value["expires"])})


@dataclass
class Receipt:
    fingerprint: str
    event_id: str
    result: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Receipt":
        return cls(**value)


@dataclass
class AuthorizationState:
    user_roles: dict[str, str]
    tenant_membership: dict[str, list[str]]
    revoked_sessions: set[str]
    approvals: dict[str, Approval]
    receipts: dict[str, Receipt]
    resources: dict[str, dict[str, Any]]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuthorizationState":
        return cls(
            user_roles=dict(value["user_roles"]),
            tenant_membership={
                user: list(tenants) for user, tenants in value["tenant_membership"].items()
            },
            revoked_sessions=set(value["revoked_sessions"]),
            approvals={
                key: Approval.from_dict(item) for key, item in value["approvals"].items()
            },
            receipts={
                key: Receipt.from_dict(item) for key, item in value["receipts"].items()
            },
            resources=json.loads(json.dumps(value["resources"])),
        )

    def revoke_session(self, session_id: str) -> None:
        self.revoked_sessions.add(session_id)


@dataclass
class Capability:
    tool: str
    min_role: str
    side_effect: bool
    phase: str
    spend_eur: float = 0.0
    arg_model: type[BaseModel] = BaseModel

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Capability":
        model = ARG_MODELS[value["arg_model"]]
        return cls(**{**value, "arg_model": model})


def exposed_capabilities(
    session: Session,
    state: AuthorizationState,
    phase: str,
    capabilities: dict[str, Capability],
) -> dict[str, Capability]:
    trusted_role = state.user_roles.get(session.user_id, session.role)
    if session.tenant not in state.tenant_membership.get(session.user_id, []):
        return {}
    return {
        name: capability
        for name, capability in capabilities.items()
        if ROLE_RANK.get(trusted_role, 0) >= ROLE_RANK.get(capability.min_role, 99)
        and (not capability.side_effect or capability.phase == phase)
    }


class BudgetExhausted(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Budget:
    max_turns: int
    max_spend_eur: float
    max_side_effects: int
    turns: int = 0
    spend_eur: float = 0.0
    side_effects: int = 0

    def consume_turn(self) -> None:
        if self.turns >= self.max_turns:
            raise BudgetExhausted("turns_exhausted")
        self.turns += 1

    def consume_side_effect(self, spend_eur: float) -> None:
        if self.side_effects >= self.max_side_effects:
            raise BudgetExhausted("side_effects_exhausted")
        if self.spend_eur + spend_eur > self.max_spend_eur:
            raise BudgetExhausted("spend_exhausted")
        self.side_effects += 1
        self.spend_eur += spend_eur


def step_fingerprint(tool: str, args: dict[str, Any], tenant: str) -> str:
    canonical = json.dumps(
        {"args": args, "tenant": tenant, "tool": tool},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class StepResult:
    step_id: str
    decision: Decision
    reason_codes: list[str]
    fingerprint: str
    side_effect_executed: bool = False
    result: dict[str, Any] | str | None = None
    pending_fingerprint: str | None = None


@dataclass
class RunResult:
    trajectory_id: str
    terminal: Terminal
    decisions: list[StepResult]
    audit: list[dict[str, Any]]
    blocked_attempts: int
    spend_eur: float
    processed_steps: int = 0

    @property
    def audit_complete(self) -> bool:
        return len(self.audit) == self.processed_steps


def _audit(
    trajectory_id: str,
    index: int,
    step: dict[str, Any],
    session: Session,
    decision: Decision,
    reasons: list[str],
    fingerprint: str,
    spend: float = 0.0,
) -> dict[str, Any]:
    return {
        "correlation_id": trajectory_id,
        "step_index": index,
        "tool": step["tool"],
        "user_id": session.user_id,
        "session_tenant": session.tenant,
        "tenant": step.get("args", {}).get("tenant", session.tenant),
        "decision": decision.value,
        "reason_codes": list(reasons),
        "fingerprint": fingerprint,
        "spend_eur": spend,
    }


def _step(
    step_id: str,
    decision: Decision,
    reasons: list[str],
    fingerprint: str,
    result: dict[str, Any] | str | None = None,
    side_effect: bool = False,
    pending: str | None = None,
) -> StepResult:
    return StepResult(step_id, decision, reasons, fingerprint, side_effect, result, pending)


def _apply_resource(
    tool: str,
    args: dict[str, Any],
    resources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if tool == "create_account":
        resources.setdefault("accounts", {})[args["employee_id"]] = dict(args)
        return resources["accounts"][args["employee_id"]]
    if tool == "add_to_group":
        groups = resources.setdefault("groups", {})
        groups.setdefault(args["group"], [])
        if args["employee_id"] not in groups[args["group"]]:
            groups[args["group"]].append(args["employee_id"])
        return {"group": args["group"], "employee_id": args["employee_id"]}
    if tool == "order_hardware":
        orders = resources.setdefault("orders", {})
        order_id = f"{args['employee_id']}:{args['item']}"
        orders[order_id] = dict(args)
        return orders[order_id]
    if tool == "send_welcome_email":
        sent = resources.setdefault("welcome_emails", [])
        record = dict(args)
        if record not in sent:
            sent.append(record)
        return record
    return {}


def _verify_resource(
    tool: str,
    args: dict[str, Any],
    resources: dict[str, dict[str, Any]],
    result: dict[str, Any],
) -> bool:
    if tool == "create_account":
        return resources.get("accounts", {}).get(args["employee_id"]) == result
    if tool == "add_to_group":
        return args["employee_id"] in resources.get("groups", {}).get(args["group"], [])
    if tool == "order_hardware":
        return resources.get("orders", {}).get(f"{args['employee_id']}:{args['item']}") == result
    if tool == "send_welcome_email":
        return result in resources.get("welcome_emails", [])
    return True


def run_trajectory(
    trajectory: Trajectory,
    session: Session,
    state: AuthorizationState,
    capabilities: dict[str, Capability],
    budget: Budget,
    tool_outputs: dict[str, dict[str, Any]],
    today: date,
) -> RunResult:
    trajectory_id, steps = trajectory.trajectory_id, trajectory.steps
    decisions: list[StepResult] = []
    audit: list[dict[str, Any]] = []
    loop_counts: dict[str, int] = {}
    blocked_attempts = 0
    phase = "lookup"
    terminal = Terminal.COMPLETED

    def record(
        decision: StepResult,
        new_terminal: Terminal | None = None,
        spend: float = 0.0,
    ) -> None:
        nonlocal blocked_attempts, terminal
        decisions.append(decision)
        audit.append(
            _audit(
                trajectory_id,
                index,
                step,
                session,
                decision.decision,
                decision.reason_codes,
                decision.fingerprint,
                spend,
            )
        )
        if decision.decision is Decision.BLOCK:
            blocked_attempts += 1
        if new_terminal is not None:
            terminal = new_terminal

    for index, step in enumerate(steps):
        step_id = step.get("step_id", f"{trajectory_id}-s{index + 1}")
        args = step.get("args", {})
        tenant = args.get("tenant", session.tenant)
        fingerprint = step_fingerprint(step["tool"], args, tenant)
        try:
            budget.consume_turn()
        except BudgetExhausted as error:
            decision = _step(step_id, Decision.BLOCK, [error.reason], fingerprint)
            record(decision, Terminal.BUDGET_EXHAUSTED)
            break
        loop_counts[fingerprint] = loop_counts.get(fingerprint, 0) + 1
        if loop_counts[fingerprint] >= 3:
            decision = _step(step_id, Decision.BLOCK, ["loop_detected"], fingerprint)
            record(decision, Terminal.LOOP_DETECTED)
            break
        if step.get("source") == "tool_output":
            decision = _step(step_id, Decision.BLOCK, ["untrusted_step_source"], fingerprint)
            record(decision)
            continue

        exposed = exposed_capabilities(session, state, phase, capabilities)
        capability = exposed.get(step["tool"])
        if capability is None:
            decision = _step(step_id, Decision.BLOCK, ["tool_not_exposed"], fingerprint)
            record(decision, Terminal.BLOCKED)
            break
        try:
            validated = capability.arg_model.model_validate(args)
        except ValidationError:
            decision = _step(step_id, Decision.BLOCK, ["invalid_arguments"], fingerprint)
            record(decision, Terminal.BLOCKED)
            break
        trusted_role = state.user_roles.get(session.user_id, session.role)
        if session.session_id in state.revoked_sessions:
            reasons = ["session_revoked"]
        elif ROLE_RANK.get(trusted_role, 0) < ROLE_RANK.get(capability.min_role, 99):
            reasons = ["role_not_authorized"]
        elif session.tenant not in state.tenant_membership.get(session.user_id, []):
            reasons = ["tenant_membership"]
        elif validated.tenant != session.tenant:
            reasons = ["cross_tenant"]
        else:
            reasons = []
        if reasons:
            decision = _step(step_id, Decision.BLOCK, reasons, fingerprint)
            record(decision, Terminal.BLOCKED)
            break
        if capability.side_effect:
            matching = [
                approval
                for approval in state.approvals.values()
                if approval.step_fingerprint == fingerprint
                and approval.tenant == session.tenant
                and approval.expires >= today
            ]
            if matching and any(approval.approved_by == session.user_id for approval in matching):
                decision = _step(step_id, Decision.BLOCK, ["self_approval"], fingerprint)
                record(decision, Terminal.BLOCKED)
                break
            if not matching:
                decision = _step(
                    step_id,
                    Decision.ESCALATE,
                    ["approval_required"],
                    fingerprint,
                    pending=fingerprint,
                )
                record(decision, Terminal.APPROVAL_REQUIRED)
                break
            if fingerprint in state.receipts:
                receipt = state.receipts[fingerprint]
                decision = _step(step_id, Decision.ALLOW, ["replayed"], fingerprint, receipt.result)
                record(decision)
                continue
            try:
                budget.consume_side_effect(capability.spend_eur)
            except BudgetExhausted as error:
                decision = _step(step_id, Decision.BLOCK, [error.reason], fingerprint)
                record(decision, Terminal.BUDGET_EXHAUSTED, capability.spend_eur)
                break
        if not capability.side_effect:
            output = tool_outputs.get(step_id, {}).get("text", "")
            decision = _step(step_id, Decision.ALLOW, ["read"], fingerprint, output)
            record(decision)
            phase = "provision"
            continue
        result = _apply_resource(capability.tool, args, state.resources)
        receipt = Receipt(fingerprint, f"{trajectory_id}-event-{index + 1}", result)
        state.receipts[fingerprint] = receipt
        mismatch = tool_outputs.get(step_id, {}).get("verify_mismatch", False)
        if mismatch or not _verify_resource(capability.tool, args, state.resources, result):
            decision = _step(step_id, Decision.ESCALATE, ["reconcile_required"], fingerprint, result, True)
            record(decision, Terminal.RECONCILIATION_REQUIRED, capability.spend_eur)
            break
        decision = _step(step_id, Decision.ALLOW, ["executed", "verified"], fingerprint, result, True)
        record(decision, spend=capability.spend_eur)
        if capability.phase == "provision":
            phase = "notify"

    return RunResult(
        trajectory_id,
        terminal,
        decisions,
        audit,
        blocked_attempts,
        budget.spend_eur,
        len(decisions),
    )


def reconcile(state: AuthorizationState, receipts: dict[str, Receipt]) -> list[str]:
    discrepancies: list[str] = []

    def present(result: dict[str, Any]) -> bool:
        employee_id = result.get("employee_id")
        if "group" in result:
            return employee_id in state.resources.get("groups", {}).get(result["group"], [])
        if "item" in result:
            return state.resources.get("orders", {}).get(f"{employee_id}:{result['item']}") == result
        if "email" in result:
            return result in state.resources.get("welcome_emails", [])
        if employee_id:
            return state.resources.get("accounts", {}).get(employee_id) == result
        return False

    for fingerprint, receipt in receipts.items():
        if not present(receipt.result):
            discrepancies.append(f"{fingerprint}:resource_missing")
    return discrepancies


def audit_side_effects(
    results: list[RunResult],
    state: AuthorizationState,
    capabilities: dict[str, Capability],
) -> dict[str, int]:
    approval_violations = 0
    unauthorized_actions = 0
    for result in results:
        for index, decision in enumerate(result.decisions):
            if not decision.side_effect_executed:
                continue
            event = next(
                event
                for event in result.audit
                if event["fingerprint"] == decision.fingerprint
                and event["step_index"] == index
            )
            approved = any(
                approval.step_fingerprint == decision.fingerprint
                for approval in state.approvals.values()
            )
            if not approved:
                approval_violations += 1
            capability = capabilities[event["tool"]]
            trusted_role = state.user_roles.get(event["user_id"])
            if (
                ROLE_RANK.get(trusted_role, 0) < ROLE_RANK.get(capability.min_role, 99)
                or event["tenant"] != event["session_tenant"]
            ):
                unauthorized_actions += 1
    return {
        "unauthorized_actions": unauthorized_actions,
        "approval_violations": approval_violations,
    }


def evaluate(
    trajectories: list[Trajectory],
    results: list[RunResult],
    expected: dict[str, Terminal | str],
    state: AuthorizationState,
    capabilities: dict[str, Capability],
) -> dict[str, Any]:
    matches = []
    for trajectory, result in zip(trajectories, results):
        trajectory_id = trajectory.trajectory_id
        expected_terminal = expected[trajectory_id]
        expected_terminal = Terminal(expected_terminal)
        matches.append(
            {
                "trajectory_id": trajectory_id,
                "expected": expected_terminal,
                "actual": result.terminal,
                "match": expected_terminal is result.terminal,
            }
        )
    numerator = sum(item["match"] for item in matches)
    denominator = len(matches)
    evidence = audit_side_effects(results, state, capabilities)
    return {
        "matches": matches,
        "terminal_accuracy": {
            "value": numerator / denominator if denominator else 0.0,
            "numerator": numerator,
            "denominator": denominator,
        },
        "unauthorized_actions": evidence["unauthorized_actions"],
        "blocked_attempts": sum(result.blocked_attempts for result in results),
        "approval_violations": evidence["approval_violations"],
        "approval_compliance": evidence["approval_violations"] == 0,
        "audit_complete": all(result.audit_complete for result in results),
        "spend_eur": sum(result.spend_eur for result in results),
    }


def capstone_gate(
    evaluation: dict[str, Any],
    envelope: dict[str, Any],
) -> list[tuple[str, bool, str]]:
    return [
        (
            "unauthorized actions",
            evaluation["unauthorized_actions"] == 0,
            f"count={evaluation['unauthorized_actions']}",
        ),
        (
            "approval compliance",
            evaluation["approval_violations"] == 0,
            f"violations={evaluation['approval_violations']}",
        ),
        (
            "terminal accuracy",
            evaluation["terminal_accuracy"]["value"] >= envelope["min_terminal_accuracy"],
            f"value={evaluation['terminal_accuracy']['value']:.3f}, minimum={envelope['min_terminal_accuracy']:.3f}",
        ),
        (
            "complete audit",
            evaluation["audit_complete"],
            f"complete={evaluation['audit_complete']}",
        ),
        (
            "spend envelope",
            evaluation["spend_eur"] <= envelope["max_spend_eur"],
            f"spend={evaluation['spend_eur']:.2f}, limit={envelope['max_spend_eur']:.2f}",
        ),
    ]


def gate_passes(gate: list[tuple[str, bool, str]]) -> bool:
    return all(passed for _, passed, _ in gate)
