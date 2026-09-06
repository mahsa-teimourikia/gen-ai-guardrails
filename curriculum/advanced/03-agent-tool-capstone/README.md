# Agent and tool capstone

**Level:** Advanced
**Estimated time:** 60–90 minutes
**Prerequisites:** [Security and privacy](../02-security-and-privacy/README.md) and [Scenario cookbook](../../intermediate/02-scenario-cookbook/README.md)
**Notebook:** [agent and tool capstone lab](agent_tool_capstone.ipynb)
**Scenario:** Internal HR/IT support assistant for new-hire onboarding

## Learning objectives

- Inspect trusted onboarding state and dynamic capabilities in sections 1–2.
- Run an approved, idempotent tool trajectory with budgets and audit evidence in sections 3–5.
- Block tool-output instructions, cross-tenant arguments, revoked sessions, and loops in sections 6–7.
- Verify post-action resources, detect reconciliation drift, and preserve receipts in section 8.
- Evaluate frozen trajectories and enforce a capstone release gate in section 9.

This capstone uses frozen planner trajectories rather than live model output. Pydantic validates every tool argument, and all data is synthetic and deterministic.

## Scenario and trusted state

**In the lab:** Section 1 loads onboarding sessions, approvals, receipts, and the trusted system of record.

The agent supports `bu-north` and `bu-south` tenants. Its tools are `read_employee`, `create_account`, `add_to_group`, `order_hardware`, and `send_welcome_email`. Planner trajectories are labelled as frozen fixtures so learners can inspect each proposed step.

## Dynamic capability exposure

**In the lab:** Section 2 compares phase- and role-scoped capability maps.

Least privilege is dynamic: read access is available throughout the flow, while provisioning and notification tools are exposed only to authorized roles during their phase.

## Approved execution, receipts, and audit

**In the lab:** Section 3 runs the happy path and prints approvals, idempotent receipts, and correlation-linked audit events.

Side effects require a matching approval from a different user, consume explicit budgets, write receipts, and are verified against trusted resources.

## Approval recovery

**In the lab:** Section 4 stops on `approval_required`, adds the pending fingerprint approval, and re-runs the trajectory.

Recovery re-evaluates every step; it never assumes that an earlier plan remains authorized.

## Budgets and loop detection

**In the lab:** Section 5 shows spend exhaustion and the third repeated fingerprint terminating a trajectory.

Turn, spend, and side-effect budgets constrain execution independently of what a planner proposes.

## Tool-output injection

**In the lab:** Section 6 blocks a step sourced from tool output while allowing the original trajectory to finish.

Read data may contain instructions, but provenance prevents it from becoming a new authorized plan step.

## Execution-time authorization

**In the lab:** Section 7 blocks revoked sessions and cross-tenant arguments at execution time.

Authorization is checked after validation and immediately before any side effect; unauthorized actions remain zero.

## Post-action verification

**In the lab:** Section 8 simulates a system-of-record mismatch and lists reconciliation discrepancies.

Receipts are not proof by themselves: the resource is read back and a disagreement escalates instead of silently continuing.

## Trajectory evaluation and capstone gate

**In the lab:** Section 9 computes terminal accuracy, blocked attempts, approval compliance, audit completeness, and spend before evaluating the gate.

The gate demonstrates that safe execution requires complete evidence, not only a successful final answer.

## Sources

- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [Pydantic validation](https://docs.pydantic.dev/latest/)

## Exercises

1. Add an approval with the wrong fingerprint and observe that it cannot authorize the step.
2. Reduce the side-effect budget and explain which terminal state changes.
3. Add a reconciliation mismatch to a group or order and preserve the audit evidence.

## Setup

Use the contributor setup in the [root README](../../../README.md#run-locally). The lab uses synthetic fixtures, frozen trajectories, and no provider credentials.

## Where this fits

This is the capstone after [Security and privacy](../02-security-and-privacy/README.md). Continue to the learning roadmap for future platform integrations.
