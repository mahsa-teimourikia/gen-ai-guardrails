# What are GenAI guardrails?

**Level:** Beginner  
**Estimated time:** 45–60 minutes  
**Prerequisites:** None  
**Notebook:** planned (see [ROADMAP.md](../../../ROADMAP.md))

## Learning objectives

- Explain the operating-envelope model.
- Distinguish input, retrieval, dialog, execution, output, and operational rails.
- Compare deterministic and model-based controls.
- Choose between fail-open and fail-closed behavior.
- Describe why guardrails fail and use a layered mental model.

Guardrails are controls that constrain, validate, observe, and recover generative AI behavior. They can inspect a request before model inference, retrieved context before it enters a prompt, tool calls before execution, and model output before it reaches a user or external system.

A guardrail is not the same as a refusal prompt. Prompts influence a model; guardrails enforce policy at a boundary the application controls. A robust system combines both.

## The operating-envelope model

Define an operating envelope before selecting technology:

```text
allowed inputs + permitted capabilities + acceptable outputs + safe side effects
```

For each policy, write:

- **scope:** which users, tools, data, and modalities it covers;
- **signal:** what the detector observes;
- **decision:** allow, transform, block, retry, abstain, or escalate;
- **owner:** who is accountable for the policy;
- **evidence:** what makes the decision auditable; and
- **exception:** when a human or higher-trust path may override it.

## Guardrail types

### Input rails

Run before the model sees user content. Common checks include abuse, self-harm, jailbreak patterns, topic scope, authentication, rate limits, PII, and prompt-injection indicators.

Input rails are useful but cannot see hidden instructions in retrieved documents or tool results. Never treat them as the only injection defense.

### Retrieval rails

Run after retrieval and before context construction. Verify authorization, tenant scope, source provenance, freshness, relevance, PII policy, and malicious instructions. Retrieval rails are essential for RAG applications because a relevant document can still be unauthorized or adversarial.

### Dialog and policy rails

Maintain policy state across turns: consent, topic boundaries, escalation, age or jurisdiction constraints, and required disclosures. State belongs in application code or a controlled policy runtime, not only in a long system prompt.

### Execution rails

Guard tool calls and agent actions. Validate the tool name, schema, identity, target, amount, scope, side effect, and approval requirement before execution. Validate the result after execution and reconcile uncertain writes.

### Output rails

Inspect the generated response for policy violations, unsafe content, PII, secrets, unsupported claims, schema failures, and missing citations. Decide whether to pass, redact, rewrite, abstain, or escalate.

### Operational rails

Rate limits, budgets, timeouts, concurrency, tracing, audit records, kill switches, and incident procedures prevent safe-looking model behavior from becoming an unsafe production system.

## Deterministic versus model-based controls

| Control | Best use | Limitation |
| --- | --- | --- |
| Schema/type validation | Shape, required fields, ranges | Cannot understand every semantic risk |
| Authorization policy | Identity and resource access | Needs current identity and resource state |
| Regex/allowlist | Known patterns and commands | Easy to evade for semantic attacks |
| Specialized classifier | Toxicity, jailbreak, PII, prompt attack signals | Threshold and distribution drift |
| LLM judge | Nuanced policy or groundedness review | Cost, latency, bias, correlated failure |
| Human review | High-impact ambiguity and appeals | Slow, expensive, inconsistent without training |

Use the strongest deterministic control available. Add model-based or human checks where the risk is semantic and cannot be specified completely with rules.

## Fail-open versus fail-closed

Choose based on harm and reversibility:

- **Fail closed:** block or escalate when a missed violation is severe, such as an unauthorized payment or privacy disclosure.
- **Fail open with monitoring:** continue with a constrained fallback when false positives would deny a low-risk experience and no sensitive side effect is possible.
- **Fail safe:** return a useful, policy-compliant alternative rather than a blank error.

Document the choice per guardrail. A global “always block on detector outage” can create availability problems; a global “always continue” can create safety problems.

## Why guardrails fail

- A detector runs after the sensitive action instead of before it.
- The model is trusted to enforce permissions that code never checks.
- A classifier is evaluated only on obvious attacks, not near-boundary legitimate requests.
- An output filter blocks text but leaves tool side effects untouched.
- Retrieved content is treated as trusted because it came from an internal index.
- The system logs too little to debug or too much to protect privacy.
- Safety is measured as a single score instead of outcome, friction, latency, and drift.

## A useful mental model

Guardrails are a control system:

```text
policy → observe → decide → constrain → execute → verify → learn
```

The model is one component in that loop. It is not the policy engine, identity provider, transaction manager, or audit log.

## Sources

- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [NVIDIA NeMo Guardrails overview](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview)
- [NVIDIA NeMo Guardrails rail types](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types)
