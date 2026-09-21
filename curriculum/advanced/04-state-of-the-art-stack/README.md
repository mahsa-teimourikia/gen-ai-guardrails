# State of the art: selecting a guardrail stack

**Level:** Advanced

**Estimated time:** 75–90 minutes

**Prerequisites:** [Evaluation and red teaming](../01-evaluation-and-red-teaming/README.md), [Security and privacy](../02-security-and-privacy/README.md), and the [Agent and tool capstone](../03-agent-tool-capstone/README.md)

**Notebook:** [state-of-the-art stack lab](state_of_the_art_stack.ipynb)

**Scenario:** A multi-tenant benefits-support assistant that reads private cases and can submit approved corrections

**Landscape snapshot:** 20 September 2026

## Learning objectives

- Separate application-owned security invariants from detectors, orchestration frameworks, managed services, evaluation tools, and telemetry.
- Compare common open-source libraries and cloud services by control boundary, deployment model, evidence, and failure behavior.
- Normalize incompatible SDK responses behind a stable typed decision contract.
- Build a risk-driven stack for a realistic regulated workflow rather than selecting a product from a feature checklist.
- Evaluate thresholds and dependency failures with false-positive, false-negative, degraded-mode, and release-gate evidence.

## What “state of the art” means here

The current frontier is not one perfect classifier. Production systems increasingly combine:

1. **Application-owned invariants** for identity, authorization, tenant boundaries, schemas, budgets, approvals, idempotency, and transaction verification.
2. **Runtime guardrail frameworks** that place configurable checks around input, retrieval, model output, and tool calls.
3. **Specialist models and services** for prompt injection, content safety, PII, grounding, malicious files or URLs, and multimodal content.
4. **Continuous evaluation and red teaming** using labeled, adversarial, multilingual, and workflow-level datasets.
5. **AI-aware observability** that relates guardrail, model, retriever, agent, and tool spans without logging unnecessary sensitive content.

This landscape changes quickly. Every capability claim below links to a maintained primary source and is dated. Re-run the evaluation on your workload before adopting or upgrading any component.

## The non-negotiable architecture boundary

```text
trusted identity + application policy
                 │
                 ▼
request → typed validation → detector adapters → model/retrieval
                 │                    │
                 └──── decision ──────┘
                           │
                 execution authorization
                           │
                approved, bounded side effect
                           │
               verification + receipt + trace
```

A safety score is evidence, not authority. A detector or model can recommend `block`, `transform`, or `escalate`; it must not grant a role, cross a tenant boundary, approve its own action, or make an irreversible write safe. Those are deterministic application responsibilities.

## Common tools and where they fit

### Runtime frameworks and validation libraries

