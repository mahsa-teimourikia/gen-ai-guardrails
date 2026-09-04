"""Deterministic, provider-neutral best-practices release lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Literal


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


@dataclass
class RiskEntry:
    risk_id: str
    asset: str
    threat: str
    impact: int
    likelihood: int
    control: str
    owner: str
    detector: str
    response: str
    residual: int
    accepted_by: str | None


def load_risk_register(path: str | Path) -> list[RiskEntry]:
    """Load synthetic risk rows; validation is explicit via ``validate_risk_register``."""
    return [RiskEntry(**row) for row in load_json(path)]


def validate_risk_register(entries: list[RiskEntry], appetite: int) -> list[str]:
    issues: list[str] = []
    for entry in entries:
        required = {
            "owner": entry.owner,
            "control": entry.control,
            "detector": entry.detector,
            "response": entry.response,
        }
        for name, value in required.items():
            if not value.strip():
                issues.append(f"{entry.risk_id}: missing {name}")
        if entry.residual > appetite and not entry.accepted_by:
            issues.append(f"{entry.risk_id}: residual risk {entry.residual} exceeds appetite {appetite}")
    return issues


ControlCategory = Literal["identity", "authorization", "limit", "content", "behaviour"]
ControlLayer = Literal["prompt", "app", "gateway", "db", "cloud"]


@dataclass
class ControlMapping:
    statement: str
    category: ControlCategory
    layer: ControlLayer


def misplaced_controls(mappings: list[ControlMapping]) -> list[ControlMapping]:
    """Find controls that prompts cannot reliably enforce."""
    return [
        mapping
        for mapping in mappings
        if mapping.category in {"identity", "authorization", "limit"} and mapping.layer == "prompt"
    ]


class BudgetExceeded(RuntimeError):
    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"{kind} budget exceeded")


@dataclass
class Budget:
    max_tool_calls: int
    max_retries: int
    max_tokens: int

    def __post_init__(self) -> None:
        self._used = {"tool_calls": 0, "retries": 0, "tokens": 0}

    def consume(self, kind: str, amount: int = 1) -> None:
        limits = {
            "tool_calls": self.max_tool_calls,
            "retries": self.max_retries,
            "tokens": self.max_tokens,
        }
        if kind not in limits:
            raise ValueError(f"unsupported budget kind: {kind}")
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if self._used[kind] + amount > limits[kind]:
            raise BudgetExceeded(kind)
        self._used[kind] += amount


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        self.failure_threshold = failure_threshold
        self._consecutive_failures = 0

    @property
    def is_open(self) -> bool:
        return self._consecutive_failures >= self.failure_threshold

    def record_success(self) -> None:
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        self._consecutive_failures += 1


@dataclass
class GuardOutcome:
    decision: Decision
    reason_codes: list[str]


def guarded_detector_call(
    breaker: CircuitBreaker,
    detector: Callable[[str], float],
    text: str,
    tool_is_irreversible: bool,
) -> GuardOutcome:
    """Apply breaker state and detector failure policy around one call."""
    if breaker.is_open:
        return GuardOutcome(
            Decision.BLOCK if tool_is_irreversible else Decision.ALLOW,
            ["detector_unavailable"],
        )
    try:
        score = detector(text)
    except Exception:
        breaker.record_failure()
        return GuardOutcome(
            Decision.BLOCK if tool_is_irreversible else Decision.ALLOW,
            ["detector_unavailable"],
        )
    breaker.record_success()
    if score >= 0.6:
        return GuardOutcome(Decision.BLOCK, ["detector_threshold"])
    return GuardOutcome(Decision.ALLOW, [])


ChangeKind = Literal["threshold", "allowlist", "policy", "prompt_copy"]


@dataclass
class ChangeRequest:
    change_id: str
    kind: ChangeKind
    author: str
    reviewer: str | None
    reviewer_role: str | None


def review_change(change: ChangeRequest) -> GuardOutcome:
    if change.kind == "prompt_copy":
        return GuardOutcome(Decision.ALLOW, ["not_safety_critical"])
    if change.reviewer is None:
        return GuardOutcome(Decision.BLOCK, ["missing_reviewer"])
    if change.reviewer == change.author:
        return GuardOutcome(Decision.BLOCK, ["self_review"])
    if change.reviewer_role != "guardrail_owner":
        return GuardOutcome(Decision.BLOCK, ["reviewer_not_authorized"])
    return GuardOutcome(Decision.ALLOW, ["review_approved"])


LayerName = Literal["unit", "component", "end_to_end", "adversarial", "monitoring"]


@dataclass
class LayerResult:
    layer: LayerName
    passed: bool
    detail: str


def layered_release_decision(
    layers: list[LayerResult],
    benchmark_score: float,
) -> GuardOutcome:
    required: tuple[LayerName, ...] = (
        "unit",
        "component",
        "end_to_end",
        "adversarial",
        "monitoring",
    )
    by_name = {layer.layer: layer for layer in layers}
    reasons = [f"benchmark={benchmark_score:.2f}"]
    reasons.extend(f"missing_layer:{name}" for name in required if name not in by_name)
    reasons.extend(
        f"layer_failed:{name}" for name in required if name in by_name and not by_name[name].passed
    )
    return GuardOutcome(Decision.ALLOW if len(reasons) == 1 else Decision.BLOCK, reasons)


@dataclass
class ReviewPacket:
    proposed_action: dict[str, Any]
    evidence_ids: list[str]
    uncertainty: str
    consequences: str
    rollback: str


def validate_packet(packet: ReviewPacket) -> list[str]:
    issues: list[str] = []
    if not packet.proposed_action:
        issues.append("missing proposed action")
    if not packet.evidence_ids:
        issues.append("missing evidence")
    if not packet.uncertainty.strip():
        issues.append("missing uncertainty")
    if not packet.consequences.strip():
        issues.append("missing consequences")
    if not packet.rollback.strip():
        issues.append("missing rollback")
    return issues


@dataclass
class GateItem:
    item: str
    passed: bool
    evidence: str


class ReleaseGate:
    def evaluate(
        self,
        manifest: dict[str, Any],
        risk_issues: list[str],
        layers_outcome: GuardOutcome,
    ) -> list[GateItem]:
        policy = manifest.get("policy", {})
        controls = manifest.get("controls", {})
        side_effects = manifest.get("side_effects", {})
        datasets = manifest.get("datasets", {})
        logging = manifest.get("logging", {})
        budgets = manifest.get("budgets", {})
        change_control = manifest.get("change_control", {})
        incident = manifest.get("incident", {})
        required_controls = ("input", "retrieval", "tool", "output")
        required_side_effects = ("preview", "approval", "idempotency", "verification")
        required_budgets = ("timeout", "rate_limit", "kill_switch")
        items = [
            GateItem(
                "policy owner and version",
                bool(policy.get("owner")) and bool(policy.get("version")),
                "manifest.policy.owner and manifest.policy.version",
            ),
            GateItem(
                "trust boundaries documented",
                manifest.get("boundaries_documented") is True,
                "manifest.boundaries_documented",
            ),
            GateItem(
                "input, retrieval, tool, and output controls",
                all(controls.get(name) for name in required_controls),
                "manifest.controls[input,retrieval,tool,output]",
            ),
            GateItem(
                "authorization enforced outside the model",
                manifest.get("authorization_layer") != "prompt",
                "manifest.authorization_layer",
            ),
            GateItem(
                "side effects have preview, approval, idempotency, and verification",
                all(side_effects.get(name) is True for name in required_side_effects),
                "manifest.side_effects[preview,approval,idempotency,verification]",
            ),
            GateItem(
                "false-positive and false-negative datasets exist",
                bool(datasets.get("false_positive")) and bool(datasets.get("false_negative")),
                "manifest.datasets.false_positive and manifest.datasets.false_negative",
            ),
            GateItem(
                "logs are sufficient but privacy-minimized",
                logging.get("privacy_minimized") is True,
                "manifest.logging.privacy_minimized",
            ),
            GateItem(
                "budgets, timeouts, rate limits, and kill switches",
                all(budgets.get(name) is True for name in required_budgets),
                "manifest.budgets[timeout,rate_limit,kill_switch]",
            ),
            GateItem(
                "policy changes require review and rollback",
                change_control.get("review_required") is True and change_control.get("rollback") is True,
                "manifest.change_control[review_required,rollback]",
            ),
            GateItem(
                "incident response and appeal paths are tested",
                incident.get("playbook_tested") is True and incident.get("appeal_tested") is True,
                "manifest.incident[playbook_tested,appeal_tested]",
            ),
            GateItem(
                "risk register validated",
                not risk_issues,
                "validate_risk_register result",
            ),
            GateItem(
                "evaluation layers pass",
                layers_outcome.decision is Decision.ALLOW,
                "layered_release_decision result",
            ),
        ]
        return items


def gate_passed(items: list[GateItem]) -> bool:
    return all(item.passed for item in items)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
