"""Offline lab for selecting and composing a production guardrail stack.

The vendor responses are frozen fixtures.  The lab deliberately separates
product-specific adapters from application-owned policy so learners can replace
a detector without silently changing authorization or failure behaviour.
"""

from __future__ import annotations

from collections import Counter
from enum import Enum
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    BLOCK = "block"
    ESCALATE = "escalate"


class Tool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str
    kind: Literal[
        "application_control",
        "runtime_framework",
        "specialist_detector",
        "managed_service",
        "evaluation",
        "observability",
    ]
    capabilities: set[str]
    deployment: set[Literal["self_hosted", "managed", "hybrid"]]
    provider_scope: Literal["provider_neutral", "provider_native", "mixed"]
    evidence: str
    as_of: str


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    required_capabilities: set[str]
    required_kinds: set[str]
    allowed_deployment: set[str]
    require_provider_neutral: bool = False


class StackPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected: list[Tool]
    scenario: Scenario

    @model_validator(mode="after")
    def validate_coverage(self) -> "StackPlan":
        capabilities = set().union(*(tool.capabilities for tool in self.selected))
        kinds = {tool.kind for tool in self.selected}
        missing = self.scenario.required_capabilities - capabilities
        if missing:
            raise ValueError(f"missing capabilities: {', '.join(sorted(missing))}")
        missing_kinds = self.scenario.required_kinds - kinds
        if missing_kinds:
            raise ValueError(f"missing tool kinds: {', '.join(sorted(missing_kinds))}")
        if not any(tool.kind == "application_control" for tool in self.selected):
            raise ValueError("application-owned authorization is required")
        if self.scenario.require_provider_neutral and not any(
            tool.provider_scope == "provider_neutral" for tool in self.selected
        ):
            raise ValueError("a provider-neutral control is required")
        for tool in self.selected:
            if not tool.deployment & self.scenario.allowed_deployment:
                raise ValueError(f"{tool.tool_id} violates the deployment constraint")
        return self


class GuardSignal(BaseModel):
    """Stable application contract for otherwise incompatible SDK responses."""

    model_config = ConfigDict(extra="forbid")

    source: str
    check: Literal["content_safety", "prompt_injection", "pii"]
    flagged: bool
    score: float = Field(ge=0.0, le=1.0)
    available: bool = True
    reason_code: str


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    injection_threshold: float = Field(ge=0.0, le=1.0)
    content_threshold: float = Field(ge=0.0, le=1.0)
    transform_pii: bool
    fail_closed_for: set[Literal["read", "write"]]
    version: str


class Outcome(BaseModel):
    decision: Decision
    reason_codes: list[str]
    policy_version: str
    degraded: bool = False


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_catalog(path: str | Path) -> list[Tool]:
    return [Tool.model_validate(item) for item in load_json(path)]


def select_stack(catalog: list[Tool], scenario: Scenario) -> list[Tool]:
    """Greedy, explainable baseline; not a procurement recommendation."""
    eligible = [
        tool
        for tool in catalog
        if tool.deployment & scenario.allowed_deployment
        and (not scenario.require_provider_neutral or tool.provider_scope != "provider_native")
    ]
    uncovered = set(scenario.required_capabilities)
    missing_kinds = set(scenario.required_kinds)
    selected: list[Tool] = []
    while uncovered or missing_kinds:
        candidates = [tool for tool in eligible if tool not in selected]
        if not candidates:
            break
        best = max(
            candidates,
            key=lambda tool: (
                len(tool.capabilities & uncovered) + (tool.kind in missing_kinds),
                tool.kind == "application_control",
                tool.provider_scope == "provider_neutral",
                tool.tool_id,
            ),
        )
        gain = len(best.capabilities & uncovered) + (best.kind in missing_kinds)
        if gain == 0:
            break
        selected.append(best)
        uncovered -= best.capabilities
        missing_kinds.discard(best.kind)
    return selected