| Tool | Best fit | Important boundary |
| --- | --- | --- |
| [OpenAI Guardrails Python](https://openai.github.io/openai-guardrails-python/quickstart/) | Configurable preflight, input, output, and agent/tool checks around OpenAI-compatible clients; includes an evaluation utility | Default execution-error handling is fail-safe unless strict error handling is enabled; choose and test failure behavior explicitly |
| [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types) | Input, retrieval, dialog, execution, and output rails; custom actions; multiple model backends | Rails still need application authorization and workload-specific evaluation; NVIDIA documents separate evaluation workflows for rail performance and configuration compliance |
| [Guardrails AI](https://guardrailsai.com/guardrails/docs) | Reusable validators, structured input/output validation, and repair or re-ask workflows | Validation improves shape and policy conformance but does not prove a claim is true or a caller is authorized |
| [Pydantic](https://docs.pydantic.dev/latest/) | Typed request, tool-argument, decision, receipt, and configuration contracts in Python | Schema validity is necessary but not sufficient for authorization, provenance, or business invariants |
| [Outlines](https://dottxt-ai.github.io/outlines/) and [Guidance](https://guidance.readthedocs.io/) | Grammar- or schema-constrained generation | Constrained syntax does not guarantee safe semantics or permitted side effects |

### Specialist safety, privacy, and managed services

| Tool/service | Current capabilities | Evaluation questions |
| --- | --- | --- |
| [Microsoft Presidio](https://microsoft.github.io/presidio/) | Extensible PII recognition plus masking, redaction, replacement, hashing, or encryption | Which languages and entity classes are required? What are the miss and over-redaction rates on your data? |
| [Meta Purple Llama / Llama Guard](https://github.com/meta-llama/PurpleLlama) | Open safety classifiers and security evaluation assets | Does the taxonomy match your policy? What compute, latency, multilingual, and calibration trade-offs apply? |
| [Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview) | Text/image safety, Prompt Shields for user and document attacks, blocklists, protected material, and groundedness features | How are severity thresholds tuned? What happens during a regional or service failure? |
| [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html) | Content and prompt-attack filters, denied topics, word and sensitive-information filters, contextual grounding, and automated-reasoning checks | Which features and logging settings apply in the selected region/tier? Are blocked prompts retained in invocation logs? |
| [Google Cloud Model Armor](https://docs.cloud.google.com/model-armor/overview) | Prompt/response screening for injection, safety, sensitive data, URLs, documents, and preview image screening | Which modality is supported by the chosen integration? What network, region, file-size, and preview constraints apply? |

Managed services can reduce integration work and provide regularly updated detectors, but they introduce data-boundary, availability, cost, regional, version-drift, and vendor-lock-in questions. Self-hosted controls improve deployment control but transfer model lifecycle, scaling, patching, and evaluation responsibilities to your team.

### Evaluation, red teaming, and observability

| Tool | Role in the lifecycle |
| --- | --- |
| [promptfoo](https://github.com/promptfoo/promptfoo) | Provider-neutral prompt/application evaluation, red teaming, custom targets, and CI gates |
| [PyRIT](https://azure.github.io/PyRIT/) | Orchestrated AI risk identification with targets, converters, scorers, and attack strategies |
| [garak](https://docs.garak.ai/) | Vulnerability probes and detectors for model and application testing |
| [Inspect AI](https://inspect.aisi.org.uk/) | Reproducible evaluation tasks, solvers, scorers, logs, and sandbox integrations |
| [OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/) | Vendor-neutral telemetry transport and semantic conventions |
| [OpenInference](https://arize-ai.github.io/openinference/spec/) | AI-specific span kinds and attributes for agents, tools, retrieval, guardrails, and evaluators on OpenTelemetry |
| [Phoenix](https://arize.com/docs/phoenix) / [Langfuse](https://langfuse.com/docs) | Trace inspection, datasets, experiments, and evaluation workflows |

Automated red teaming generates hypotheses and cases; it does not replace an authorized test plan, domain experts, manual exploration, or remediation. Model-based graders also require calibration against blind human labels.

## A risk-driven selection method

Choose components in this order:

1. **Write the operating envelope.** List users, data, modalities, languages, allowed actions, prohibited outcomes, reversibility, and regulatory constraints.
2. **Assign each invariant to an enforcement boundary.** Put identity, authorization, tenant isolation, budgets, and transactions in deterministic application or infrastructure controls.
3. **Define required evidence.** For each policy, state the decision type, reason code, version, trace, retention, appeal, and human-review requirements.
4. **Set deployment constraints.** Record data residency, egress, latency, throughput, offline operation, model/provider compatibility, and total cost.
5. **Shortlist by capability, not branding.** Require primary documentation and a dated capability claim.
6. **Run a bake-off on representative data.** Compare false negatives, false positives, slice performance, latency, cost, and outage behavior.
7. **Test the composed workflow.** A good detector can still be unsafe if it runs after retrieval, logs raw PII, or fails open before a consequential tool call.
8. **Plan replacement before adoption.** Normalize vendor responses, version configurations, keep evaluation datasets portable, and avoid putting business authorization inside an SDK callback.

## Practical lab

The offline lab uses [Pydantic](https://docs.pydantic.dev/latest/) for real typed contracts and frozen representative response shapes for OpenAI Guardrails, NeMo Guardrails, and a managed service. It does not claim that the small catalog is a benchmark or procurement ranking.

### 1. Validate a stack plan

Load `fixtures/tool_catalog.json` and `fixtures/scenario.json`, run `select_stack`, then construct `StackPlan`. The model rejects missing capabilities, unsupported deployment modes, and detector-only stacks without application-owned controls.

### 2. Normalize SDK responses

Call `normalize_response` for each frozen provider response. The output is one stable `GuardSignal` with a source, check, score, availability state, and reason code. Application policy no longer depends on a vendor-specific `tripwire_triggered`, `status`, or `action` field.

### 3. Exercise decision and outage policy

`decide` composes injection, content, and PII signals. The same dependency outage permits a degraded read-only response but fails closed before a write. Change `fail_closed_for` and explain the user-harm and availability trade-off.

### 4. Evaluate and gate

`evaluate` reports exact matches, false positives, false negatives with denominators, degraded cases, and the decision confusion map. Raise the injection threshold to `0.99`: the indirect-injection case becomes a false negative and `release_gate` blocks promotion.

### 5. Emit privacy-minimized evidence

`trace_event` emits a `GUARDRAIL` span-shaped record with the decision, version, reason codes, and degraded state. It deliberately omits raw prompts and responses. In production, record hashes, controlled references, or redacted excerpts only when the incident and retention policy require them.

## Evaluation matrix for a real bake-off

| Dimension | Minimum evidence |
| --- | --- |
| Policy fit | Labeled cases mapped to explicit policy clauses and reason codes |
| Detection | Precision, recall, false-positive and false-negative counts with denominators |
| Slices | Language, modality, tenant, user group, attack family, and risk tier |
| Workflow security | Unauthorized actions, cross-tenant access, injection-to-tool success, and data leakage |
| Operations | p50/p95/p99 latency, throughput, cost per request, timeout and rate-limit behavior |
| Privacy | Data sent, storage location, retention, training use, redaction, and deletion path |
| Change safety | Version pinning, changelog review, shadow/canary evidence, rollback, and kill switch |
| Explainability | Stable reason codes, trace correlation, reviewer packet, and appeal path |

Do not compare products using only a vendor demo set or overall accuracy. Keep the same held-out workload, threshold-selection rule, hardware/service tier, and failure injection across candidates.

## Failure modes to recognize

- Treating “has prompt-injection detection” as proof that injection cannot cause harm.
- Asking one model to generate, judge, authorize, and approve its own consequential action.
- Adding multiple correlated model checks and calling the result defense in depth.
- Logging raw prompts, retrieved documents, secrets, or tool results into every telemetry backend.
- Allowing an SDK default to decide fail-open versus fail-closed behavior without a threat model.
- Upgrading a managed or open model without re-running calibration and regression suites.
- Selecting a framework before defining required controls, evidence, deployment constraints, and exit criteria.

## Exercises

1. Add a self-hosted PII tool to the catalog and require `redaction`; inspect whether the greedy baseline changes.
2. Remove `application-policy-and-authz` and explain why a detector-rich plan still fails validation.
3. Add a multilingual false-positive case and expose the language as an evaluation slice.
4. Change the degraded read to an escalation instead of an allow. Update the expected outcome and release gate.
5. Sketch a real adapter for one SDK using its official quickstart, while keeping `GuardSignal` as the application contract.

## Source notes

- [NIST AI RMF Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — governance, content provenance, pre-deployment testing, incident disclosure, and lifecycle risk management.
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) and [Agentic AI threats and mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) — application and agent threat taxonomies.
- [OpenAI Guardrails Python quickstart](https://openai.github.io/openai-guardrails-python/quickstart/) and [evaluation tool](https://openai.github.io/openai-guardrails-python/evals/) — current pipeline stages, SDK integration, failure modes, and labeled evaluation.
- [NeMo Guardrails rail types](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types), [catalog](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog), and [configuration evaluation](https://docs.nvidia.com/nemo/guardrails/evaluation/evaluate-configuration) — current control surfaces and evaluation workflow.
- [Amazon Bedrock Guardrails components](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html), [Azure Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection), and [Google Model Armor](https://docs.cloud.google.com/model-armor/overview) — current managed-service capabilities and operational cautions.
- [Presidio Analyzer](https://microsoft.github.io/presidio/analyzer/) and [Anonymizer](https://microsoft.github.io/presidio/anonymizer/) — extensible PII recognition and transformation.
- [OpenInference specification](https://arize-ai.github.io/openinference/spec/) — AI-specific trace semantics layered on OpenTelemetry.

## Setup

Use the contributor setup in the [root README](../../../README.md#run-locally). The notebook uses synthetic fixtures and frozen SDK responses; it needs no API key or network access.

## Where this fits

This module follows the capstone. It helps teams turn the earlier architectural controls into a documented, replaceable implementation stack without confusing a product feature with an end-to-end safety guarantee.
