# Best practices for production guardrails

**Level:** Intermediate  
**Estimated time:** 45–60 minutes  
**Prerequisites:** [The guardrail lifecycle](../../beginner/02-guardrail-lifecycle/README.md)  
**Notebook:** [best_practices.ipynb](best_practices.ipynb)  
**Scenario:** Internal HR/IT support assistant

## Learning objectives

- Load and validate an HR/IT risk register, then map policy statements to enforcement layers in sections 1–2.
- Exercise budgets, circuit breakers, and safe detector failure behavior in section 3.
- Review safety-critical guardrail changes and distinguish them from ordinary prompt-copy changes in section 4.
- Require every evaluation layer, not only a high benchmark score, in section 5.
- Validate a human-review packet and turn a system manifest into an evidence-backed release gate in sections 6–7.
- Summarize the deterministic simulation and extend it with the exercises in section 8.

## 1. Start with a risk register

For each use case, record the asset, threat, impact, likelihood, control, owner, detector, response, and residual risk. Include ordinary mistakes, malicious users, compromised dependencies, and distribution shift.

## 2. Separate policy from implementation

Write policy in plain language and map it to enforcement. A vendor's content category is not automatically your organization's policy. Define severity, jurisdiction, age or role constraints, allowed transformations, and appeal behavior.

## 3. Prefer boundaries over instructions

Prompts are useful for behavior guidance but cannot enforce identity, access, network isolation, or transaction limits. Implement those controls in the application, gateway, database, and cloud policy.

## 4. Use defense in depth

Combine inexpensive deterministic checks with specialized models, model-based review, and human review. Do not stack many correlated LLM judges and call the result independent evidence.

## 5. Design for false positives and false negatives

For every detector, keep examples near the decision boundary. Measure what gets blocked incorrectly and what slips through. Provide an appeal or escalation path for legitimate users.

## 6. Treat all external content as untrusted

User prompts, web pages, uploaded files, retrieved documents, tool results, memory, and messages from other agents may contain malicious instructions or sensitive data. Label provenance and keep instructions separate from data.

## 7. Guard tools before and after execution

Before a call validate identity, capability, target, schema, range, and approval. After a call validate result shape, authorization effects, expected state, and sensitive output. A successful HTTP response does not prove a safe business operation.

## 8. Minimize data

Collect only what the guardrail needs, redact before external classifiers where possible, set retention limits, isolate tenants, and support deletion. Do not send full conversations to a detector when a local feature or span is sufficient.

## 9. Make safe failure useful

Users should understand what they can do next: rephrase, provide evidence, authenticate, request review, or choose a lower-risk action. Avoid exposing detector internals that make bypass easier.

## 10. Version everything

Version policy, prompts, classifiers, thresholds, schemas, tools, model IDs, and evaluation data. Store the version with each decision.

## 11. Use budgets and circuit breakers

Bound input size, output tokens, retries, tool calls, spend, concurrency, and time. Trip a circuit breaker when a detector or downstream system is unavailable or producing anomalous results.

## 12. Protect the guardrail itself

Restrict who can change policies, validators, thresholds, prompts, and allowlists. Require review for safety-critical changes. Monitor for attempts to disable or bypass checks.

## 13. Evaluate in layers

Run unit tests for rules and schemas, component tests for detectors, end-to-end tests for workflows, adversarial tests for attacks, and production monitoring for drift. A benchmark score is not a release decision by itself.

## 14. Keep humans where consequences require them

Human review is appropriate for irreversible, high-impact, ambiguous, or legally sensitive decisions. Show the reviewer the exact proposed action, evidence, uncertainty, and consequences; do not ask for context-free approval.

## 15. Keep an incident playbook

The playbook should cover credential revocation, workflow or model rollback, policy freeze, evidence preservation, user notification, impact assessment, and regression tests.

## Release checklist

- [ ] Policy owner and version are recorded.
- [ ] Trust boundaries and data flows are documented.
- [ ] Input, retrieval, tool, and output controls are identified.
- [ ] Authorization is enforced outside the model.
- [ ] Side effects have previews, approvals, idempotency, and verification.
- [ ] False-positive and false-negative datasets exist.
- [ ] Logs are sufficient but privacy-minimized.
- [ ] Budgets, timeouts, rate limits, and kill switches are configured.
- [ ] Policy changes require review and can be rolled back.
- [ ] Incident response and appeal paths are tested.

The lab evaluates each item against a system manifest and reports the evidence path it inspected; see `ReleaseGate`.

## Exercises

1. Add a risk-register row for a new HR/IT asset and decide whether its residual risk needs explicit acceptance.
2. Add a safety-critical change with an authorized reviewer, then compare it with a prompt-copy change.
3. Repair the adversarial evaluation regression and the three failing manifest items, then explain why the benchmark score alone was insufficient.

## Setup

Run the lab using the root README's [Run locally](../../../README.md#run-locally) instructions.

## Where this fits

Continue with the [scenario cookbook](../02-scenario-cookbook/README.md) to adapt these release practices to concrete trust boundaries and consequences.
