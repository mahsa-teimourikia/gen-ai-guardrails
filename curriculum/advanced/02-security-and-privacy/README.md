# Security and privacy

**Level:** Advanced  
**Estimated time:** 45–60 minutes  
**Prerequisites:** [Evaluation and red teaming](../01-evaluation-and-red-teaming/README.md)  
**Notebook:** [security and privacy lab](security_and_privacy.ipynb) (see [ROADMAP.md](../../../ROADMAP.md))
**Scenario:** Internal HR/IT support assistant

## Learning objectives

**In the lab:** Sections 1–9 produce deterministic evidence for each objective over synthetic HR/IT support data.

- Map OWASP and agentic threats to executable controls in section 1.
- Prove execution-time authorization and injection-resistant capability binding in sections 2–3.
- Detect, mask, tokenize, and govern PII and secrets in sections 4–6.
- Verify detector artifacts and privacy-preserving evaluation access in sections 7–8.
- Produce an immutable incident evidence bundle and regression case in section 9.

Guardrails are part of an application security architecture. They should complement authentication, authorization, network isolation, secrets management, data governance, and incident response.

## Threats to model

**In the lab:** Section 1 builds a threat register from the OWASP lists and maps each threat to the relevant runnable control.

Use the [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) and [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) as starting taxonomies. Model at least:

- direct prompt injection and jailbreaks;
- indirect injection in documents, web pages, email, and tool output;
- sensitive information disclosure;
- data and model poisoning;
- improper output handling;
- excessive agency and tool misuse;
- unauthorized retrieval across tenants;
- insecure plugin or dependency supply chain;
- denial of service and denial of wallet; and
- unsafe memory or policy changes.

## Authorization is not a guardrail score

**In the lab:** Section 2 passes a plan check, changes trusted state, and shows execution-time authorization blocking the stale plan.

A classifier can say a request looks safe while the user is still unauthorized. Enforce access control with the identity provider, service authorization, row/document filters, and tool gateway. Check authorization at execution time because state can change after the model decides.

## Prompt injection

**In the lab:** Section 3 extracts untrusted claims, demonstrates that they cannot change session authority, and blocks a detector-miss export at the gateway.

Separate instructions from data, label provenance, minimize retrieved content, and assume any content can contain instructions. Use detection as a signal, not proof of safety. Most importantly, make injected instructions unable to grant permissions or bypass the tool gateway.

## PII and sensitive data

**In the lab:** Section 4 reports rule-based PII detections, documents a name miss and phone false positive, and exercises masking and scoped re-identification.

Define data classes, purpose, retention, residency, and legal basis. Detect and mask or tokenize sensitive fields before sending content to external models or validators. Preserve a reversible mapping only where the workflow requires it, with access controls and expiration.

[Microsoft Presidio](https://microsoft.github.io/presidio/) provides open-source detection and anonymization building blocks. A detector will miss entities and create false positives; combine it with schema, source, and policy checks.

The lab uses rule-based heuristics and frozen scores as a deterministic simulation, not as a live detector or provider integration.

## Tool and agent security

**In the lab:** Section 5 runs the full binding chain, including tenant, resource, argument, detector, side-effect, and idempotency checks.

For a tool call, bind:

```text
initiating user → agent role → capability → exact resource → validated arguments → approved side effect
```

Use least privilege, short-lived credentials, allowlisted destinations, read-only defaults, dry-run previews, idempotency keys, and post-action verification. Treat other agents as untrusted peers; validate messages and delegated authority.

## Secrets and logs

**In the lab:** Section 6 redacts secrets, separates conversation and audit records, and catches a secret reconstructed from two individually harmless fragments.

Do not place secrets in prompts, retrieved documents, memory, or model output. Redact traces, set retention, restrict access, and separate security audit logs from user-visible conversation logs. Test whether a model can reconstruct secrets from indirect evidence.

## Model and detector supply chain

**In the lab:** Section 7 verifies pinned artifact hashes and fails a detector upgrade when a regression case becomes a miss.

Pin dependencies and model artifacts, verify checksums or signatures where available, review validator code, restrict policy changes, and monitor changes in third-party APIs. Test a detector upgrade against the same regression set before rollout.

## Privacy-preserving evaluation

**In the lab:** Section 8 checks role access to a synthetic, retention-limited evaluation set.

Use synthetic or de-identified examples, minimize copied production content, restrict dataset access, and record consent and retention. Evaluation data often contains the same sensitive material as production.

## Incident response

**In the lab:** Section 9 disables a capability, records revoked credentials, computes blast radius, preserves evidence hashes, and creates a regression case.

1. Stop or constrain the affected capability.
2. Revoke exposed credentials and rotate keys.
3. Preserve traces, policy versions, detector versions, and relevant artifacts.
4. Identify affected users, data, tools, and external side effects.
5. Roll back or tighten the policy and add a regression test.
6. Communicate impact and remediation according to your obligations.

## Sources

**In the lab:** The examples remain provider-neutral and use these sources as conceptual context rather than live service dependencies.

- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)
- [MITRE ATLAS](https://atlas.mitre.org/)
## Exercises

1. Add a new capability and test every link in its binding chain, including execution-time revocation.
2. Extend the PII rules with a documented miss and false positive, then update the external-call boundary test.
3. Add a detector regression case and explain why the supply-chain gate blocks the upgrade.

## Setup

Use the contributor setup in the [root README](../../../README.md#run-locally). The lab uses synthetic fixtures, rule-based detectors, and frozen scores; it makes no provider calls.

## Where this fits

This course follows [Evaluation and red teaming](../01-evaluation-and-red-teaming/README.md) and prepares you for the agent/tool capstone. Continue to the [Agent and tool capstone](../03-agent-tool-capstone/README.md) to apply these security boundaries to bounded side effects.
