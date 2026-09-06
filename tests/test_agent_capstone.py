import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
COURSE = ROOT / "curriculum/advanced/03-agent-tool-capstone"
spec = importlib.util.spec_from_file_location("agent_capstone_lab", COURSE / "capstone_lab.py")
lab = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


def load(name):
    return json.loads((COURSE / "fixtures" / name).read_text())


SESSIONS = [lab.Session.from_dict(item) for item in load("sessions.json")]
CAPABILITIES = {
    item["tool"]: lab.Capability.from_dict(item) for item in load("capabilities.json")
}
TRAJECTORIES = load("trajectories.json")
OUTPUTS = load("tool_outputs.json")
EXPECTED = load("expected_terminals.json")
APPROVALS = {
    item["approval_id"]: lab.Approval.from_dict(item) for item in load("approvals.json")
}


def state():
    value = load("state.json")
    value["approvals"] = {item["approval_id"]: item for item in load("approvals.json") if item["approval_id"] in {
        "approve-create-1",
        "approve-group-1",
        "approve-order-1",
        "approve-email-1",
        "approve-reconcile",
    }}
    return lab.AuthorizationState.from_dict(value)


def budget(name="default"):
    value = load("budget.json")[name]
    return lab.Budget(**value)


def run(item, session=SESSIONS[0], current=None):
    if "session_id" in item:
        session = next(candidate for candidate in SESSIONS if candidate.session_id == item["session_id"])
    return lab.run_trajectory(
        item,
        session,
        current or state(),
        CAPABILITIES,
        budget(item["trajectory_id"] if item["trajectory_id"] == "T3" else "default"),
        OUTPUTS,
    )


def test_decision_and_terminal_enums_are_exact():
    assert len(lab.Decision) == 5
    assert len(lab.Terminal) == 6


def test_exposure_is_phase_and_role_scoped():
    employee = SESSIONS[2]
    assert set(lab.exposed_capabilities(employee, state(), "lookup", CAPABILITIES)) == {"read_employee"}
    assert "create_account" not in lab.exposed_capabilities(SESSIONS[0], state(), "lookup", CAPABILITIES)
    assert "create_account" in lab.exposed_capabilities(SESSIONS[0], state(), "provision", CAPABILITIES)


def test_all_frozen_trajectories_have_expected_terminals():
    results = [run(item) for item in TRAJECTORIES]
    assert [result.terminal.value for result in results] == [EXPECTED[item["trajectory_id"]] for item in TRAJECTORIES]
    assert all(result.unauthorized_actions == 0 for result in results)


def test_missing_approval_can_be_added_and_re_evaluated():
    current = state()
    first = run(TRAJECTORIES[1], current=current)
    assert first.terminal is lab.Terminal.APPROVAL_REQUIRED
    pending = first.decisions[-1].pending_fingerprint
    current.approvals["approve-t2"] = lab.Approval(
        "approve-t2", pending, "hr_bri", "hr_admin", "bu-north", lab.date(2027, 1, 1)
    )
    second = run(TRAJECTORIES[1], current=current)
    assert second.terminal is lab.Terminal.COMPLETED


def test_self_and_expired_approvals_do_not_authorize_side_effects():
    self_plan = {
        "trajectory_id": "self",
        "steps": [
            {
                "step_id": "self-read",
                "tool": "read_employee",
                "args": {"employee_id": "EMP-10004", "tenant": "bu-north"},
                "source": "plan",
            },
            {
                "step_id": "self-s2",
                "tool": "create_account",
                "args": {"employee_id": "EMP-10004", "tenant": "bu-north"},
                "source": "plan",
            }
        ],
    }
    self_state = state()
    self_state.approvals["self"] = APPROVALS["approve-self"]
    self_result = run(self_plan, current=self_state)
    assert self_result.terminal is lab.Terminal.BLOCKED
    assert self_result.decisions[-1].reason_codes == ["self_approval"]
    plan = {
        "trajectory_id": "expired",
        "steps": [
            {
                "step_id": "expired-read",
                "tool": "read_employee",
                "args": {"employee_id": "EMP-10002", "tenant": "bu-north"},
                "source": "plan",
            },
            {
                "step_id": "expired-s1",
                "tool": "create_account",
                "args": {"employee_id": "EMP-10002", "tenant": "bu-north"},
                "source": "plan",
            }
        ],
    }
    current = state()
    current.approvals = {"expired": APPROVALS["approve-expired"]}
    result = run(plan, current=current)
    assert result.terminal is lab.Terminal.APPROVAL_REQUIRED


def test_replay_does_not_execute_a_second_side_effect():
    result = run(TRAJECTORIES[0])
    replay = next(item for item in result.decisions if item.reason_codes == ["replayed"])
    assert replay.side_effect_executed is False
    assert sum(item.side_effect_executed for item in result.decisions) == 3


def test_injected_tool_output_step_is_blocked_and_loop_is_detected():
    injection = run(TRAJECTORIES[4])
    assert injection.terminal is lab.Terminal.COMPLETED
    assert injection.blocked_attempts == 1
    assert injection.decisions[-1].reason_codes == ["untrusted_step_source"]
    loop = run(TRAJECTORIES[3])
    assert loop.terminal is lab.Terminal.LOOP_DETECTED
    assert loop.decisions[-1].reason_codes == ["loop_detected"]


def test_budget_and_reconciliation_controls():
    exhausted = run(TRAJECTORIES[2])
    assert exhausted.terminal is lab.Terminal.BUDGET_EXHAUSTED
    assert exhausted.decisions[-1].reason_codes == ["spend_exhausted"]
    mismatch = run(TRAJECTORIES[7])
    assert mismatch.terminal is lab.Terminal.RECONCILIATION_REQUIRED
    assert mismatch.decisions[-1].reason_codes == ["reconcile_required"]


def test_reconcile_reports_mutated_resource():
    current = state()
    result = run(TRAJECTORIES[0], current=current)
    current.resources["accounts"]["EMP-10001"]["tenant"] = "bu-south"
    assert any("resource_missing" in item for item in lab.reconcile(current, current.receipts))
    assert result.audit


def test_evaluation_and_capstone_gate_pass_then_fail():
    results = [run(item) for item in TRAJECTORIES]
    evaluation = lab.evaluate(TRAJECTORIES, results, EXPECTED)
    assert evaluation["terminal_accuracy"] == {"value": 1.0, "numerator": 8, "denominator": 8}
    assert evaluation["unauthorized_actions"] == 0
    assert evaluation["audit_complete"] is True
    assert lab.gate_passes(lab.capstone_gate(evaluation, load("envelope.json")))
    broken = copy.deepcopy(evaluation)
    broken["terminal_accuracy"]["value"] = 0.5
    assert not lab.gate_passes(lab.capstone_gate(broken, load("envelope.json")))


def test_every_processed_step_has_an_audit_event():
    for item in TRAJECTORIES:
        result = run(item)
        assert len(result.audit) == len(result.decisions)
        assert all(event["correlation_id"] == item["trajectory_id"] for event in result.audit)
