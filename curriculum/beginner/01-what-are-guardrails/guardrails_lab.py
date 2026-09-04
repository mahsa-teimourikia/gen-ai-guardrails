"""A deterministic, provider-neutral lab for layered GenAI guardrails."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable
from uuid import uuid4


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


class OnError(str, Enum):
    FAIL_OPEN = "fail_open"
    FAIL_CLOSED = "fail_closed"


@dataclass
class PolicyRecord:
    policy_id: str
    rail: str
    scope: str
    signal: str
    decision_on_violation: Decision
    owner: str
    evidence: str | list[str]
    exception: str
    on_error: OnError


@dataclass
class Identity:
    user_id: str
    role: str
    business_unit: str
    authenticated: bool

    def __post_init__(self) -> None:
        if self.role not in {"employee", "manager", "hr_admin"}:
            raise ValueError(f"unsupported role: {self.role}")
        if self.business_unit not in {"bu-north", "bu-south"}:
            raise ValueError(f"unsupported business unit: {self.business_unit}")


@dataclass
class DecisionRecord:
    rail: str
    policy_id: str
    decision: Decision
    reasons: list[str]
    identity_hash: str
    correlation_id: str
    detector_version: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize an audit-safe record without raw identity or input text."""
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return json.dumps(payload, sort_keys=True)


@dataclass
class Document:
    doc_id: str
    business_unit: str
    title: str
    text: str
    source: str
    version: str


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


