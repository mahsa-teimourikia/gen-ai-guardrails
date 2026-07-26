# The guardrail lifecycle

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
  "decision": "allow|transform|block|retry|abstain|escalate",
  "policy": "customer_support.v3",
  "reason_codes": ["unsupported_claim"],
  "confidence": 0.91,
  "next_step": "request_source"
}
```

Avoid a single opaque boolean. Reason codes support analytics, user messaging, appeals, and policy debugging.

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
| Retry | Cap retries and vary the strategy |
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

## 9. Improve

Use failures to update the narrowest responsible layer. A prompt injection that reached a tool may require tool authorization, retrieval isolation, and a new regression test—not only a stronger system prompt.

Version policies, detectors, prompts, models, thresholds, and datasets together. Roll out changes gradually and compare against the previous policy version.

## A staged rollout

1. Shadow mode: observe decisions without blocking.
2. Alert mode: notify operators and collect labels.
3. Low-risk enforcement: block or transform reversible cases.
4. High-risk enforcement: require approval or fail closed.
5. Continuous monitoring: sample outcomes and refresh adversarial tests.

## Sources

- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)
- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [OpenAI safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [NVIDIA NeMo Guardrails architecture](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/how-it-works)
