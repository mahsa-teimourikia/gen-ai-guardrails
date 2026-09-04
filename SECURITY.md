# Security policy

## Supported version

GenAI Guardrails is an educational repository. Security fixes are applied to the current `main` branch; older branches and deployed copies are not maintained as separate supported versions.

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability or include exploit details, credentials, personal data, or cross-tenant evidence in public artifacts.

Use [GitHub private vulnerability reporting](https://github.com/mahsa-teimourikia/gen-ai-guardrails/security/advisories/new). Include the affected file or workflow, impact and preconditions, minimal reproduction, and a safe validation method.

## Educational code disclaimer

Lessons favor inspectability and local execution. They are not production security controls by themselves. Before deploying a derived system, perform a threat model, enforce identity and authorization outside the model, isolate credentials, validate tool actions, test adversarial paths, and follow each dependency's security guidance.