class Ledger:
    """A fake side-effect ledger used to demonstrate ordering."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(self, entry: dict[str, Any]) -> None:
        self._entries.append(dict(entry))

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)


@dataclass
class PipelineResult:
    terminal: Decision
    deciding_rail: str
    records: list[DecisionRecord]


class DetectorUnavailable(RuntimeError):
    """Raised when a detector cannot produce a result."""


Detector = Callable[..., bool]


def topic_classifier(text: str) -> bool:
    """Heuristic stand-in; production uses a tested classifier."""
    return any(word in text.lower() for word in ("weather forecast", "recipe for", "sports scores"))


def injection_heuristic(text: str) -> bool:
    """Heuristic stand-in; production uses a tested classifier."""
    lowered = text.lower()
    markers = (
        "ignore prior",
        "ignore previous",
        "system prompt",
        "export all salaries",
        "disregard policy",
    )
    return any(marker in lowered for marker in markers)


def failing_detector(*_args: Any, **_kwargs: Any) -> bool:
    """Test helper that simulates a detector outage."""
    raise DetectorUnavailable("detector unavailable")


DEFAULT_DETECTORS: dict[str, Detector] = {
    "topic_classifier": topic_classifier,
    "injection_heuristic": injection_heuristic,
}

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_WRITE_TOOLS = {"issue_payroll_adjustment"}
_ALLOWED_TOOLS = {"read_ticket", "issue_payroll_adjustment"}


def _identity_hash(identity: Identity | None) -> str:
    user_id = identity.user_id if identity else ""
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def _policy_map(policies: list[PolicyRecord]) -> dict[str, PolicyRecord]:
    return {policy.policy_id: policy for policy in policies}


def _record(
    rail: str,
    policy_id: str,
    decision: Decision,
    reasons: list[str],
    identity: Identity | None,
    correlation_id: str | None = None,
    detector_version: str = "deterministic-v1",
    metadata: dict[str, Any] | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        rail=rail,
        policy_id=policy_id,
        decision=decision,
        reasons=reasons,
        identity_hash=_identity_hash(identity),
        correlation_id=correlation_id or str(uuid4()),
        detector_version=detector_version,
        metadata=metadata or {},
    )


def _detector_record(
    rail: str,
    policy: PolicyRecord,
    identity: Identity | None,
    detector_name: str,
    correlation_id: str | None,
) -> DecisionRecord:
    decision = Decision.ALLOW if policy.on_error is OnError.FAIL_OPEN else Decision.BLOCK
    return _record(
        rail,
        policy.policy_id,
        decision,
        ["detector_unavailable"],
        identity,
        correlation_id,
        detector_version=f"{detector_name}-unavailable",
        metadata={"audit_event": "detector_unavailable", "detector": detector_name},
    )


def _call_detector(
    detector: Detector,
    detector_name: str,
    policy: PolicyRecord,
    args: tuple[Any, ...],
    rail: str,
    identity: Identity | None,
    correlation_id: str | None,
) -> tuple[bool | None, DecisionRecord | None]:
    try:
        return bool(detector(*args)), None
    except Exception:
        return None, _detector_record(rail, policy, identity, detector_name, correlation_id)


def guard_input(
    text: str,
    identity: Identity,
    policies: list[PolicyRecord],
    detectors: dict[str, Detector] | None = None,
) -> DecisionRecord:
    """Apply authentication, size, topic, and injection checks."""
    policy = _policy_map(policies)
    correlation_id = str(uuid4())
    if not identity.authenticated:
        return _record("input", "input-authentication", Decision.BLOCK, ["authentication_required"], identity, correlation_id)
    if len(text) > 20_000:
        return _record("input", "input-size", Decision.BLOCK, ["input_too_large"], identity, correlation_id)

    detector_map = detectors or DEFAULT_DETECTORS
    topic_policy = policy["input-topic"]
    detected, outage = _call_detector(
        detector_map["topic_classifier"],
        "topic_classifier",
        topic_policy,
        (text,),
        "input",
        identity,
        correlation_id,
    )
    if outage:
        return outage
    elif detected:
        return _record("input", topic_policy.policy_id, topic_policy.decision_on_violation, ["out_of_scope"], identity, correlation_id, "topic-heuristic-v1")

    injection_policy = policy["input-injection"]
    detected, outage = _call_detector(
        detector_map["injection_heuristic"],
        "injection_heuristic",
        injection_policy,
        (text,),
        "input",
        identity,
        correlation_id,
    )
    if outage:
        return outage
    if detected:
        return _record("input", injection_policy.policy_id, injection_policy.decision_on_violation, ["possible_prompt_injection"], identity, correlation_id, "injection-heuristic-v1")
    return _record("input", "input-authentication", Decision.ALLOW, [], identity, correlation_id)


def guard_retrieval(
    docs: list[Document],
    identity: Identity,
    policies: list[PolicyRecord],
) -> tuple[list[Document], list[DecisionRecord]]:
    """Filter tenant scope before context and quarantine poisoned documents."""
    policy = _policy_map(policies)
    records: list[DecisionRecord] = []
    allowed: list[Document] = []
    for doc in docs:
        correlation_id = str(uuid4())
        if doc.business_unit != identity.business_unit:
            records.append(
                _record(
                    "retrieval",
                    "retrieval-scope",
                    Decision.BLOCK,
                    ["business_unit_not_authorized"],
                    identity,
                    correlation_id,
                    metadata={"doc_id": doc.doc_id, "source": doc.source, "version": doc.version},
                )
            )
            continue
        if injection_heuristic(doc.text):
            records.append(
                _record(
                    "retrieval",
                    "retrieval-injection",
                    Decision.TRANSFORM,
                    ["poisoned_document_quarantined"],
                    identity,
                    correlation_id,
                    detector_version="injection-heuristic-v1",
                    metadata={"doc_id": doc.doc_id, "source": doc.source, "version": doc.version, "provenance_retained": True},
                )
            )
            continue
        allowed.append(doc)
    if any(record.decision is Decision.BLOCK for record in records):
        return [], records
    return allowed, records


def guard_tool_call(
    identity: Identity,
    call: ToolCall,
    policies: list[PolicyRecord],
    detectors: dict[str, Detector] | None = None,
) -> DecisionRecord:
    """Validate tool capability, authorization, schema, and approval."""
    policy = _policy_map(policies)
    correlation_id = str(uuid4())
    authorization_detector = (detectors or {}).get("authorization")
    if authorization_detector:
        _, outage = _call_detector(
            authorization_detector,
            "authorization",
            policy["tool-authorization"],
            (identity, call),
            "execution",
            identity,
            correlation_id,
        )
        if outage:
            return outage
    if call.name not in _ALLOWED_TOOLS:
        return _record("execution", "tool-allowlist", Decision.BLOCK, ["tool_not_allowed"], identity, correlation_id)
    if not isinstance(call.arguments, dict):
        return _record("execution", "tool-schema", Decision.BLOCK, ["invalid_arguments"], identity, correlation_id)
    if call.name == "read_ticket":
        if not isinstance(call.arguments.get("ticket_id"), str) or not call.arguments["ticket_id"]:
            return _record("execution", "tool-schema", Decision.BLOCK, ["invalid_arguments"], identity, correlation_id)
        return _record("execution", "tool-allowlist", Decision.ALLOW, [], identity, correlation_id)
    if not isinstance(call.arguments.get("employee_id"), str) or not isinstance(call.arguments.get("amount"), (int, float)):
        return _record("execution", "tool-schema", Decision.BLOCK, ["invalid_arguments"], identity, correlation_id)
    if call.arguments["amount"] <= 0:
        return _record("execution", "tool-schema", Decision.BLOCK, ["invalid_arguments"], identity, correlation_id)
    if identity.role != "hr_admin":
        return _record("execution", "tool-authorization", Decision.BLOCK, ["write_not_authorized"], identity, correlation_id)
    return _record("execution", "tool-approval", Decision.ESCALATE, ["approval_required"], identity, correlation_id)


def verify_tool_result(call: ToolCall, result: Any, ledger: Ledger) -> DecisionRecord:
    """Check a tool result after execution and preserve a receipt in the ledger."""
    if isinstance(result, dict) and result.get("success") is True:
        ledger.record({"tool": call.name, "operation_id": result.get("operation_id", "synthetic-receipt")})
        return _record("execution", "tool-result", Decision.ALLOW, [], None, metadata={"verified": True})
    return _record("execution", "tool-result", Decision.ABSTAIN, ["tool_result_unverified"], None, metadata={"verified": False})


def guard_output(
    text: str,
    evidence_docs: list[Document],
    policies: list[PolicyRecord],
) -> DecisionRecord:
    """Redact PII and abstain from explicitly unsupported claims."""
    if _EMAIL.search(text) or _SSN.search(text):
        redacted = _EMAIL.sub("[REDACTED]", _SSN.sub("[REDACTED]", text))
        return _record(
            "output",
            "output-sensitive-data",
            Decision.TRANSFORM,
            ["sensitive_data"],
            None,
            metadata={"redacted": True, "redacted_text": redacted, "evidence_count": len(evidence_docs)},
        )
    if "unsupported claim" in text.lower() or "without evidence" in text.lower():
        return _record("output", "output-groundedness", Decision.ABSTAIN, ["unsupported_claim"], None, metadata={"evidence_count": len(evidence_docs)})
    return _record("output", "output-sensitive-data", Decision.ALLOW, [], None, metadata={"evidence_count": len(evidence_docs)})


def run_pipeline(
    request: dict[str, Any],
    identity: Identity,
    policies: list[PolicyRecord],
    kb: list[Document],
    ledger: Ledger,
    detectors: dict[str, Detector] | None = None,
    misordered: bool = False,
) -> PipelineResult:
    """Run a request through input, retrieval, execution, and output rails."""
    records: list[DecisionRecord] = []
    input_text = "x" * 20_001 if request.get("oversize") else request.get("text", "")
    input_record = guard_input(input_text, identity, policies, detectors or DEFAULT_DETECTORS)
    records.append(input_record)
    if input_record.decision is not Decision.ALLOW:
        return PipelineResult(input_record.decision, input_record.rail, records)

    by_id = {doc.doc_id: doc for doc in kb}
    docs = [by_id[doc_id] for doc_id in request.get("retrieved_doc_ids", []) if doc_id in by_id]
    filtered_docs, retrieval_records = guard_retrieval(docs, identity, policies)
    records.extend(retrieval_records)
    if any(record.decision is Decision.BLOCK for record in retrieval_records):
        return PipelineResult(Decision.BLOCK, "retrieval", records)
    if retrieval_records and not request.get("tool_call") and not request.get("output_text"):
        transform = next((record for record in retrieval_records if record.decision is Decision.TRANSFORM), None)
        if transform:
            return PipelineResult(Decision.TRANSFORM, "retrieval", records)

    tool_data = request.get("tool_call")
    if tool_data:
        call = ToolCall(tool_data["name"], tool_data.get("arguments", {}))
        if misordered:
            ledger.record({"tool": call.name, "arguments": dict(call.arguments), "ordering": "before_guard"})
        tool_record = guard_tool_call(identity, call, policies, detectors)
        records.append(tool_record)
        if tool_record.decision is not Decision.ALLOW:
            return PipelineResult(tool_record.decision, tool_record.rail, records)
        if not misordered and call.name in _WRITE_TOOLS:
            ledger.record({"tool": call.name, "arguments": dict(call.arguments), "ordering": "after_guard"})
        if request.get("tool_result") is not None:
            result_record = verify_tool_result(call, request["tool_result"], ledger)
            records.append(result_record)
            if result_record.decision is not Decision.ALLOW:
                return PipelineResult(result_record.decision, result_record.rail, records)

    output_text = request.get("output_text")
    if output_text:
        output_record = guard_output(output_text, filtered_docs, policies)
        records.append(output_record)
        if output_record.decision is not Decision.ALLOW:
            return PipelineResult(output_record.decision, output_record.rail, records)
    return PipelineResult(Decision.ALLOW, "output" if output_text else ("execution" if tool_data else "input"), records)


def default_policies() -> list[PolicyRecord]:
    return [
        PolicyRecord("input-authentication", "input", "all requests", "authentication", Decision.BLOCK, "identity", "identity provider", "authenticated identity", OnError.FAIL_CLOSED),
        PolicyRecord("input-size", "input", "all requests", "size", Decision.BLOCK, "platform", "request length", "trusted internal client", OnError.FAIL_CLOSED),
        PolicyRecord("input-topic", "input", "support assistant", "topic", Decision.ESCALATE, "product", "topic classifier", "human routing", OnError.FAIL_OPEN),
        PolicyRecord("input-injection", "input", "all requests", "prompt injection", Decision.ESCALATE, "security", "injection signal", "review queue", OnError.FAIL_CLOSED),
        PolicyRecord("retrieval-scope", "retrieval", "internal documents", "business unit", Decision.BLOCK, "data owner", "document ACL", "approved cross-unit transfer", OnError.FAIL_CLOSED),
        PolicyRecord("retrieval-injection", "retrieval", "retrieved documents", "embedded instruction", Decision.TRANSFORM, "security", "document scan", "quarantine and review", OnError.FAIL_CLOSED),
        PolicyRecord("tool-allowlist", "execution", "support tools", "tool name", Decision.BLOCK, "platform", "allowlist", "new reviewed tool", OnError.FAIL_CLOSED),
        PolicyRecord("tool-authorization", "execution", "write tools", "identity role", Decision.BLOCK, "HR", "role authorization", "approved HR admin", OnError.FAIL_CLOSED),
        PolicyRecord("tool-schema", "execution", "all tools", "arguments", Decision.BLOCK, "platform", "schema validation", "corrected arguments", OnError.FAIL_CLOSED),
        PolicyRecord("tool-approval", "execution", "payroll writes", "side effect", Decision.ESCALATE, "HR", "approval record", "human approval", OnError.FAIL_CLOSED),
        PolicyRecord("tool-result", "execution", "executed tools", "receipt", Decision.ABSTAIN, "platform", "operation receipt", "reconciliation", OnError.FAIL_CLOSED),
        PolicyRecord("output-sensitive-data", "output", "assistant responses", "PII", Decision.TRANSFORM, "privacy", "PII pattern", "redaction review", OnError.FAIL_CLOSED),
        PolicyRecord("output-groundedness", "output", "assistant responses", "unsupported claim", Decision.ABSTAIN, "product", "evidence", "ask for evidence", OnError.FAIL_CLOSED),
    ]


def load_fixtures(path: str | Path) -> Any:
    """Load a JSON fixture file or all JSON fixtures in a directory."""
    fixture_path = Path(path)
    if fixture_path.is_dir():
        return {item.stem: json.loads(item.read_text(encoding="utf-8")) for item in sorted(fixture_path.glob("*.json"))}
    return json.loads(fixture_path.read_text(encoding="utf-8"))
