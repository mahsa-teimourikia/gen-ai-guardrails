from datetime import date
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "curriculum/intermediate/02-scenario-cookbook/cookbook_lab.py"
FIXTURE_DIR = MODULE_PATH.parent / "fixtures"
spec = importlib.util.spec_from_file_location("scenario_cookbook_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


def fixture(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_extraction_candidates_follow_expected_routes():
    policy = fixture("extraction_policy.json")
    for item in fixture("extraction_candidates.json"):
        outcome = lab.route_extraction(item["candidate"], policy, date(2026, 12, 31))
        assert outcome.decision.value == item["expected_decision"], item["id"]
        assert item["expected_reason"] in outcome.reason_codes, item["id"]


def test_extraction_unknown_field_is_schema_invalid():
    item = next(item for item in fixture("extraction_candidates.json") if item["id"] == "claim-unknown-field")
    outcome = lab.route_extraction(item["candidate"], fixture("extraction_policy.json"), date(2026, 12, 31))
    assert outcome.decision is lab.Decision.BLOCK
    assert outcome.reason_codes == ["schema_invalid"]


def test_agent_approval_gate_covers_fixture_outcomes():
    policy = fixture("agent_policy.json")
    actions = fixture("agent_actions.json")
    expected_reasons = {
        "action-read": "approved",
        "action-create": "approved",
        "action-payroll-blocked": "role_not_authorized",
        "action-payroll-approved": "approved",
        "action-payroll-duplicate": "approved",
    }
    for item in actions:
        action = lab.ProposedAction(**item["action"])
        outcome = lab.approve_gate(action, policy)
        assert outcome.decision.value == item["expected_decision"], item["id"]
        assert expected_reasons[item["id"]] in outcome.reason_codes


@pytest.mark.parametrize(
    ("tool", "requester", "approver", "reason", "decision"),
    [
        ("unknown", {"user_id": "u", "role": "employee"}, None, "tool_not_allowed", lab.Decision.BLOCK),
        ("issue_payroll_adjustment", {"user_id": "u", "role": "hr_admin"}, None, "approval_required", lab.Decision.ESCALATE),
        (
            "issue_payroll_adjustment",
            {"user_id": "u", "role": "hr_admin"},
            {"user_id": "u", "role": "hr_admin"},
            "self_approval",
            lab.Decision.BLOCK,
        ),
        (
            "issue_payroll_adjustment",
            {"user_id": "u", "role": "hr_admin"},
            {"user_id": "manager", "role": "manager"},
            "approver_not_authorized",
            lab.Decision.BLOCK,
        ),
    ],
)
def test_agent_approval_negative_paths(tool, requester, approver, reason, decision):
    action = lab.ProposedAction("negative", tool, {}, requester, approver, "negative-key")
    outcome = lab.approve_gate(action, fixture("agent_policy.json"))
    assert outcome.decision is decision
    assert outcome.reason_codes == [reason]


def test_kill_switch_blocks_writes():
    policy = fixture("agent_policy.json")
    policy["kill_switch"] = True
    action = lab.ProposedAction(
        "kill",
        "create_ticket",
        {"title": "test"},
        {"user_id": "u", "role": "employee"},
        None,
        "kill-key",
    )
    assert lab.approve_gate(action, policy).reason_codes == ["kill_switch"]


def test_executor_is_idempotent_and_verifies_reconciliation():
    action = lab.ProposedAction(
        "write",
        "create_ticket",
        {"title": "VPN"},
        {"user_id": "u", "role": "employee"},
        None,
        "write-key",
    )
    executor = lab.Executor(budget_writes=2)
    first = executor.execute(action)
    second = executor.execute(action)
    assert first == second
    assert executor.write_count == 1
    assert executor.verify(first, first["state"]).decision is lab.Decision.ALLOW
    assert executor.verify(first, {"tool": "create_ticket", "title": "different"}).reason_codes == [
        "reconcile_required"
    ]


def test_executor_budget_exceeded():
    executor = lab.Executor(budget_writes=1)
    action = lab.ProposedAction(
        "write",
        "create_ticket",
        {"title": "VPN"},
        {"user_id": "u", "role": "employee"},
        None,
        "budget-key",
    )
    executor.execute(action)
    second = lab.ProposedAction(
        "write-2",
        "create_ticket",
        {"title": "Email"},
        {"user_id": "u", "role": "employee"},
        None,
        "budget-key-2",
    )
    with pytest.raises(lab.BudgetExceeded):
        executor.execute(second)


def test_precheck_reasons():
    policy = fixture("moderation_policy.json")
    base = {"text": "ok", "mime": "text/plain", "tenant_id": "tenant-a", "posts_in_window": 1}
    cases = [
        ({"text": "x" * 501}, "too_large"),
        ({"mime": "image/png"}, "unsupported_type"),
        ({"tenant_id": ""}, "tenant_required"),
        ({"posts_in_window": 11}, "rate_limited"),
    ]
    for update, reason in cases:
        post = {**base, **update}
        assert lab.precheck(post, policy).reason_codes == [reason]


def test_moderation_severity_ordering():
    policy = fixture("moderation_policy.json")
    outcome = lab.classify_outcome(
        {"harassment": 0.5, "confidential_data": 0.0, "spam": 0.9},
        policy["thresholds"],
    )
    assert outcome.decision is lab.Decision.BLOCK
    assert outcome.reason_codes == ["category:block", "category_name:spam"]


def test_moderation_category_metrics_match_fixture():
    counts = lab.evaluate_by_category(fixture("moderation_posts.json"), fixture("moderation_policy.json"))
    assert counts == {
        "harassment": {"tp": 4, "fp": 2, "fn": 1, "tn": 13},
        "confidential_data": {"tp": 2, "fp": 1, "fn": 2, "tn": 15},
        "spam": {"tp": 3, "fp": 2, "fn": 2, "tn": 13},
    }


def test_decision_enum_has_exactly_five_members():
    assert list(lab.Decision) == [
        lab.Decision.ALLOW,
        lab.Decision.TRANSFORM,
        lab.Decision.BLOCK,
        lab.Decision.ABSTAIN,
        lab.Decision.ESCALATE,
    ]
