# Security Policy

Thanks for helping keep **LLMAIx Web** and its users safe. This document
covers how to report a vulnerability. For the broader security posture of the
application (threat model, data flow, hardening checklist), see
[`docs/SECURITY.md`](../docs/SECURITY.md) and the companion documents in
[`docs/`](../docs).

> ⚠️ **Research use.** LLMAIx Web is provided for research use and is **not a
> certified medical device**. The deploying institution is the data controller
> and is responsible for its own security review, DPIA, and information-
> governance sign-off before processing real patient data.

## Supported versions

This is an actively developed research project. Only the **latest release** and
the `main` branch receive security fixes. Please upgrade to the newest version
before reporting an issue, in case it has already been addressed.

| Version         | Supported          |
| --------------- | ------------------ |
| Latest release  | :white_check_mark: |
| `main`          | :white_check_mark: |
| Older releases  | :x:                |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report privately through either channel:

1. **GitHub Security Advisories (preferred)** — use the
   [**Report a vulnerability**](https://github.com/KatherLab/llmaixweb/security/advisories/new)
   button on the repository's *Security* tab. This keeps the report private and
   lets us collaborate on a fix.
2. **Email** — contact the maintainer at **fabian.wolf2@tu-dresden.de**. Use the
   subject line `[LLMAIx Web security]`.

Please include, where possible:

- A description of the vulnerability and its impact.
- Steps to reproduce (proof-of-concept, affected endpoint/component, config).
- The version / commit hash and deployment mode (local storage vs. S3, SSO on/off, etc.).
- Any suggested remediation.

## What to expect

- **Acknowledgement:** we aim to confirm receipt within **5 business days**.
- **Assessment:** we will investigate and keep you updated on our findings and
  planned remediation.
- **Disclosure:** we follow **coordinated disclosure**. Please give us a
  reasonable window to release a fix before any public disclosure. We are happy
  to credit reporters in the release notes unless you prefer to remain anonymous.

As a small research team we cannot offer a paid bug-bounty, but we genuinely
appreciate responsible disclosure and will acknowledge your contribution.

## Scope

In scope: the LLMAIx Web backend (FastAPI), frontend (Vue), Celery task
processing, authentication/SSO, and the official Docker images.

Out of scope: vulnerabilities in third-party dependencies (report those
upstream; we track them via Dependabot and the security-scanning CI), issues
requiring a compromised admin account, and self-inflicted misconfiguration
already called out in [`DEPLOY.md`](../DEPLOY.md).
