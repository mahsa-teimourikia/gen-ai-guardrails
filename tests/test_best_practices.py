import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "curriculum/intermediate/01-best-practices/best_practices_lab.py"
FIXTURE_DIR = MODULE_PATH.parent / "fixtures"
spec = importlib.util.spec_from_file_location("best_practices_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


def fixture(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_risk_register_reports_unaccepted_residual_risk():
    entries = lab.load_risk_register(FIXTURE_DIR / "risk_register.json")
    issues = lab.validate_risk_register(entries, appetite=2)
    assert any("risk-unreviewed-threshold" in issue for issue in issues)
    assert any("residual risk" in issue for issue in issues)


def test_misplaced_controls_flags_prompt_authorization_and_limits():
    mappings = [
        lab.ControlMapping("check identity", "identity", "prompt"),
        lab.ControlMapping("authorize payroll", "authorization", "prompt"),
        lab.ControlMapping("limit tool calls", "limit", "app"),
        lab.ControlMapping("redact output", "content", "prompt"),
    ]
    assert [mapping.statement for mapping in lab.misplaced_controls(mappings)] == [
        "check identity",
        "authorize payroll",
    ]


def test_budget_raises_when_a_kind_is_exhausted():
    budget = lab.Budget(max_tool_calls=1, max_retries=2, max_tokens=10)
    budget.consume("tool_calls")
    with pytest.raises(lab.BudgetExceeded) as error:
        budget.consume("tool_calls")
    assert error.value.kind == "tool_calls"


def test_breaker_opens_and_fails_closed_only_for_irreversible_tools():
    breaker = lab.CircuitBreaker(failure_threshold=3)

    def unavailable(_: str) -> float:
        raise RuntimeError("detector unavailable")

    for _ in range(3):
        outcome = lab.guarded_detector_call(breaker, unavailable, "request", True)
        assert outcome.decision is lab.Decision.BLOCK
    assert breaker.is_open
    read_outcome = lab.guarded_detector_call(breaker, unavailable, "request", False)
    assert read_outcome.decision is lab.Decision.ALLOW
    assert read_outcome.reason_codes == ["detector_unavailable"]


def test_successful_detector_call_resets_failures_and_scores():
    breaker = lab.CircuitBreaker(failure_threshold=3)
    breaker.record_failure()
    outcome = lab.guarded_detector_call(breaker, lambda _: 0.8, "request", True)
    assert outcome.decision is lab.Decision.BLOCK
    assert outcome.reason_codes == ["detector_threshold"]
    assert not breaker.is_open


def test_change_review_covers_safety_and_non_safety_paths():
    changes = [lab.ChangeRequest(**row) for row in fixture("change_requests.json")]
    outcomes = [lab.review_change(change) for change in changes]
    assert outcomes[0].reason_codes == ["self_review"]
    assert outcomes[1].reason_codes == ["missing_reviewer"]
    assert outcomes[2].reason_codes == ["reviewer_not_authorized"]
    assert outcomes[3].decision is lab.Decision.ALLOW
    assert lab.review_change(
        lab.ChangeRequest("copy-1", "prompt_copy", "analyst-a", None, None)
    ).reason_codes == ["not_safety_critical"]


def test_layered_evaluation_blocks_adversarial_regression_despite_benchmark():
    data = fixture("evaluation_layers.json")
    layers = [lab.LayerResult(**row) for row in data["layers"]]
    outcome = lab.layered_release_decision(layers, data["benchmark_score"])
    assert outcome.decision is lab.Decision.BLOCK
    assert "benchmark=0.97" in outcome.reason_codes
    assert "layer_failed:adversarial" in outcome.reason_codes


def test_layered_evaluation_requires_all_layers():
    outcome = lab.layered_release_decision(
        [lab.LayerResult("unit", True, "pass")],
        0.97,
    )
    assert outcome.decision is lab.Decision.BLOCK
    assert "missing_layer:monitoring" in outcome.reason_codes

    all_pass = [
        lab.LayerResult(name, True, "pass")
        for name in ("unit", "component", "end_to_end", "adversarial", "monitoring")
    ]
    assert lab.layered_release_decision(all_pass, 0.97).decision is lab.Decision.ALLOW


def test_review_packet_rejects_context_free_approval():
    packet = lab.ReviewPacket({}, [], "", "", "")
    issues = lab.validate_packet(packet)
    assert len(issues) == 5
    complete = lab.ReviewPacket(
        {"tool": "issue_payroll_adjustment"},
        ["decision-42"],
        "detector score is below threshold",
        "payroll state could change",
        "reverse operation-42",
    )
    assert lab.validate_packet(complete) == []


def test_release_gate_passes_and_fails_on_exact_manifest_items():
    layers = [
        lab.LayerResult(name, True, "pass")
        for name in ("unit", "component", "end_to_end", "adversarial", "monitoring")
    ]
    layer_outcome = lab.layered_release_decision(layers, 0.97)
    gate = lab.ReleaseGate()

    passing = gate.evaluate(fixture("manifest_pass.json"), [], layer_outcome)
    assert lab.gate_passed(passing)

    failing = gate.evaluate(fixture("manifest_fail.json"), [], layer_outcome)
    failed_items = {item.item for item in failing if not item.passed}
    assert failed_items == {
        "authorization enforced outside the model",
        "false-positive and false-negative datasets exist",
        "incident response and appeal paths are tested",
    }


def test_decision_enum_has_exactly_five_members():
    assert list(lab.Decision) == [
        lab.Decision.ALLOW,
        lab.Decision.TRANSFORM,
        lab.Decision.BLOCK,
        lab.Decision.ABSTAIN,
        lab.Decision.ESCALATE,
    ]
