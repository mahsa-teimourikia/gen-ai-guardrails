import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "curriculum/intermediate/02-scenario-cookbook/examples/guardrail_pipeline.py"
)
spec = importlib.util.spec_from_file_location("guardrail_pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = pipeline
spec.loader.exec_module(pipeline)


def test_unauthenticated_identity_is_blocked():
    result = pipeline.guard_input("Hello", {"authenticated": False})
    assert result.decision is pipeline.Decision.BLOCK
    assert result.reasons == ["authentication_required"]


def test_oversized_input_is_blocked():
    result = pipeline.guard_input("x" * 20_001, {"authenticated": True})
    assert result.decision is pipeline.Decision.BLOCK
    assert result.reasons == ["input_too_large"]


def test_normal_authenticated_input_is_allowed():
    result = pipeline.guard_input("Hello", {"authenticated": True})
    assert result.decision is pipeline.Decision.ALLOW


def test_write_tool_requires_authorization_and_approval():
    unauthorized = pipeline.guard_tool_call({}, "create_draft", {})
    assert unauthorized.decision is pipeline.Decision.BLOCK
    assert unauthorized.reasons == ["write_not_authorized"]

    authorized = pipeline.guard_tool_call({"can_write": True}, "create_draft", {})
    assert authorized.decision is pipeline.Decision.ESCALATE
    assert authorized.reasons == ["approval_required"]
