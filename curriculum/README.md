# GenAI Guardrails Curriculum

A practical, architecture-first curriculum for learning how to design, implement, evaluate, and operate controls for generative AI applications and agents.

The curriculum is organized by engineering capability, not by vendor or framework:

```text
BEGINNER
Understand the control model
        ↓
INTERMEDIATE
Design and implement controls
        ↓
ADVANCED
Evaluate, red-team and operate
```

## Learning philosophy

Every course follows the same progression:

```text
Concept
  ↓
Why it exists
  ↓
Control boundary
  ↓
Implementation
  ↓
Failure modes
  ↓
Evaluation
  ↓
Operational trade-offs
```

The README is the technical training chapter. Planned notebooks will be practical companions, so learners understand the policy and trade-offs before relying on a framework abstraction.

> **Add complexity only when evaluation demonstrates the failure mode that complexity is intended to solve.**

## Curriculum map

### Beginner — Understand the control model

Start with [`beginner/README.md`](beginner/README.md).

| Course | Main question | Core capability |
| --- | --- | --- |
| [01 — What are GenAI guardrails?](beginner/01-what-are-guardrails/README.md) | What is the operating envelope of an AI system? | Distinguish guardrail boundaries, control types, and safe failure behavior |
| [02 — Guardrail lifecycle](beginner/02-guardrail-lifecycle/README.md) | How does a policy become an observable control? | Define, decide, execute, recover, measure, and improve controls |

```text
control model
      ↓
measurable lifecycle
```

**Exit capability:** explain where controls belong, why prompts are insufficient, and how a typed decision moves through a guarded system.

### Intermediate — Design and implement controls

Continue with [`intermediate/README.md`](intermediate/README.md).

| Course | Main question | Core capability |
| --- | --- | --- |
| [01 — Best practices](intermediate/01-best-practices/README.md) | How should production controls be designed? | Turn risk, boundaries, failure behavior, and operations into explicit practice |
| [02 — Scenario cookbook](intermediate/02-scenario-cookbook/README.md) | How do controls change with the scenario? | Apply identity, authorization, validation, transformation, abstention, and escalation |

```text
risk register
      ↓
boundary design
      ↓
scenario implementation
```

**Exit capability:** design a provider-neutral control plan with explicit trust boundaries, safe fallbacks, and tests for false positives and false negatives.

### Advanced — Evaluate, red-team and operate

Finish with [`advanced/README.md`](advanced/README.md).

| Course | Main question | Core capability |
| --- | --- | --- |
| [01 — Evaluation and red teaming](advanced/01-evaluation-and-red-teaming/README.md) | How do we know controls work under attack? | Measure, calibrate, red-team, and gate a guardrail with tests |
| [02 — Security and privacy](advanced/02-security-and-privacy/README.md) | How do we operate controls against real threats? | Model threats, protect data and tools, and prepare incident response |

```text
measurement
      ↓
adversarial evidence
      ↓
secure operation
```

**Exit capability:** evaluate controls by safety, reliability, security, and operations dimensions, then operate them with privacy-aware evidence and incident response.
