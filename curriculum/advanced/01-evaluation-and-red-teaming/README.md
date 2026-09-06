# Evaluation and red teaming

**Level:** Advanced  
**Estimated time:** 45–60 minutes  
**Prerequisites:** [Scenario cookbook](../../intermediate/02-scenario-cookbook/README.md)  
**Notebook:** [evaluation and red teaming lab](evaluation_and_red_teaming.ipynb) (see [ROADMAP.md](../../../ROADMAP.md))
**Scenario:** Internal HR/IT support assistant

## Learning objectives

**In the lab:** Sections 1–8 turn each objective into a deterministic result over frozen synthetic cases.

- Compute taxonomy coverage and identify adversarial gaps in section 1.
- Compute confusion, security, and slice metrics with explicit numerators and denominators in section 2.
- Calibrate frozen judge labels against human labels and inspect grader choices in section 4.
- Run an authorized red-team workflow, create regression cases, and verify threshold selection in sections 5–6.
- Compare shadow/canary decisions and evaluate release gates in sections 7–8.

Guardrails need their own evaluation. A safe-looking demo can hide false positives, bypasses, latency, privacy leakage, or unsafe side effects.

## Build a test taxonomy

**In the lab:** Section 1 counts golden, adversarial, and production-sampled cases by family and reports families without adversarial coverage.

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

**In the lab:** Section 2 computes the positive class as `expected != ALLOW`, exposes each numerator and denominator, and compares language and tenant slices.

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

**In the lab:** Section 4 applies deterministic, state, judge, and human graders in order and calibrates frozen judge labels against a frozen human reference set.

Prefer the strongest evidence available:

1. deterministic validators and schemas;
2. environment state or transaction verification;
3. rule-based policy checks;
4. calibrated model judges with a rubric; and
5. expert or user review for high-impact ambiguity.

Model judges need blind calibration examples, inter-rater checks, versioning, and periodic comparison with human judgments.

## Red-team workflow

**In the lab:** Section 5 refuses production, expired, or out-of-scope authorization, then records findings and turns them into golden regression cases.

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

**In the lab:** Section 6 sweeps frozen detector scores with tier-specific costs and prints the accuracy-maximizing and expected-loss-minimizing thresholds.

Do not choose a threshold from a single accuracy score. Select it by risk tier and operational cost:

```text
expected loss = false-negative cost + false-positive cost + latency/cost friction
```

High-impact actions generally justify lower tolerance for false negatives and a human escalation path for uncertain cases. Low-risk creative flows may prioritize a smooth safe alternative.

## Shadow and canary deployment

**In the lab:** Section 7 lists current/candidate disagreements and applies the candidate only to the `bu-south` canary slice.

Run a new detector in shadow mode, compare decisions with the current policy, inspect disagreements, then enforce it for a low-risk slice. Roll out by tenant, traffic percentage, or risk tier and keep an immediate rollback path.

## Regression gates

**In the lab:** Section 8 evaluates bypass, security, false-negative, output, latency, and trace-completeness gates before and after threshold and trace remediation.

Block a release when:

- critical bypasses increase;
- unauthorized actions are possible;
- false negatives exceed the risk threshold;
- schema or groundedness checks regress;
- latency or cost exceeds the service envelope; or
- traces lack enough evidence to investigate decisions.

## Sources

**In the lab:** The executable examples stay provider-neutral and use these sources as conceptual context rather than live service dependencies.

- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [Garak](https://docs.garak.ai/)
- [PyRIT](https://azure.github.io/PyRIT/)
- [promptfoo red teaming](https://www.promptfoo.dev/docs/red-team/)
- [NeMo Guardrails evaluation](https://docs.nvidia.com/nemo/guardrails/latest/evaluate/evaluate.html)

## Exercises

1. Add a new multilingual case and inspect how it changes the language slice and expected loss.
2. Change the high-tier false-negative envelope and explain whether the release gate should pass.
3. Add a judge disagreement and recalculate Cohen's kappa.

## Setup

Use the contributor setup in the [root README](../../../README.md#run-locally). The lab uses synthetic cases, frozen detector scores, and frozen grader labels; it makes no provider calls.

## Where this fits

Continue to [Security and privacy](../02-security-and-privacy/README.md) after this evaluation loop.
