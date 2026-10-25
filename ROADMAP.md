# GenAI Guardrails learning roadmap

This repository is a progressive, runnable learning platform. Each lesson follows the same loop: learn the concept, run a small example, change one variable, measure the effect, and explain the trade-off.

## Levels

| Level | Outcome | Typical projects |
| --- | --- | --- |
| Beginner | Understand the control model and guardrail lifecycle | Layered assistant, policy decision walkthrough |
| Intermediate | Design and implement scenario-specific controls | Support assistant, extraction pipeline, tool gateway |
| Advanced | Evaluate, red-team, and operate secure controls | Red-team lab, regression suite, agent/tool capstone |

## Delivery sequence

1. **Foundation (delivered):** curriculum structure, lesson contract, and repository scaffolding.
2. **Runnable lessons (delivered):** eight provider-neutral notebooks and reusable lab modules with deterministic fixtures.
3. **Red-team lab (delivered):** adversarial scenarios, calibrated metrics, and regression tests for discovered failures.
4. **Secure operation lab (delivered):** security, privacy, supply-chain, and incident-response controls with deterministic evidence.
5. **Agent/tool capstone (delivered):** [`curriculum/advanced/03-agent-tool-capstone`](curriculum/advanced/03-agent-tool-capstone) demonstrates bounded tool use, authorization, approvals, budgets, receipts, and reconciliation.
6. **Learning hub (delivered):** [Open the browser-based companion](https://mahsa-teimourikia.github.io/gen-ai-guardrails/) for curriculum navigation, runnable-lab links, progress, and the full quiz.
7. **State-of-the-art stack course (delivered):** current frameworks, services, evaluation tools, adapters, and replaceable stack selection are covered in [`curriculum/advanced/04-state-of-the-art-stack`](curriculum/advanced/04-state-of-the-art-stack).
8. **Release audit (delivered):** the locked Python environment, Python 3.11–3.13 CI matrix, curriculum coverage validator, Hub build, quiz, notebooks, and security checks form one release gate.

## Definition of done

- [x] Lesson README has objectives, prerequisites, estimated time, and stable links.
- [x] Examples are deterministic, provider-neutral, and use synthetic data.
- [x] Tests cover expected behavior and important failure modes.
- [x] Internal links and quiz sources resolve.
- [x] Security, privacy, and authorization boundaries are explicit.
- [x] Changes pass the repository validation commands.

## Technology policy

Examples remain provider-neutral Python first. Pydantic is appropriate for typed validation. NeMo Guardrails, Guardrails AI, Presidio, promptfoo, and Garak are comparison points, not mandatory dependencies or endorsements.
