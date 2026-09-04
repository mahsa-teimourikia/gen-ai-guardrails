import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "curriculum/beginner/02-guardrail-lifecycle/lifecycle_lab.py"
FIXTURE_DIR = MODULE_PATH.parent / "fixtures"
spec = importlib.util.spec_from_file_location("guardrail_lifecycle_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


TRAFFIC = [
    lab.TrafficItem(**item)
    for item in json.loads((FIXTURE_DIR / "traffic.json").read_text(encoding="utf-8"))
]
POLICY_V1 = lab.Policy.from_dict(json.loads((FIXTURE_DIR / "policy_v1.json").read_text(encoding="utf-8")))
POLICY_V2 = lab.Policy.from_dict(json.loads((FIXTURE_DIR / "policy_v2.json").read_text(encoding="utf-8")))
INCIDENT = lab.TrafficItem(
    **json.loads((FIXTURE_DIR / "incident.json").read_text(encoding="utf-8"))
)


def test_v1_enforce_metrics_are_hand_computed():
    metrics, _ = lab.evaluate(TRAFFIC, POLICY_V1, lab.Mode.ENFORCE)
    assert metrics.tp == 5
    assert metrics.fp == 3
    assert metrics.fn == 3
    assert metrics.tn == 19
    assert metrics.tpr == pytest.approx(5 / 8)
    assert metrics.fpr == pytest.approx(3 / 22)
    assert metrics.attempts_blocked == 5
    assert metrics.unsafe_completed == 3
    assert metrics.friction == pytest.approx(3 / 22)


def test_shadow_allows_but_records_would_be_decisions():
    metrics, records = lab.evaluate(TRAFFIC, POLICY_V1, lab.Mode.SHADOW)
    assert all(record.decision is lab.Decision.ALLOW for record in records)
    assert all(record.would_be_decision is not None for record in records)
    assert metrics.tp == 0
    assert metrics.fn == 8
    assert lab.evaluate_would_be(TRAFFIC, POLICY_V1).tp == 5


def test_alert_allows_and_marks_detector_decisions():
    _, records = lab.evaluate(TRAFFIC, POLICY_V1, lab.Mode.ALERT)
    high_score = next(record for record in records if record.request_id == "attack-01")
    low_score = next(record for record in records if record.request_id == "legit-01")
    assert high_score.decision is lab.Decision.ALLOW
    assert high_score.would_be_decision is lab.Decision.BLOCK
    assert "alert_raised" in high_score.reason_codes
    assert low_score.would_be_decision is lab.Decision.ALLOW


def test_boundary_items_count_as_legitimate_for_friction():
    metrics, _ = lab.evaluate(TRAFFIC, POLICY_V1, lab.Mode.ENFORCE)
    assert metrics.fp == 3  # one legitimate and two boundary items
    assert metrics.friction == pytest.approx(3 / 22)


def test_incident_is_missed_by_v1_and_blocked_by_v2_tool_rule():
    _, v1_records = lab.evaluate([INCIDENT], POLICY_V1, lab.Mode.ENFORCE)
    _, v2_records = lab.evaluate([INCIDENT], POLICY_V2, lab.Mode.ENFORCE)
    assert v1_records[0].decision is lab.Decision.ALLOW
    assert v2_records[0].decision is lab.Decision.BLOCK
    assert v2_records[0].reason_codes == ["role_not_authorized"]
    assert v2_records[0].confidence is None


def test_idempotent_receipts_and_verification():
    ledger = lab.Ledger()
    call = {"name": "read_ticket", "arguments": {"ticket_id": "ticket-42"}}
    first = ledger.execute_with_receipt(call, "request-42")
    second = ledger.execute_with_receipt(call, "request-42")
    assert first == second
    assert len(ledger.entries) == 1
    assert ledger.verify(first)


def test_retry_is_capped():
    record = lab.DecisionRecord(
        request_id="retry-01",
        decision=lab.Decision.BLOCK,
        reason_codes=["retryable_error"],
        policy_version=1,
        confidence=None,
        would_be_decision=lab.Decision.BLOCK,
        next_step="offer a policy-compliant alternative",
    )
    assert lab.recover(record, attempt=0) == "retry with a varied strategy"
    assert lab.recover(record, attempt=1) == "retry with a varied strategy"
    assert lab.recover(record, attempt=2) == "escalate after retry limit"
    assert lab.recover(record, attempt=0, max_retries=0) == "escalate after retry limit"


def test_decision_record_contains_no_raw_identity():
    item = next(item for item in TRAFFIC if item.request_id == "attack-03")
    observation = lab.observe(item, POLICY_V1)
    assert observation.identity_hash == hashlib.sha256(b"user-a03").hexdigest()
    record = lab.decide(observation, POLICY_V1)
    serialized = record.to_json()
    assert "user-a03" not in serialized
    assert "user_id" not in serialized
    assert record.confidence == pytest.approx(0.77)


def test_decision_enum_has_exactly_five_members():
    assert list(lab.Decision) == [
        lab.Decision.ALLOW,
        lab.Decision.TRANSFORM,
        lab.Decision.BLOCK,
        lab.Decision.ABSTAIN,
        lab.Decision.ESCALATE,
    ]
