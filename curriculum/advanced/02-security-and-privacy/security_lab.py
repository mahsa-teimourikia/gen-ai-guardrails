"""Deterministic security and privacy controls for an HR/IT assistant."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


ROLE_RANK = {"employee": 1, "manager": 2, "hr_admin": 3}


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True)
class Session:
    user_id: str
    tenant: str
    role: str
    clearance: str
    session_id: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Session":
        return cls(**value)


@dataclass
class Content:
    content_id: str
    text: str
    provenance: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Content":
        return cls(value["content_id"], value["text"], value["provenance"])


def extract_claims(content: Content) -> list[str]:
    """Heuristic claims are signals, not trusted identity or authority."""
    patterns = [
        r"\brole\s*=\s*[a-z_]+",
        r"\byou are now\b[^.!?\n]*",
        r"\bgrant\b[^.!?\n]*",
        r"\bignore previous\b[^.!?\n]*",
    ]
    return [
        match.group(0).strip()
        for pattern in patterns
        for match in re.finditer(pattern, content.text, flags=re.IGNORECASE)
    ]


def effective_authority(session: Session, contents: list[Content]) -> Session:
    del contents
    return session


def detect_injection(content: Content, scores: dict[str, float]) -> float:
    return float(scores[content.content_id])


@dataclass
class ToolPlan:
    tool: str
    resource: str
    args: dict[str, Any]
    tenant: str
    idempotency_key: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ToolPlan":
        return cls(**value)


@dataclass
class Capability:
    tool: str
    min_role: str
    allowed_resources: list[str]
    side_effect: bool
    arg_schema: dict[str, str]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Capability":
        return cls(**value)


@dataclass
class AuthorizationState:
    user_roles: dict[str, str]
    tenant_membership: dict[str, list[str]]
    revoked_sessions: set[str] = field(default_factory=set)
    disabled_capabilities: set[str] = field(default_factory=set)
    used_idempotency_keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    revoked_credentials: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuthorizationState":
        return cls(
            user_roles=dict(value["user_roles"]),
            tenant_membership={
                user: list(tenants)
                for user, tenants in value["tenant_membership"].items()
            },
            revoked_sessions=set(value["revoked_sessions"]),
            disabled_capabilities=set(value["disabled_capabilities"]),
            used_idempotency_keys=dict(value["used_idempotency_keys"]),
            revoked_credentials=list(value["revoked_credentials"]),
        )

    def revoke_session(self, session_id: str) -> None:
        self.revoked_sessions.add(session_id)

    def downgrade_role(self, user_id: str, role: str) -> None:
        self.user_roles[user_id] = role


@dataclass
class GateResult:
    decision: Decision
    reason_codes: list[str]
    side_effect_executed: bool
    audit_event: dict[str, Any] | None


def _gate(
    decision: Decision,
    reasons: list[str],
    plan: ToolPlan,
    session: Session,
    side_effect: bool = False,
    audit_event: dict[str, Any] | None = None,
) -> GateResult:
    event = audit_event or {
        "event_id": f"event-{plan.idempotency_key}",
        "capability": plan.tool,
        "tool": plan.tool,
        "resource": plan.resource,
        "tenant": plan.tenant,
        "user_id": session.user_id,
        "session_id": session.session_id,
        "side_effect": side_effect,
    }
    return GateResult(decision, reasons, side_effect, event)


def _capability(capabilities: dict[str, Capability], tool: str) -> Capability | None:
    return capabilities.get(tool)


def _state_role(session: Session, state: AuthorizationState) -> str:
    return state.user_roles.get(session.user_id, session.role)


def _type_matches(value: Any, expected: str) -> bool:
    types = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
    }
    expected_type = types.get(expected)
    return expected_type is not None and isinstance(value, expected_type) and not (
        expected == "int" and isinstance(value, bool)
    )


def _binding_checks(
    plan: ToolPlan,
    session: Session,
    state: AuthorizationState,
    capabilities: dict[str, Capability],
) -> tuple[Capability | None, list[str]]:
    capability = _capability(capabilities, plan.tool)
    if capability is None:
        return None, ["tool_not_allowed"]
    if session.session_id in state.revoked_sessions:
        return capability, ["session_revoked"]
    if _state_role(session, state) not in ROLE_RANK or ROLE_RANK[_state_role(session, state)] < ROLE_RANK.get(capability.min_role, 99):
        return capability, ["role_not_authorized"]
    if plan.tenant != session.tenant or session.tenant not in state.tenant_membership.get(session.user_id, []):
        return capability, ["cross_tenant"]
    if plan.resource not in capability.allowed_resources:
        return capability, ["resource_not_allowed"]
    for name, expected in capability.arg_schema.items():
        if name not in plan.args or not _type_matches(plan.args[name], expected):
            return capability, ["invalid_arguments"]
    if capability.tool in state.disabled_capabilities:
        return capability, ["capability_disabled"]
    return capability, []


def plan_check(
    plan: ToolPlan,
    session: Session,
    state: AuthorizationState,
    capabilities: dict[str, Capability],
) -> GateResult:
    capability, reasons = _binding_checks(plan, session, state, capabilities)
    if reasons:
        return _gate(Decision.BLOCK, reasons, plan, session)
    assert capability is not None
    return _gate(Decision.ALLOW, ["plan_authorized"], plan, session, False)


def execute(
    plan: ToolPlan,
    session: Session,
    state: AuthorizationState,
    capabilities: dict[str, Capability],
    detector_score: float,
    threshold: float,
) -> GateResult:
    capability, reasons = _binding_checks(plan, session, state, capabilities)
    if reasons:
        return _gate(Decision.BLOCK, reasons, plan, session)
    assert capability is not None
    if plan.idempotency_key in state.used_idempotency_keys:
        return _gate(Decision.ALLOW, ["replayed"], plan, session, False)
    if detector_score >= threshold:
        return _gate(Decision.ESCALATE, ["injection_suspected"], plan, session)
    event = {
        "event_id": f"event-{plan.idempotency_key}",
        "capability": plan.tool,
        "tool": plan.tool,
        "resource": plan.resource,
        "tenant": plan.tenant,
        "user_id": session.user_id,
        "session_id": session.session_id,
        "side_effect": capability.side_effect,
    }
    if capability.side_effect:
        state.used_idempotency_keys[plan.idempotency_key] = event
    return _gate(Decision.ALLOW, ["executed"], plan, session, capability.side_effect, event)


@dataclass
class DataClass:
    name: str
    purpose: str
    retention_days: int
    residency: str
    legal_basis: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DataClass":
        return cls(**value)


@dataclass(frozen=True)
class Entity:
    kind: str
    span: tuple[int, int]
    value: str


def detect_pii(text: str) -> list[Entity]:
    patterns = [
        ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ("phone", r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)"),
        ("employee_id", r"\bEMP-\d{5}\b"),
        ("iban", r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    ]
    found: list[Entity] = []
    for kind, pattern in patterns:
        found.extend(Entity(kind, match.span(), match.group(0)) for match in re.finditer(pattern, text))
    return sorted(found, key=lambda entity: entity.span)


class ReidentificationDenied(PermissionError):
    pass


@dataclass
class _Token:
    value: str
    created: datetime


@dataclass
class TokenVault:
    purpose: str
    ttl_days: int
    allowed_roles: list[str]
    _tokens: dict[str, _Token] = field(default_factory=dict, init=False, repr=False)
    _counter: int = field(default=0, init=False, repr=False)

    def tokenize(
        self,
        text: str,
        entities: list[Entity],
        now: datetime,
    ) -> tuple[str, dict[str, str]]:
        masked = text
        tokens: dict[str, str] = {}
        assignments: dict[Entity, str] = {}
        for entity in sorted(entities, key=lambda item: item.span):
            self._counter += 1
            assignments[entity] = f"<{entity.kind.upper()}_TOKEN_{self._counter}>"
            tokens[assignments[entity]] = entity.value
        for entity in sorted(entities, key=lambda item: item.span, reverse=True):
            token = assignments[entity]
            masked = masked[: entity.span[0]] + token + masked[entity.span[1] :]
            self._tokens[token] = _Token(entity.value, now)
        return masked, tokens

    def detokenize(
        self,
        token: str,
        session: Session,
        purpose: str,
        now: datetime,
    ) -> str:
        record = self._tokens.get(token)
        if (
            record is None
            or purpose != self.purpose
            or session.role not in self.allowed_roles
            or now > record.created + timedelta(days=self.ttl_days)
        ):
            raise ReidentificationDenied(token)
        return record.value


def external_call_boundary(text: str, vault: TokenVault, now: datetime) -> str:
    masked, _ = vault.tokenize(text, detect_pii(text), now)
    return masked


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[A-Z0-9]{12,}\b"),
    re.compile(r"(?i)\bpassword\s*=\s*\S+"),
]


def redact(text: str) -> tuple[str, int]:
    count = 0
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED]", redacted)
        count += replacements
    return redacted, count


class AuditLog:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append(self, event: dict[str, Any]) -> str:
        record = dict(event)
        record["prev_hash"] = self.head_hash()
        record["event_hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.events.append(record)
        return record["event_hash"]

    def head_hash(self) -> str:
        return self.events[-1]["event_hash"] if self.events else ""

    def verify_chain(self) -> bool:
        previous = ""
        for event in self.events:
            if event.get("prev_hash") != previous:
                return False
            expected = dict(event)
            actual = expected.pop("event_hash", None)
            digest = hashlib.sha256(
                json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if actual != digest:
                return False
            previous = actual
        return True


@dataclass
class ConversationLog:
    retention_days: int
    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, text: str, now: datetime) -> None:
        safe, _ = redact(text)
        self.events.append({"at": now.isoformat(), "text": safe})


def reconstruct_secret(fragments: list[str]) -> bool:
    values = [
        fragment.split(":", 1)[1].strip() if ":" in fragment else fragment.strip()
        for fragment in fragments
    ]
    _, count = redact("".join(values))
    return count > 0


@dataclass(frozen=True)
class ArtifactManifest:
    name: str
    version: str
    sha256: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ArtifactManifest":
        return cls(**value)


def verify_artifacts(
    manifest: list[ArtifactManifest],
    actual: dict[str, str],
) -> list[str]:
    return [
        f"{item.name}:sha256_mismatch"
        for item in manifest
        if actual.get(item.name) != item.sha256
    ]


def detector_upgrade_gate(
    regression_cases: list[dict[str, Any]],
    old_scores: dict[str, float],
    new_scores: dict[str, float],
    threshold: float,
) -> tuple[bool, list[str]]:
    new_misses = [
        case["case_id"]
        for case in regression_cases
        if old_scores.get(case["case_id"], 0.0) >= threshold
        and new_scores.get(case["case_id"], 0.0) < threshold
    ]
    return not new_misses, new_misses


@dataclass(frozen=True)
class Incident:
    incident_id: str
    capability: str
    trigger_event_id: str


@dataclass
class EvidenceBundle:
    kill_switch: list[str]
    revoked_credentials: list[str]
    evidence: dict[str, Any]
    blast_radius: dict[str, list[str]]
    regression_case: dict[str, Any]
    bundle_hash: str = ""

    def calculate_hash(self) -> str:
        payload = {
            "kill_switch": self.kill_switch,
            "revoked_credentials": self.revoked_credentials,
            "evidence": self.evidence,
            "blast_radius": self.blast_radius,
            "regression_case": self.regression_case,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def verify(self) -> bool:
        return self.bundle_hash == self.calculate_hash()


def bundle_hash(bundle: EvidenceBundle) -> str:
    return bundle.calculate_hash()


def respond(
    incident: Incident,
    state: AuthorizationState,
    audit_log: AuditLog,
    manifest: list[ArtifactManifest],
    policy_version: str,
    detector_version: str,
) -> EvidenceBundle:
    state.disabled_capabilities.add(incident.capability)
    state.revoked_credentials.append(f"credential:{incident.capability}")
    matching = [
        event for event in audit_log.events if event.get("capability") == incident.capability
    ]
    tenants = sorted({event["tenant"] for event in matching if "tenant" in event})
    users = sorted({event["user_id"] for event in matching if "user_id" in event})
    side_effects = [
        event["event_id"] for event in matching if event.get("side_effect")
    ]
    regression_case = {
        "case_id": f"{incident.incident_id}-regression",
        "capability": incident.capability,
        "expected": Decision.BLOCK.value,
    }
    bundle = EvidenceBundle(
        kill_switch=[incident.capability],
        revoked_credentials=list(state.revoked_credentials),
        evidence={
            "trace_ids": [event["event_id"] for event in matching],
            "trigger_event_id": incident.trigger_event_id,
            "policy_version": policy_version,
            "detector_version": detector_version,
            "artifact_hashes": {entry.name: entry.sha256 for entry in manifest},
            "audit_log_head_hash": audit_log.head_hash(),
        },
        blast_radius={
            "tenants": tenants,
            "users": users,
            "side_effects": side_effects,
        },
        regression_case=regression_case,
    )
    bundle.bundle_hash = bundle.calculate_hash()
    return bundle


@dataclass(frozen=True)
class EvaluationSet:
    name: str
    synthetic: bool
    access_roles: list[str]
    retention_days: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvaluationSet":
        return cls(**value)


def check_eval_access(session: Session, evalset: EvaluationSet) -> bool:
    return evalset.synthetic and session.role in evalset.access_roles
