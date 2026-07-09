# Security Overview

This document summarises the security posture of **LLMAIx Web** for operators
deploying it inside a clinic to process patient data for research. It is a
companion to [DEPLOY.md](../DEPLOY.md) (deployment + production checklist),
[THREAT_MODEL.md](./THREAT_MODEL.md), [DATA_FLOW.md](./DATA_FLOW.md),
[RISK_REGISTER.md](./RISK_REGISTER.md), [DATA_RETENTION.md](./DATA_RETENTION.md),
[AUDIT_LOGGING.md](./AUDIT_LOGGING.md), and the
[DPIA template](./DPIA_TEMPLATE.md).

> ⚠️ **Research use.** This software is provided for research use. It is not a
> certified medical device. The deploying institution is the data controller and
> is responsible for its own DPIA, legal basis, and information-governance
> sign-off.

## Reporting a vulnerability

Report suspected vulnerabilities privately to the maintainers (see the
repository `README`/`SECURITY` contact). Do not open a public issue for an
unpatched vulnerability. Include: affected version/commit, reproduction steps,
and impact. We aim to acknowledge within a few working days.

## Security controls at a glance

| Area | Control |
|------|---------|
| Authentication | JWT access tokens + hashed, rotating, revocable refresh tokens; global revocation via `token_version` |
| Passwords | bcrypt (cost 12); configurable complexity policy; empty-hash sentinel blocks password login for SSO-only accounts |
| Brute force | Per-account lockout after N failed logins + per-IP rate limits on all auth endpoints |
| SSO | OIDC (PKCE + signed state); provider client secrets Fernet-encrypted at rest |
| Secrets at rest | Trial API keys + SSO client secrets Fernet-encrypted (key derived from `SECRET_KEY`); `SECRET_KEY` required (≥16 chars, hard-exit otherwise) |
| Egress control (SSRF) | User-supplied LLM/OCR endpoints validated against an SSRF policy; redirect-following disabled on extraction clients; optional host allowlist (`ALLOWED_LLM_ENDPOINTS` / `ALLOWED_OCR_ENDPOINTS`) restricts egress to approved hosts |
| Transport | TLS terminated at an external reverse proxy; HSTS emitted by the app when HTTPS is detected |
| HTTP headers | Security headers on API responses (app middleware) and on the SPA (nginx): CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Accountability | Append-only **audit log** of auth, PHI access, mutations, external egress, and admin changes (see [AUDIT_LOGGING.md](./AUDIT_LOGGING.md)) |
| Error handling | Global handler assigns a correlation **error id**, logs the trace, persists an error-log row, and returns only the id to the user |
| Uploads | Size-capped streaming reads; SHA-256 dedup; UUID storage filenames; inline serving restricted to a safe MIME allowlist |
| Deletion | Cascade delete of DB rows + stored blobs on project/user deletion |

## Known limitations (be deliberate about these)

These are documented so operators can compensate at the infrastructure layer.
See [Residual Risks & Operator Responsibilities](./RISK_REGISTER.md) for what to
do about each.

1. **Data at rest is not encrypted by the application.** Extracted document text
   (PHI) is stored in the database and uploaded files in local/S3 storage as
   plaintext. **You must provide encryption at rest** via an encrypted database
   volume / disk and encrypted object storage (SSE). This is a deployment
   requirement, not a code feature.
2. **External LLM/OCR endpoints are sub-processors.** Any trial or remote-OCR
   run sends patient text to the configured endpoint. Keep these self-hosted /
   on-premise unless you have explicitly cleared the endpoint as a permitted
   sub-processor. Every such egress is recorded in the audit log.
3. **No built-in data-retention automation.** Deletion is on-demand. See
   [DATA_RETENTION.md](./DATA_RETENTION.md) for the manual/operational process.
4. **Access model is per-owner + admin.** A project is visible to its owner and
   to admins. There is no per-field or per-cohort access control; scope projects
   accordingly.

## Hardening quick wins for production

- `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 60 min (refresh-token rotation covers
  longer sessions) — raise it only if you genuinely need longer sessions.
- Set `ALLOWED_LLM_ENDPOINTS` / `ALLOWED_OCR_ENDPOINTS` to your approved hosts so
  patient data can only ever be sent to endpoints you've cleared.
- Set `LOG_FORMAT=json` and ship stdout to your SIEM/Loki; forward the audit log
  too (see [AUDIT_LOGGING.md](./AUDIT_LOGGING.md)).
- Keep `REMOTE_OCR_FALLBACK_ENABLED=false` unless a self-hosted OCR endpoint is
  configured.
- Restrict `BACKEND_CORS_ORIGINS` to the exact public origin.
- Terminate TLS and set HSTS at the reverse proxy; forward `X-Forwarded-Proto`.
