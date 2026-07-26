# Security and privacy

Guardrails are part of an application security architecture. They should complement authentication, authorization, network isolation, secrets management, data governance, and incident response.

## Threats to model

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

A classifier can say a request looks safe while the user is still unauthorized. Enforce access control with the identity provider, service authorization, row/document filters, and tool gateway. Check authorization at execution time because state can change after the model decides.

## Prompt injection

Separate instructions from data, label provenance, minimize retrieved content, and assume any content can contain instructions. Use detection as a signal, not proof of safety. Most importantly, make injected instructions unable to grant permissions or bypass the tool gateway.

## PII and sensitive data

Define data classes, purpose, retention, residency, and legal basis. Detect and mask or tokenize sensitive fields before sending content to external models or validators. Preserve a reversible mapping only where the workflow requires it, with access controls and expiration.

[Microsoft Presidio](https://microsoft.github.io/presidio/) provides open-source detection and anonymization building blocks. A detector will miss entities and create false positives; combine it with schema, source, and policy checks.

## Tool and agent security

For a tool call, bind:

```text
initiating user → agent role → capability → exact resource → validated arguments → approved side effect
```

Use least privilege, short-lived credentials, allowlisted destinations, read-only defaults, dry-run previews, idempotency keys, and post-action verification. Treat other agents as untrusted peers; validate messages and delegated authority.

## Secrets and logs

Do not place secrets in prompts, retrieved documents, memory, or model output. Redact traces, set retention, restrict access, and separate security audit logs from user-visible conversation logs. Test whether a model can reconstruct secrets from indirect evidence.

## Model and detector supply chain

Pin dependencies and model artifacts, verify checksums or signatures where available, review validator code, restrict policy changes, and monitor changes in third-party APIs. Test a detector upgrade against the same regression set before rollout.

## Privacy-preserving evaluation

Use synthetic or de-identified examples, minimize copied production content, restrict dataset access, and record consent and retention. Evaluation data often contains the same sensitive material as production.

## Incident response

1. Stop or constrain the affected capability.
2. Revoke exposed credentials and rotate keys.
3. Preserve traces, policy versions, detector versions, and relevant artifacts.
4. Identify affected users, data, tools, and external side effects.
5. Roll back or tighten the policy and add a regression test.
6. Communicate impact and remediation according to your obligations.

## Sources

- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)
- [MITRE ATLAS](https://atlas.mitre.org/)
