# GenAI Guardrails learning roadmap

This repository is evolving from a curated guide into a progressive, runnable learning platform. Each lesson should move through the same loop: learn the concept, run a small example, change one variable, measure the effect, and explain the trade-off.

## Levels

| Level | Outcome | Typical projects |
| --- | --- | --- |
| Beginner | Understand the control model and guardrail lifecycle | Layered assistant, policy decision walkthrough |
| Intermediate | Design and implement scenario-specific controls | Support assistant, extraction pipeline, tool gateway |
| Advanced | Evaluate, red-team, and operate secure controls | Red-team lab, regression suite, agent/tool capstone |

## Delivery sequence

1. **Foundation (current):** curriculum restructure, lesson contract, and repository scaffolding.
2. **Runnable lessons:** provider-neutral notebooks per lesson with deterministic fixtures.
3. **Red-team lab:** adversarial scenarios and regression tests for discovered failures.
4. **Secure operation lab:** security, privacy, supply-chain, and incident-response controls with deterministic evidence.
5. **Agent/tool capstone:** bounded tool use, authorization, approvals, and reconciliation.
6. **Learning hub:** a browser-based companion for navigation and progress.

## Definition of done

- [ ] Lesson README has objectives, prerequisites, estimated time, and stable links.
- [ ] Examples are deterministic, provider-neutral, and use synthetic data.
- [ ] Tests cover expected behavior and important failure modes.
- [ ] Internal links and quiz sources resolve.
- [ ] Security, privacy, and authorization boundaries are explicit.
- [ ] Changes pass the repository validation commands.

## Technology policy

Examples remain provider-neutral Python first. Pydantic is appropriate for typed validation. NeMo Guardrails, Guardrails AI, Presidio, promptfoo, and Garak are comparison points, not mandatory dependencies or endorsements.
