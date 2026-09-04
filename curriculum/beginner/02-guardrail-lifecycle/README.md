# The guardrail lifecycle

**Level:** Beginner  
**Estimated time:** 45–60 minutes  
**Prerequisites:** [What are GenAI guardrails?](../01-what-are-guardrails/README.md)  
**Notebook:** [guardrail_lifecycle.ipynb](guardrail_lifecycle.ipynb)  
**Scenario:** Internal HR/IT support assistant

## Learning objectives

- Define a versioned HR/IT policy and map its protected boundaries in sections 1–2.
- Build privacy-safe observations and apply typed decisions in sections 3–4.
- Execute a permitted tool idempotently, verify its receipt, and recover safely in sections 5–6.
- Compute rates, friction, blocked attempts, and unsafe completions in section 7.
- Compare shadow, alert, and enforce modes and improve a missed incident in section 8.

Guardrails should be designed as a measurable lifecycle, not added as a last-minute filter. The lifecycle below applies to a chatbot, RAG pipeline, tool-using agent, or multimodal application.

## 1. Define policy

Translate broad goals such as “safe” or “private” into observable rules:

```yaml
policy:
  name: customer_support
  prohibited:
    - disclose another customer's data
    - approve refunds above the operator limit
  required:
    - cite the authorized support record
  escalation:
    - legal threat
    - uncertain identity
```

Assign a policy owner, version it, and define who can approve changes.

## 2. Map the trust boundaries

Mark every boundary where data or authority changes:

- user or tenant identity;
- uploaded files and retrieved documents;
- model context and output;
- tool gateway and external API;
- memory store;
- human approval interface; and
- logs, traces, datasets, and analytics.

Guardrails should sit at the boundary they protect. A prompt injection detector at the input boundary cannot replace authorization at the tool boundary.

## 3. Observe

Collect the minimum signal needed for the decision:

- normalized user input;
- modality and content provenance;
- classifier scores and model version;
- retrieved source IDs and access decisions;
- proposed tool name and arguments;
- user, agent, and service identity;
- policy version and environment; and
- prior decision or appeal state.

Redact or hash sensitive content where possible. A trace should be useful without becoming a second data breach.

## 4. Decide

Use a typed decision:

```json
{
  "decision": "allow|transform|block|abstain|escalate",
  "policy": "customer_support.v3",
  "reason_codes": ["unsupported_claim"],
  "confidence": null,
  "next_step": "request_source"
}
```

Avoid a single opaque boolean. Reason codes support analytics, user messaging, appeals, and policy debugging. `confidence` is optional and is populated only when a detector score drives the decision; deterministic authorization decisions use `null`.

## 5. Constrain

Examples of enforcement:

- remove or mask PII;
- strip instructions from retrieved content while preserving evidence;
- reduce tool scope or require approval;
- force a structured output schema;
- replace an unsafe answer with a safe completion;
- limit turns, tokens, spend, and rate; or
- route to a human or a specialized policy flow.

## 6. Execute and verify

For any side effect:

1. Validate identity, authorization, target, and arguments.
2. Show a preview when the action is consequential.
3. Require approval where policy says so.
4. Execute with a short-lived, least-privilege credential.
5. Record an idempotency key and external operation ID.
6. Verify the resulting state.
7. Reconcile or escalate if the result is uncertain.

## 7. Recover

Define safe behavior for each decision:

| Decision | User/system response |
| --- | --- |
| Allow | Continue and record the decision |
| Transform | Explain only when useful; preserve provenance |
| Block | Give a concise policy-compliant alternative |
| Retry (recovery action) | Cap retries and vary the strategy |
| Abstain | State what evidence or permission is missing |
| Escalate | Pause, checkpoint state, and provide context to a reviewer |

## 8. Measure

Track:

- true-positive and false-positive rates by policy;
- false negatives from adversarial tests and incidents;
- user friction, abandonment, and appeal outcomes;
- added latency and cost;
- coverage of inputs, retrieval, tools, outputs, and modalities;
- policy drift and detector drift; and
- unsafe side effects prevented or completed.

The lab uses these definitions:

| Metric | Numerator | Denominator |
| --- | --- | --- |
| `tp` | Attack items applied `block` or `escalate` | Count of attack items |
| `fp` | Legitimate or boundary items applied `block` or `escalate` | Count of legitimate and boundary items |
| `fn` | Attack items applied `allow` | Count of attack items |
| `tn` | Legitimate or boundary items applied `allow` | Count of legitimate and boundary items |
| `tpr` | `tp` | `tp + fn` |
| `fpr` | `fp` | `fp + tn` |
| `attempts_blocked` | Attack items applied `block` or `escalate` | Count of attack items |
| `unsafe_completed` | Items marked unsafe whose applied decision is `allow` | Count (not a rate) |
| `friction` | Legitimate or boundary items applied anything except `allow` | Count of legitimate and boundary items |

The traffic fixture contains frozen detector scores, not a live model. Boundary items count as legitimate for false-positive and friction calculations.

## 9. Improve

Use failures to update the narrowest responsible layer. A prompt injection that reached a tool may require tool authorization, retrieval isolation, and a new regression test—not only a stronger system prompt.

Version policies, detectors, prompts, models, thresholds, and datasets together. Roll out changes gradually and compare against the previous policy version.

## A staged rollout

1. Shadow mode: observe decisions without blocking.
2. Alert mode: notify operators and collect labels.
3. Low-risk enforcement: block or transform reversible cases.
4. High-risk enforcement: require approval or fail closed.
5. Continuous monitoring: sample outcomes and refresh adversarial tests.

## Exercises

1. Add a policy rule for an unlisted risk and predict its shadow, alert, and enforce outcomes.
2. Change the threshold without changing the tool rule and predict which metric moves first.
3. Add the incident to a regression fixture and explain why the narrowest fix belongs at the tool boundary.

## Setup

Run the lab using the root README's [Run locally](../../../README.md#run-locally) instructions.

## Where this fits

Continue with [Course 03: Best practices](../../intermediate/01-best-practices/README.md) to turn lifecycle decisions into implementation patterns.

## Sources

- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)
- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [OpenAI safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [NVIDIA NeMo Guardrails architecture (vendor documentation; terminology comparison)](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/how-it-works)