def normalize_response(source: str, raw: dict[str, Any]) -> GuardSignal:
    """Normalize three representative SDK/service response shapes."""
    if source == "openai_guardrails":
        return GuardSignal(
            source=source,
            check=raw["guardrail_name"],
            flagged=raw["tripwire_triggered"],
            score=raw.get("score", 1.0 if raw["tripwire_triggered"] else 0.0),
            available=not raw.get("error"),
            reason_code=raw.get("reason", "tripwire"),
        )
    if source == "nemo":
        return GuardSignal(
            source=source,
            check=raw["rail"],
            flagged=raw["status"] == "blocked",
            score=raw.get("confidence", 1.0 if raw["status"] == "blocked" else 0.0),
            available=raw["status"] != "error",
            reason_code=raw.get("reason", raw["status"]),
        )
    if source == "managed_service":
        return GuardSignal(
            source=source,
            check=raw["category"],
            flagged=raw["action"] == "BLOCKED",
            score=raw.get("confidence", 0.0),
            available=raw["action"] != "ERROR",
            reason_code=raw.get("code", raw["action"].lower()),
        )
    raise ValueError(f"unsupported adapter: {source}")


def decide(signals: list[GuardSignal], policy: Policy, operation: Literal["read", "write"]) -> Outcome:
    unavailable = [signal for signal in signals if not signal.available]
    if unavailable and operation in policy.fail_closed_for:
        return Outcome(
            decision=Decision.BLOCK,
            reason_codes=[f"dependency_unavailable:{signal.source}" for signal in unavailable],
            policy_version=policy.version,
            degraded=True,
        )

    available = [signal for signal in signals if signal.available]
    if any(
        signal.check == "prompt_injection"
        and signal.flagged
        and signal.score >= policy.injection_threshold
        for signal in available
    ):
        return Outcome(
            decision=Decision.BLOCK,
            reason_codes=["prompt_injection"],
            policy_version=policy.version,
            degraded=bool(unavailable),
        )
    if any(
        signal.check == "content_safety"
        and signal.flagged
        and signal.score >= policy.content_threshold
        for signal in available
    ):
        return Outcome(
            decision=Decision.ESCALATE,
            reason_codes=["content_safety"],
            policy_version=policy.version,
            degraded=bool(unavailable),
        )
    if policy.transform_pii and any(
        signal.check == "pii" and signal.flagged for signal in available
    ):
        return Outcome(
            decision=Decision.TRANSFORM,
            reason_codes=["pii_redaction_required"],
            policy_version=policy.version,
            degraded=bool(unavailable),
        )
    return Outcome(
        decision=Decision.ALLOW,
        reason_codes=["checks_passed"] if not unavailable else ["degraded_read_only"],
        policy_version=policy.version,
        degraded=bool(unavailable),
    )


def evaluate(cases: list[dict[str, Any]], policy: Policy) -> dict[str, Any]:
    results = []
    for case in cases:
        signals = [normalize_response(item["source"], item["response"]) for item in case["signals"]]
        outcome = decide(signals, policy, case["operation"])
        results.append((case, outcome))

    counts = Counter((case["expected"], outcome.decision.value) for case, outcome in results)
    harmful = {"block", "escalate"}
    expected_harmful = sum(case["expected"] in harmful for case, _ in results)
    expected_safe = len(results) - expected_harmful
    false_negatives = sum(
        case["expected"] in harmful and outcome.decision.value not in harmful
        for case, outcome in results
    )
    false_positives = sum(
        case["expected"] not in harmful and outcome.decision.value in harmful
        for case, outcome in results
    )
    return {
        "cases": len(results),
        "exact_matches": sum(case["expected"] == outcome.decision.value for case, outcome in results),
        "false_negatives": {"value": false_negatives, "denominator": expected_harmful},
        "false_positives": {"value": false_positives, "denominator": expected_safe},
        "degraded_cases": sum(outcome.degraded for _, outcome in results),
        "confusion": {f"{expected}->{actual}": count for (expected, actual), count in counts.items()},
    }


def release_gate(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if metrics["false_negatives"]["value"]:
        failures.append("false_negatives")
    if metrics["exact_matches"] != metrics["cases"]:
        failures.append("decision_mismatch")
    if metrics["degraded_cases"] > 2:
        failures.append("dependency_reliability")
    return not failures, failures


def trace_event(outcome: Outcome, trace_id: str) -> dict[str, Any]:
    """Privacy-minimized attributes compatible with an AI guardrail span."""
    return {
        "trace_id": trace_id,
        "openinference.span.kind": "GUARDRAIL",
        "guardrail.decision": outcome.decision.value,
        "guardrail.policy.version": outcome.policy_version,
        "guardrail.reason_codes": outcome.reason_codes,
        "guardrail.degraded": outcome.degraded,
    }
