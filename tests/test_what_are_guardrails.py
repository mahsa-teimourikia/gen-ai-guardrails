import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "curriculum/beginner/01-what-are-guardrails/guardrails_lab.py"
FIXTURE_DIR = MODULE_PATH.parent / "fixtures"
spec = importlib.util.spec_from_file_location("what_are_guardrails_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


REQUESTS = json.loads((FIXTURE_DIR / "requests.json").read_text(encoding="utf-8"))
KB = [lab.Document(**item) for item in json.loads((FIXTURE_DIR / "kb.json").read_text(encoding="utf-8"))]


@pytest.mark.parametrize("case", REQUESTS, ids=lambda case: case["id"])
def test_fixture_request_matches_labeled_outcome(case):
    identity = lab.Identity(**case["identity"])
    result = lab.run_pipeline(case, identity, lab.default_policies(), KB, lab.Ledger())
    assert result.terminal.value == case["expected_decision"]
    assert result.deciding_rail == case["expected_rail"]


def test_fail_open_detector_outage_allows_with_audit_reason():
    identity = lab.Identity("user-2001", "employee", "bu-north", True)
    detectors = dict(lab.DEFAULT_DETECTORS)
    detectors["topic_classifier"] = lab.failing_detector
    record = lab.guard_input("How do I request help?", identity, lab.default_policies(), detectors)
    assert record.decision is lab.Decision.ALLOW
    assert record.reasons == ["detector_unavailable"]
    assert record.metadata["audit_event"] == "detector_unavailable"


def test_fail_closed_write_path_detector_outage_blocks():
    identity = lab.Identity("user-2002", "employee", "bu-north", True)
    call = lab.ToolCall("issue_payroll_adjustment", {"employee_id": "user-2002", "amount": 25})
    record = lab.guard_tool_call(
        identity,
        call,
        lab.default_policies(),
        {"authorization": lab.failing_detector},
    )
    assert record.decision is lab.Decision.BLOCK
    assert record.reasons == ["detector_unavailable"]


def test_misordered_pipeline_leaves_side_effect():
    request = next(item for item in REQUESTS if item["id"] == "req-05")
    identity = lab.Identity(**request["identity"])
    safe_ledger = lab.Ledger()
    lab.run_pipeline(request, identity, lab.default_policies(), KB, safe_ledger)
    unsafe_ledger = lab.Ledger()
    lab.run_pipeline(request, identity, lab.default_policies(), KB, unsafe_ledger, misordered=True)
    assert safe_ledger.entries == []
    assert unsafe_ledger.entries[0]["tool"] == "issue_payroll_adjustment"


def test_decision_record_is_audit_safe():
    record = lab.DecisionRecord(
        rail="execution",
        policy_id="tool-authorization",
        decision=lab.Decision.BLOCK,
        reasons=["write_not_authorized"],
        identity_hash=hashlib.sha256(b"user-1005").hexdigest(),
        correlation_id="correlation-1",
        detector_version="deterministic-v1",
        metadata={},
    )
    payload = json.loads(record.to_json())
    assert set(payload) == {
        "rail",
        "policy_id",
        "decision",
        "reasons",
        "identity_hash",
        "correlation_id",
        "detector_version",
        "metadata",
    }
    serialized = record.to_json()
    assert "user-1005" not in serialized
    assert "user_id" not in serialized
    assert "user-1042@example.test" not in serialized


def test_decision_enum_has_exactly_five_members():
    assert list(lab.Decision) == [
        lab.Decision.ALLOW,
        lab.Decision.TRANSFORM,
        lab.Decision.BLOCK,
        lab.Decision.ABSTAIN,
        lab.Decision.ESCALATE,
    ]
