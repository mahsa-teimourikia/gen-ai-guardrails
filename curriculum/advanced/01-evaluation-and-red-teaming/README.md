# Evaluation and red teaming

**Level:** Advanced  
**Estimated time:** 45–60 minutes  
**Prerequisites:** [Scenario cookbook](../../intermediate/02-scenario-cookbook/README.md)  
**Notebook:** planned (see [ROADMAP.md](../../../ROADMAP.md))

## Learning objectives

- Build a test taxonomy for guardrail evaluation.
- Select metrics and calibrate graders.
- Run an authorized red-team workflow.
- Choose thresholds and use shadow or canary deployment.
- Establish regression gates for discovered failures.

Guardrails need their own evaluation. A safe-looking demo can hide false positives, bypasses, latency, privacy leakage, or unsafe side effects.

## Build a test taxonomy

Organize cases by policy and attack surface:

- allowed, borderline, and prohibited requests;
- direct jailbreaks and multi-turn manipulation;
- indirect instructions in retrieved files and websites;
- PII, secrets, and cross-tenant access;
- harmful or unsupported content;
- tool misuse, invalid arguments, and unauthorized targets;
- long inputs, multilingual and multimodal inputs;
- detector outage, timeout, and rate-limit behavior; and
- partial success, approval rejection, and rollback.

Keep a golden set, an adversarial set, and a production-sampled set. Never optimize only on the cases used to build the detector.

## Metrics

| Dimension | Metrics |
| --- | --- |
| Detection | precision, recall, false-negative rate, false-positive rate |
| User experience | block rate, appeal rate, abandonment, safe-completion rate |
| Reliability | schema validity, groundedness, refusal quality, recovery rate |
| Security | unauthorized actions, injection success, data leakage, privilege escalation |
| Operations | latency, cost, throughput, timeout rate, detector availability |
| Governance | policy version coverage, trace completeness, review SLA |

Report metrics by policy, language, modality, tenant, model version, and risk tier. Aggregates can hide a vulnerable slice.

## Graders

Prefer the strongest evidence available:

1. deterministic validators and schemas;
2. environment state or transaction verification;
3. rule-based policy checks;
4. calibrated model judges with a rubric; and
5. expert or user review for high-impact ambiguity.

Model judges need blind calibration examples, inter-rater checks, versioning, and periodic comparison with human judgments.

## Red-team workflow

1. Define scope, authorization, and a safe test environment.
2. Enumerate assets, tools, identities, and unacceptable outcomes.
3. Create baseline prompts and known attack families.
4. Probe direct and indirect injection, evasion, encoding, multilingual, and multi-turn paths.
5. Attempt data exfiltration and unauthorized tool actions with synthetic secrets.
6. Record the complete trace and detector decisions.
7. Classify severity, exploitability, and blast radius.
8. Fix the narrowest responsible layer and add a regression case.
9. Re-run the baseline and adversarial suite before release.

Tools worth studying include [Garak](https://docs.garak.ai/), [PyRIT](https://azure.github.io/PyRIT/), [promptfoo](https://www.promptfoo.dev/docs/red-team/), and [Inspect AI](https://inspect.aisi.org.uk/).

## Threshold selection

Do not choose a threshold from a single accuracy score. Select it by risk tier and operational cost:

```text
expected loss = false-negative cost + false-positive cost + latency/cost friction
```

High-impact actions generally justify lower tolerance for false negatives and a human escalation path for uncertain cases. Low-risk creative flows may prioritize a smooth safe alternative.

## Shadow and canary deployment

Run a new detector in shadow mode, compare decisions with the current policy, inspect disagreements, then enforce it for a low-risk slice. Roll out by tenant, traffic percentage, or risk tier and keep an immediate rollback path.

## Regression gates

Block a release when:

- critical bypasses increase;
- unauthorized actions are possible;
- false negatives exceed the risk threshold;
- schema or groundedness checks regress;
- latency or cost exceeds the service envelope; or
- traces lack enough evidence to investigate decisions.

## Sources

- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [Garak](https://docs.garak.ai/)
- [PyRIT](https://azure.github.io/PyRIT/)
- [promptfoo red teaming](https://www.promptfoo.dev/docs/red-team/)
- [NeMo Guardrails evaluation](https://docs.nvidia.com/nemo/guardrails/latest/evaluate/evaluate.html)
