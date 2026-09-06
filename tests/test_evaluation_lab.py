import importlib.util
import json
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "curriculum/advanced/01-evaluation-and-red-teaming/evaluation_lab.py"
FIXTURE_DIR = MODULE_PATH.parent / "fixtures"
spec = importlib.util.spec_from_file_location("evaluation_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


def fixture(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


CASES = [lab.TestCase.from_dict(item) for item in fixture("cases.json")]
POLICY_V1 = lab.Policy.from_dict(fixture("policy_v1.json"))
POLICY_V2 = lab.Policy.from_dict(fixture("policy_v2.json"))
V1_RESULTS = [lab.guard(case, POLICY_V1) for case in CASES]
V2_RESULTS = [lab.guard(case, POLICY_V2) for case in CASES]


def test_decision_has_exactly_five_members_and_taxonomy_has_adversarial_coverage():
    assert len(lab.Decision) == 5
    required = [
        "direct_jailbreak",
        "indirect_injection",
        "cross_tenant",
        "pii",
        "tool_misuse",
        "allowed",
        "borderline",
        "long_input",
        "multilingual",
        "detector_outage",
    ]
    assert lab.coverage_gaps(CASES, required) == []


def test_confusion_exposes_hand_computed_rates_and_zero_denominators():
    mini = [
        lab.TestCase("allow", lab.Suite.GOLDEN, "allowed", "input", "bu-north", "en", "low", {}, lab.Decision.ALLOW, {}, {}),
        lab.TestCase("block", lab.Suite.GOLDEN, "pii", "output", "bu-north", "en", "high", {}, lab.Decision.BLOCK, {}, {}),
        lab.TestCase("miss", lab.Suite.GOLDEN, "pii", "output", "bu-north", "en", "high", {}, lab.Decision.BLOCK, {}, {}),
        lab.TestCase("false", lab.Suite.GOLDEN, "borderline", "input", "bu-north", "en", "low", {}, lab.Decision.ALLOW, {}, {}),
    ]
    results = [
        lab.GuardResult("allow", lab.Decision.ALLOW, ["x"], "v1", 0.1, 1, True, False),
        lab.GuardResult("block", lab.Decision.BLOCK, ["x"], "v1", 0.9, 1, True, False),
        lab.GuardResult("miss", lab.Decision.ALLOW, ["x"], "v1", 0.1, 1, True, False),
        lab.GuardResult("false", lab.Decision.BLOCK, ["x"], "v1", 0.7, 1, True, False),
    ]
    metrics = lab.confusion(mini, results)
    assert (metrics["tp"], metrics["fp"], metrics["fn"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["precision"] == {"value": 0.5, "numerator": 1, "denominator": 2}
    zero = lab.confusion(
        [mini[0]],
        [lab.GuardResult("allow", lab.Decision.ALLOW, ["x"], "v1", 0.1, 1, True, False)],
    )
    assert zero["recall"] == {"value": None, "numerator": 0, "denominator": 0}


def test_slices_and_security_distinguish_blocked_attempts_from_actions():
    slices = lab.slice_metrics(CASES, V1_RESULTS, "language")
    assert set(slices) >= {"en", "de", "fr"}
    blocked = lab.TestCase("blocked", lab.Suite.ADVERSARIAL, "tool_misuse", "tool", "bu-north", "en", "high", {}, lab.Decision.BLOCK, {}, {})
    action = replace(blocked, case_id="action")
    results = [
        lab.GuardResult("blocked", lab.Decision.BLOCK, ["rule"], "v1", None, 1, True, False),
        lab.GuardResult("action", lab.Decision.ALLOW, ["detector_unavailable_fail_open"], "v1", None, 1, True, True),
    ]
    metrics = lab.security_metrics([blocked, action], results)
    assert metrics == {"blocked_attempts": 1, "unauthorized_actions": 1}


def test_guard_rules_precede_detector_and_v1_bypass_set_is_known():
    expected_bypasses = {"direct-1", "indirect-1"}
    actual = {
        case.case_id
        for case, result in zip(CASES, V1_RESULTS)
        if case.expected is lab.Decision.BLOCK and result.decision is lab.Decision.ALLOW
    }
    assert actual == expected_bypasses
    assert lab.guard(next(case for case in CASES if case.case_id == "cross-1"), POLICY_V1).reason_codes == ["cross_tenant"]
    assert lab.guard(next(case for case in CASES if case.case_id == "tool-1"), POLICY_V1).reason_codes == ["role_not_authorized"]
    assert lab.guard(next(case for case in CASES if case.case_id == "direct-1"), POLICY_V2).decision is lab.Decision.BLOCK
    assert lab.guard(next(case for case in CASES if case.case_id == "indirect-1"), POLICY_V2).decision is lab.Decision.BLOCK
    assert lab.guard(next(case for case in CASES if case.case_id == "border-1"), POLICY_V2).decision is lab.Decision.BLOCK
    assert lab.guard(next(case for case in CASES if case.case_id == "multi-1"), POLICY_V1).decision is lab.Decision.BLOCK
    assert lab.guard(next(case for case in CASES if case.case_id == "multi-1"), POLICY_V2).decision is lab.Decision.ALLOW


def test_ops_metrics_uses_nearest_rank_and_tracks_outages():
    metrics = lab.ops_metrics(V1_RESULTS)
    assert metrics["p50_latency_ms"] == 82
    assert metrics["p95_latency_ms"] == 151
    assert metrics["detector_unavailable_rate"] == pytest.approx(3 / 36)


def test_grader_hierarchy_and_judge_calibration():
    tool_case = next(case for case in CASES if case.case_id == "tool-1")
    assert lab.grade(tool_case, next(result for result in V1_RESULTS if result.case_id == "tool-1"))[0] is lab.Grader.STATE
    rule_case = next(case for case in CASES if case.case_id == "cross-1")
    rule_result = next(result for result in V1_RESULTS if result.case_id == "cross-1")
    assert lab.grade(rule_case, rule_result)[0] is lab.Grader.RULE
    judge_case = next(case for case in CASES if case.case_id == "pii-1")
    judge_result = next(result for result in V1_RESULTS if result.case_id == "pii-1")
    assert lab.grade(judge_case, judge_result, {"pii-1": lab.Decision.BLOCK})[0] is lab.Grader.JUDGE
    assert lab.cohens_kappa(["a", "a", "b"], ["a", "b", "b"]) == pytest.approx(0.4)
    judge = {key: lab.Decision(value) for key, value in fixture("judge_labels.json").items()}
    human = {key: lab.Decision(value) for key, value in fixture("human_labels.json").items()}
    calibration = lab.calibrate_judge(judge, human)
    assert calibration["n"] == 12
    assert calibration["trusted"] is True
    assert 0.6 <= calibration["kappa"] <= 0.9


def test_red_team_requires_authorization_and_creates_regressions():
    authorization = lab.Authorization.from_dict(fixture("authorization.json"))
    findings = lab.run_red_team(CASES, POLICY_V1, authorization, date(2026, 9, 6))
    assert findings
    regression = lab.to_regression_case(findings[0], next(case for case in CASES if case.case_id == findings[0].case_id))
    assert regression.suite is lab.Suite.GOLDEN
    assert regression.case_id.endswith("-regression")
    with pytest.raises(lab.RedTeamNotAuthorized):
        lab.run_red_team(CASES, POLICY_V1, replace(authorization, scope_env="production"), date(2026, 9, 6))
    with pytest.raises(lab.RedTeamNotAuthorized):
        lab.run_red_team(CASES, POLICY_V1, lab.Authorization.from_dict(fixture("authorization_expired.json")), date(2026, 9, 6))
    with pytest.raises(lab.RedTeamNotAuthorized):
        lab.run_red_team(CASES, POLICY_V1, replace(authorization, allowed_families=["direct_jailbreak"]), date(2026, 9, 6))


def test_threshold_sweep_selects_loss_over_accuracy():
    sweep = lab.sweep_thresholds(CASES, POLICY_V2, [0.4, 0.5, 0.6, 0.7], fixture("costs.json"))
    assert max(sweep, key=lambda row: row["accuracy"])["threshold"] != lab.select_threshold(sweep)
    assert lab.select_threshold(sweep) == 0.5


def test_shadow_and_canary_show_candidate_disagreements_on_slice():
    disagreements = lab.shadow_compare(CASES, POLICY_V1, POLICY_V2)
    assert disagreements
    assert all({"case_id", "current", "candidate", "expected"} <= set(row) for row in disagreements)
    results = lab.canary_results(CASES, POLICY_V1, POLICY_V2, "tenant", "bu-south")
    assert results
    for case, result in zip(CASES, results):
        expected = lab.guard(case, POLICY_V2 if case.tenant == "bu-south" else POLICY_V1)
        assert result.decision is expected.decision


def test_release_gate_fails_candidate_then_passes_after_threshold_and_trace_remediation():
    envelope = fixture("envelope.json")
    failed = lab.release_gate(CASES, V1_RESULTS, V2_RESULTS, envelope)
    assert not lab.release_gate_passes(failed)
    assert any(not passed for _, passed, _ in failed)
    assert any(name == "output correctness (schema/groundedness proxy)" for name, _, _ in failed)
    selected = replace(POLICY_V2, threshold=0.5)
    repaired_cases = [
        replace(case, request={**case.request, "trace_dropped": False})
        if case.case_id == "outage-3" else case
        for case in CASES
    ]
    selected_results = [lab.guard(case, selected) for case in repaired_cases]
    passed = lab.release_gate(repaired_cases, V1_RESULTS, selected_results, envelope)
    assert lab.release_gate_passes(passed)
