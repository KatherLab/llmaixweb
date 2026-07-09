# Threat Model

A STRIDE-oriented threat model for LLMAIx Web deployed inside a clinic to
process patient data for research. Scope: the application and its immediate
dependencies (PostgreSQL, Redis, object/local storage, Celery workers, and the
configured LLM/OCR endpoints). Out of scope: the underlying host/OS, the outer
reverse proxy, and the identity provider, which the deploying institution
secures per its own standards.

## Assets

- **PHI**: uploaded files, extracted document text, trial results, ground truth.
- **Credentials/secrets**: `SECRET_KEY`, DB credentials, LLM/OCR API keys, SSO
  client secrets, user passwords, refresh tokens.
- **Accountability data**: the audit trail and error log.

## Actors

- Anonymous internet/network user (if exposed beyond the clinic network).
- Authenticated non-admin user (project owner).
- Authenticated admin.
- Compromised dependency / malicious external LLM-OCR endpoint.
- Insider with host or DB access.

## STRIDE analysis

### Spoofing
- **JWT forgery / weak secret** → `SECRET_KEY` required (≥16 chars, hard-exit
  otherwise); HS256; `token_version` global revocation.
- **Credential stuffing / brute force** → per-account lockout + per-IP rate
  limits; bcrypt(12). Failed logins and lockouts are audited.
- **Session fixation / stale tokens** → short access tokens + rotating,
  revocable refresh tokens; deactivated users rejected on every request and WS
  connect. The WebSocket JWT is passed via the `Sec-WebSocket-Protocol` header,
  not the URL, so it does not appear in access logs.

### Tampering
- **SSRF via user-supplied LLM/OCR URL** → SSRF policy validation +
  redirect-following disabled on extraction clients.
- **Malicious upload served inline (stored XSS)** → inline serving restricted to
  a safe MIME allowlist; everything else forced to attachment.
- **Audit-trail tampering** → append-only by construction (no update/delete
  path); for higher assurance, forward logs to a write-once external sink.
- **Mass-assignment / privilege escalation on update** → ownership transfer and
  role changes are admin-gated.

### Repudiation
- **"I never accessed / exported that"** → append-only audit trail records
  auth, PHI access, exports, mutations, egress, and admin changes with actor +
  IP + correlation id. Actor email is snapshotted so deleting a user does not
  erase history.

### Information disclosure
- **PHI at rest** → **not encrypted by the app**; the operator must encrypt the
  DB volume + object storage (see [Residual Risks](./RISK_REGISTER.md), item 1).
- **PHI egress to external LLM/OCR** → keep endpoints self-hosted; restrict with
  the endpoint allowlist; every egress is audited (item 2).
- **Exception detail leakage** → the global error handler returns only an error
  id; no exception detail reaches the client.
- **Secrets in API responses** → secret settings masked; SSO client secret never
  returned; internal service URLs removed from the public settings endpoint.
- **PHI in logs** → document text / extracted values are never logged.

### Denial of service
- **Unbounded uploads** → size-capped streaming reads (413 on overflow).
- **Runaway tasks** → Celery soft/hard time limits + a stuck-task sweeper;
  per-call LLM/OCR timeouts.
- **Request floods** → per-IP rate limits on auth; per-user WebSocket connection
  cap. No global request-rate limit — add one at the reverse proxy if the app is
  exposed to untrusted networks (see [Residual Risks](./RISK_REGISTER.md), item 7).

### Elevation of privilege
- **Non-admin performing admin actions** → admin dependency guard on all
  `/admin/*` endpoints; `bypass_celery` (synchronous, user-URL) is admin-only.
- **First-admin bootstrap abuse** → gated by `ALLOW_FIRST_ADMIN_SETUP` and
  "no admin exists"; rate-limited.

## What the operator must own

Full list in [Residual Risks & Operator Responsibilities](./RISK_REGISTER.md).
The most important for a clinic:

1. Encryption of PHI at rest (encrypted DB volume + object storage).
2. Controlling PHI egress to external LLM/OCR endpoints (self-host + allowlist).
3. Data retention/purge (manual process) and backup ageing.
