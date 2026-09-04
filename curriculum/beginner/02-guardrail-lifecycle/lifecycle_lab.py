"""A deterministic, provider-neutral guardrail lifecycle lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


class Mode(str, Enum):
    SHADOW = "shadow"
    ALERT = "alert"
    ENFORCE = "enforce"


@dataclass
class Identity:
    user_id: str
    role: str
    business_unit: str
    authenticated: bool = True

    def __post_init__(self) -> None:
        if self.role not in {"employee", "manager", "hr_admin"}:
            raise ValueError(f"unsupported role: {self.role}")
        if self.business_unit not in {"bu-north", "bu-south"}:
            raise ValueError(f"unsupported business unit: {self.business_unit}")


@dataclass
class Policy:
    policy_id: str
    version: int
    owner: str
    threshold: float
    mode: Mode
    prohibited: list[str]
    required: list[str]
    escalation: list[str]
    tool_rules: dict[str, str]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Policy":
        data = dict(value)
        data["mode"] = Mode(data["mode"])
        data["version"] = int(data["version"])
        return cls(**data)


@dataclass
class TrafficItem:
    request_id: str
    identity: dict[str, Any]
    text_summary: str
    tool_call: dict[str, Any] | None
    detector_score: float
    detector_version: str
    label: str
    unsafe_if_allowed: bool

    def __post_init__(self) -> None:
        if self.label not in {"legitimate", "attack", "boundary"}:
            raise ValueError(f"unsupported traffic label: {self.label}")


@dataclass
class Observation:
    request_id: str
    identity_hash: str
    role: str
    business_unit: str
    tool_name: str
    detector_score: float
    detector_version: str
    policy_version: int


@dataclass
class DecisionRecord:
    request_id: str
    decision: Decision
    reason_codes: list[str]
    policy_version: int
    confidence: float | None
    would_be_decision: Decision | None
    next_step: str

    def to_json(self) -> str:
        payload = {
            "request_id": self.request_id,
            "decision": self.decision.value,
            "reason_codes": self.reason_codes,
            "policy_version": self.policy_version,
            "confidence": self.confidence,
            "would_be_decision": self.would_be_decision.value if self.would_be_decision else None,
            "next_step": self.next_step,
        }
        return json.dumps(payload, sort_keys=True)


@dataclass
class Metrics:
    """tp/fp/fn/tn count attack and non-attack outcomes.

    Positives are items labelled ``attack``; boundary items count as legitimate
    for false positives and friction.  ``tpr`` is ``tp / (tp + fn)`` and
    ``fpr`` is ``fp / (fp + tn)``.  ``attempts_blocked`` counts attacks whose
    applied decision is BLOCK or ESCALATE.  ``unsafe_completed`` counts items
    marked ``unsafe_if_allowed`` whose applied decision is ALLOW.  ``friction``
    is non-ALLOW decisions for legitimate and boundary items divided by the
    count of those items.  Empty denominators produce 0.0.
    """

    tp: int
    fp: int
    fn: int
    tn: int
    tpr: float
    fpr: float
    attempts_blocked: int
    unsafe_completed: int
    friction: float


class Ledger:
    """A tiny receipt ledger with idempotent execution."""

    def __init__(self) -> None:
        self._receipts: dict[str, dict[str, Any]] = {}

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._receipts.values())

    def execute_with_receipt(self, call: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self._receipts:
            return dict(self._receipts[idempotency_key])
        receipt = {
            "operation_id": f"op-{uuid4()}",
            "idempotency_key": idempotency_key,
            "tool": call.get("name", ""),
            "arguments": dict(call.get("arguments", {})),
            "status": "completed",
        }
        self._receipts[idempotency_key] = receipt
        return dict(receipt)

    def verify(self, receipt: dict[str, Any]) -> bool:
        key = receipt.get("idempotency_key")
        return bool(key and self._receipts.get(key) == receipt and receipt.get("status") == "completed")


_ROLE_RANK = {"employee": 0, "manager": 1, "hr_admin": 2}
_DECISION_NEXT_STEPS = {
    Decision.ALLOW: "continue and record the decision",
    Decision.TRANSFORM: "continue with transformed output",
    Decision.BLOCK: "offer a policy-compliant alternative",
    Decision.ABSTAIN: "request missing evidence or permission",
    Decision.ESCALATE: "pause, checkpoint state, and route to a reviewer",
}


def _identity_hash(identity: dict[str, Any]) -> str:
    return hashlib.sha256(str(identity.get("user_id", "")).encode("utf-8")).hexdigest()


def observe(item: TrafficItem, policy: Policy) -> Observation:
    """Capture minimum decision signal without retaining raw identity."""
    return Observation(
        request_id=item.request_id,
        identity_hash=_identity_hash(item.identity),
        role=item.identity.get("role", ""),
        business_unit=item.identity.get("business_unit", ""),
        tool_name=(item.tool_call or {}).get("name", ""),
        detector_score=item.detector_score,
        detector_version=item.detector_version,
        policy_version=policy.version,
    )


def _computed_decision(obs: Observation, policy: Policy) -> tuple[Decision, list[str], float | None]:
    if obs.tool_name in policy.tool_rules:
        minimum_role = policy.tool_rules[obs.tool_name]
        if _ROLE_RANK.get(obs.role, -1) < _ROLE_RANK.get(minimum_role, 99):
            return Decision.BLOCK, ["role_not_authorized"], None
    if obs.detector_score >= policy.threshold:
        decision = Decision.ESCALATE if obs.tool_name else Decision.BLOCK
        return decision, ["detector_threshold"], obs.detector_score
    return Decision.ALLOW, [], None


def decide(obs: Observation, policy: Policy) -> DecisionRecord:
    """Apply deterministic capability checks before detector scoring."""
    computed, reasons, confidence = _computed_decision(obs, policy)
    applied = computed
    reason_codes = list(reasons)
    if policy.mode is Mode.SHADOW:
        applied = Decision.ALLOW
        reason_codes.append("shadow_mode")
    elif policy.mode is Mode.ALERT:
        applied = Decision.ALLOW
        reason_codes.append("alert_raised")
    return DecisionRecord(
        request_id=obs.request_id,
        decision=applied,
        reason_codes=reason_codes,
        policy_version=policy.version,
        confidence=confidence,
        would_be_decision=computed,
        next_step=_DECISION_NEXT_STEPS[applied],
    )


def recover(record: DecisionRecord, attempt: int, max_retries: int = 2) -> str:
    """Return a safe recovery action; retryable errors are capped."""
    if "retryable_error" in record.reason_codes:
        if attempt < max_retries:
            return "retry with a varied strategy"
        return "escalate after retry limit"
    return _DECISION_NEXT_STEPS[record.decision]


def _metrics_from_records(traffic: list[TrafficItem], records: list[DecisionRecord], use_would_be: bool = False) -> Metrics:
    record_by_id = {record.request_id: record for record in records}
    tp = fp = fn = tn = attempts_blocked = unsafe_completed = friction_count = 0
    friction_total = sum(item.label in {"legitimate", "boundary"} for item in traffic)
    for item in traffic:
        record = record_by_id[item.request_id]
        decision = record.would_be_decision if use_would_be else record.decision
        blocked = decision in {Decision.BLOCK, Decision.ESCALATE}
        if item.label == "attack":
            if blocked:
                tp += 1
                attempts_blocked += 1
            else:
                fn += 1
        else:
            if blocked:
                fp += 1
            else:
                tn += 1
            if decision is not Decision.ALLOW:
                friction_count += 1
        if item.unsafe_if_allowed and decision is Decision.ALLOW:
            unsafe_completed += 1
    tpr_denominator = tp + fn
    fpr_denominator = fp + tn
    return Metrics(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        tpr=tp / tpr_denominator if tpr_denominator else 0.0,
        fpr=fp / fpr_denominator if fpr_denominator else 0.0,
        attempts_blocked=attempts_blocked,
        unsafe_completed=unsafe_completed,
        friction=friction_count / friction_total if friction_total else 0.0,
    )


def evaluate(
    traffic: list[TrafficItem],
    policy: Policy,
    mode: Mode,
) -> tuple[Metrics, list[DecisionRecord]]:
    """Evaluate labelled traffic using the requested rollout mode."""
    evaluated_policy = replace(policy, mode=Mode(mode))
    records = [decide(observe(item, evaluated_policy), evaluated_policy) for item in traffic]
    return _metrics_from_records(traffic, records), records


def evaluate_would_be(traffic: list[TrafficItem], policy: Policy) -> Metrics:
    """Measure the decisions that enforcement would make in shadow mode."""
    _, records = evaluate(traffic, policy, Mode.SHADOW)
    return _metrics_from_records(traffic, records, use_would_be=True)


def compare(first: Metrics, second: Metrics) -> dict[str, float]:
    """Return second-minus-first deltas for every metric."""
    before = asdict(first)
    return {name: value - before[name] for name, value in asdict(second).items()}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
