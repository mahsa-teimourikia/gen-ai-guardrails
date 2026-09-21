import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).parents[1]
COURSE = ROOT / "curriculum/advanced/04-state-of-the-art-stack"
spec = importlib.util.spec_from_file_location("stack_lab", COURSE / "stack_lab.py")
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


def fixture(name: str):
    return json.loads((COURSE / "fixtures" / name).read_text(encoding="utf-8"))


def policy(**changes):
    values = {
        "injection_threshold": 0.8,
        "content_threshold": 0.8,
        "transform_pii": True,
        "fail_closed_for": {"write"},
        "version": "support-guardrails/3.2",
    }
    values.update(changes)
    return lab.Policy(**values)


def test_selector_builds_a_valid_provider_neutral_stack():
    catalog = lab.load_catalog(COURSE / "fixtures/tool_catalog.json")
    scenario = lab.Scenario.model_validate(fixture("scenario.json"))
    selected = lab.select_stack(catalog, scenario)
    plan = lab.StackPlan(selected=selected, scenario=scenario)
    assert {tool.kind for tool in plan.selected} >= {
        "application_control",
        "runtime_framework",
        "evaluation",
        "observability",
    }
    assert any(tool.tool_id == "application-policy-and-authz" for tool in plan.selected)
    assert all(tool.provider_scope != "provider_native" for tool in plan.selected)


def test_a_detector_only_stack_cannot_claim_authorization_coverage():
    catalog = lab.load_catalog(COURSE / "fixtures/tool_catalog.json")
    scenario = lab.Scenario(
        name="write assistant",
        required_capabilities={"prompt_injection"},
        required_kinds={"runtime_framework"},
        allowed_deployment={"self_hosted", "hybrid"},
    )
    nemo = next(tool for tool in catalog if tool.tool_id == "nemo-guardrails")
    with pytest.raises(ValidationError, match="application-owned authorization"):
        lab.StackPlan(selected=[nemo], scenario=scenario)


def test_stack_plan_rejects_missing_capabilities_and_deployment_mismatch():
    catalog = lab.load_catalog(COURSE / "fixtures/tool_catalog.json")
    scenario = lab.Scenario.model_validate(fixture("scenario.json"))
    pydantic_tool = next(tool for tool in catalog if tool.tool_id == "pydantic")
    with pytest.raises(ValidationError, match="missing capabilities"):
        lab.StackPlan(selected=[pydantic_tool], scenario=scenario)

    managed = next(tool for tool in catalog if tool.tool_id == "managed-runtime-guardrail")
    self_hosted = scenario.model_copy(update={"allowed_deployment": {"self_hosted"}})
    with pytest.raises(ValidationError, match="deployment constraint"):
        lab.StackPlan(
            selected=[*lab.select_stack(catalog, self_hosted), managed],
            scenario=self_hosted,
        )


@pytest.mark.parametrize(
    ("source", "raw", "check", "flagged"),
    [
        (
            "openai_guardrails",
            {"guardrail_name": "prompt_injection", "tripwire_triggered": True, "score": 0.9},
            "prompt_injection",
            True,
        ),
        (
            "nemo",
            {"rail": "pii", "status": "allowed", "confidence": 0.1},
            "pii",
            False,
        ),
        (
            "managed_service",
            {"category": "content_safety", "action": "BLOCKED", "confidence": 0.8},
            "content_safety",
            True,
        ),
    ],
)
def test_adapters_normalize_incompatible_responses(source, raw, check, flagged):
    signal = lab.normalize_response(source, raw)
    assert signal.check == check
    assert signal.flagged is flagged


def test_policy_composes_block_escalate_transform_and_allow():
    cases = fixture("evaluation_cases.json")
    outcomes = []
    for case in cases:
        signals = [lab.normalize_response(item["source"], item["response"]) for item in case["signals"]]
        outcomes.append(lab.decide(signals, policy(), case["operation"]))
    assert [item.decision.value for item in outcomes] == [case["expected"] for case in cases]
    assert outcomes[4].degraded is True
    assert outcomes[5].reason_codes == ["dependency_unavailable:managed_service"]


def test_evaluation_exposes_denominators_and_passes_release_gate():
    metrics = lab.evaluate(fixture("evaluation_cases.json"), policy())
    assert metrics["exact_matches"] == metrics["cases"] == 6
    assert metrics["false_negatives"] == {"value": 0, "denominator": 3}
    assert metrics["false_positives"] == {"value": 0, "denominator": 3}
    assert lab.release_gate(metrics) == (True, [])


def test_threshold_regression_blocks_release():
    metrics = lab.evaluate(
        fixture("evaluation_cases.json"),
        policy(injection_threshold=0.99),
    )
    passed, failures = lab.release_gate(metrics)
    assert passed is False
    assert set(failures) == {"false_negatives", "decision_mismatch"}


def test_trace_is_semantic_and_privacy_minimized():
    outcome = lab.Outcome(
        decision=lab.Decision.BLOCK,
        reason_codes=["prompt_injection"],
        policy_version="support-guardrails/3.2",
    )
    event = lab.trace_event(outcome, "trace-synthetic-42")
    assert event["openinference.span.kind"] == "GUARDRAIL"
    assert event["guardrail.decision"] == "block"
    assert "prompt" not in event
    assert "response" not in event


def test_policy_rejects_invalid_thresholds():
    with pytest.raises(ValidationError):
        policy(injection_threshold=1.5)
