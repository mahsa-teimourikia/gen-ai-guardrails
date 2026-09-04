# Beginner track

## Track goal

**Understand the control model.** This track establishes the boundaries, typed decisions, and lifecycle used to keep generative AI behavior within an intended operating envelope.

## Who this track is for

This track is for learners who build or review conversational applications, RAG pipelines, or agents and need a practical mental model before selecting a guardrail technology.

## What you will be able to do

- Explain why guardrails are layered controls rather than a single prompt or filter.
- Identify input, retrieval, policy, execution, output, and operational boundaries.
- Turn a broad safety goal into observable policy decisions.
- Describe how controls are observed, recovered, measured, and improved.

## Course sequence

| Course | Main question | Core capability |
| --- | --- | --- |
| [01 — What are GenAI guardrails?](01-what-are-guardrails/README.md) | What is the operating envelope? | Define and test layered guardrail decisions |
| [02 — Guardrail lifecycle](02-guardrail-lifecycle/README.md) | How does policy become a control? | Run a policy through shadow, enforce, measure, and improve |

### 01 — What are GenAI guardrails?

**Key concepts:** operating envelope, guardrail types, deterministic and model-based controls, fail-open and fail-closed behavior.

**Exit criterion:** explain which boundaries need application enforcement and how layered controls handle failure.

### 02 — Guardrail lifecycle

**Key concepts:** policy, trust boundaries, observation, typed decisions, constraints, verification, recovery, measurement, and staged rollout.

**Exit criterion:** describe an observable lifecycle for a guardrail from policy definition to continuous improvement.
