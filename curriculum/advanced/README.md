# Advanced track

## Track goal

**Evaluate, red-team and operate.** This track addresses adversarial behavior, measurement quality, privacy, supply chain risk, and incident response.

## Who this track is for

This track is for engineers, evaluators, and security practitioners responsible for proving that guardrails work and operating them safely after release.

## What you will be able to do

- Build a test taxonomy spanning safety, reliability, security, and operations.
- Select metrics, calibrate graders, and establish regression gates.
- Run authorized red-team exercises with synthetic data and complete traces.
- Model injection, privacy, tool, supply-chain, and incident-response risks.

## Course sequence

| Course | Main question | Core capability |
| --- | --- | --- |
| [01 — Evaluation and red teaming](01-evaluation-and-red-teaming/README.md) | How do we know controls work under attack? | Measure, calibrate, red-team, and gate a guardrail with tests |
| [02 — Security and privacy](02-security-and-privacy/README.md) | How do we operate controls against threats? | Protect identities, data, tools, dependencies, and incident evidence with tests |

### 01 — Evaluation and red teaming

**Key concepts:** test taxonomies, metrics, graders, authorized probing, thresholds, shadow and canary deployment, and regression gates.

**Exit criterion:** design an evaluation loop that converts adversarial findings into measurable release gates.

### 02 — Security and privacy

**Key concepts:** threat modeling, authorization, prompt injection, PII, secrets, tool and agent security, supply chain, privacy-preserving evaluation, and incident response.

**Exit criterion:** explain the surrounding security architecture required for guardrails to be operated responsibly.
