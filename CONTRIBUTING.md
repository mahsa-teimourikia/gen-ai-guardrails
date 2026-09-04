# Contributing to GenAI Guardrails

Thank you for improving the curriculum, runnable examples, quiz, or curated guidance.

## What belongs here

- Primary research, official documentation, maintained open-source projects, and high-signal educational material about guardrails.
- Focused corrections and learning improvements that help a technical reader explain, implement, test, evaluate, or operate a control.
- Scenario recipes that identify the threat, trust boundary, policy decision, safe fallback, and tests for false positives and false negatives.
- Direct links and concise explanations of why each resource belongs here.

## Submission rules

1. Search the README and curriculum before adding material.
2. Place content in the narrowest relevant lesson or resource section.
3. Prefer primary sources, official documentation, and maintained projects.
4. Do not include credentials, private data, realistic secrets, promotional claims, or ephemeral vendor limits.
5. Keep pull requests focused and preserve existing useful material.

## Choose the right contribution path

- Use issue forms for reproducible bugs, content improvements, and feature proposals.
- Use [private vulnerability reporting](https://github.com/mahsa-teimourikia/gen-ai-guardrails/security/advisories/new) for security vulnerabilities.
- Small, self-contained fixes may go directly to a pull request; discuss large curriculum changes before implementation.

## Develop from main

Create a focused branch from the latest `main`. Inspect adjacent lessons, examples, tests, prerequisites, and navigation before editing. Do not commit virtual environments, credentials, private data, or generated artifacts.

## Course expectations

A lesson README should stand on its own as a technical chapter. Contributions should:

- explain the threat model and trust boundary;
- separate deterministic authorization from model behavior;
- state the policy decision and safe fallback;
- use synthetic, deterministic data;
- explain false-positive and false-negative testing; and
- preserve stable headings and source links.

## AI-assisted contributions

AI tools may assist with research, drafting, implementation, and review, but contributors remain responsible for the artifact. Verify claims against authoritative sources, inspect generated code, run the actual checks, validate links, and ensure no secrets or unsafe examples were introduced.

Quiz questions must test concepts explained in the curriculum, have at least two correct answers, include an explanation and source link, and avoid ephemeral vendor limits.

## Validate the change

| Change | Required validation |
| --- | --- |
| Python examples or tests | `make test` |
| Internal curriculum links | `make links` |
| Quiz or quiz sources | `make quiz-test` |
| Python syntax | `python -m compileall -q curriculum tests` |

Document exact checks and results in the pull request.

## Pull request review

Complete the pull request template, link related issues and primary sources, and keep unrelated changes out of the diff. Review feedback may request narrower scope, stronger threat-model evidence, clearer failure behavior, or closer alignment between lessons, examples, tests, and navigation.

By contributing, you agree that your contribution will be licensed under this repository's MIT License.
