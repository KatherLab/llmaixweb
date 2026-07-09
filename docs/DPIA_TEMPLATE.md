# Data Protection Impact Assessment (DPIA) — Template

> A DPIA is the deploying institution's responsibility. This template
> pre-fills the parts that are properties of the **software** so your data
> protection officer (DPO) only has to supply the deployment- and study-specific
> details. Replace every `‹…›` placeholder. This is not legal advice.

Related: [DATA_FLOW.md](./DATA_FLOW.md), [THREAT_MODEL.md](./THREAT_MODEL.md),
[RISK_REGISTER.md](./RISK_REGISTER.md), [SECURITY.md](./SECURITY.md),
[DATA_RETENTION.md](./DATA_RETENTION.md).

## 1. Administrative details

| Field | Value |
|-------|-------|
| System | LLMAIx Web — LLM-based structured extraction from clinical documents |
| Version / commit | `‹fill in — see UI footer›` |
| Data controller | `‹institution›` |
| DPO / contact | `‹name, email›` |
| Assessment date / reviewer | `‹date› / ‹name›` |
| Study / purpose | `‹research study name + objective›` |

## 2. Description of the processing

- **Nature:** users upload clinical documents; the system OCRs/extracts text and
  uses an LLM to extract structured JSON fields; results are compared to ground
  truth. See [DATA_FLOW.md](./DATA_FLOW.md).
- **Scope:** `‹data subjects (e.g. N patients), document types, time range›`
- **Context:** internal clinical/research deployment on `‹infrastructure›`.
- **Purposes:** `‹specific research purpose(s)›`
- **Legal basis:** `‹e.g. GDPR Art. 6(1)(e)/(f) + Art. 9(2)(j) research, national law, ethics approval ref›`

## 3. Categories of personal data

| Category | Present? | Where stored | Notes |
|----------|----------|--------------|-------|
| Special-category health data (PHI) | `‹yes/no›` | `documents.text`, uploaded files, trial results, ground truth | Plaintext at rest — see §6 |
| Direct identifiers (name, MRN, DOB) | `‹yes/no›` | Within document text/files | Consider de-identifying before upload |
| User account data (staff) | Yes | `users` table | Email, name, hashed password |
| Audit metadata | Yes | `audit_logs` | Actor, action, IP, timestamps — no PHI |

## 4. Data flow & sub-processors

- Internal components: PostgreSQL, object/local storage, Redis, Celery workers.
- **Egress / sub-processors** (patient data leaving the app):
  - LLM extraction endpoint: `‹host — self-hosted? vendor?›`
  - OCR endpoint (if remote): `‹host›`
  - Email/SMTP (no clinical PHI): `‹provider›`
- Egress is restricted by `ALLOWED_LLM_ENDPOINTS` / `ALLOWED_OCR_ENDPOINTS`: `‹list configured hosts›`
- Every LLM/OCR egress is recorded in the audit log (host + counts, no content).

## 5. Necessity & proportionality

- Data minimisation: `‹what steps — e.g. de-identification before upload, delete raw files after extraction›`
- Retention: `‹retention period + trigger›` (see [DATA_RETENTION.md](./DATA_RETENTION.md))
- Data subject rights handling: `‹how access/erasure requests are served›`

## 6. Risks & mitigations

Work through [Residual Risks & Operator Responsibilities](./RISK_REGISTER.md)
and record the residual risk after your controls:

| Risk | Software control | Your deployment control | Residual |
|------|------------------|-------------------------|----------|
| PHI at rest plaintext | — | `‹encrypted DB volume + object storage — confirm›` | `‹low/med/high›` |
| PHI egress to external endpoints | Allowlist + audit + SSRF guard | `‹self-hosted endpoint? sub-processor agreement?›` | `‹…›` |
| Unauthorised access | AuthN, RBAC, lockout, short tokens | `‹network isolation, SSO, MFA at IdP›` | `‹…›` |
| Retention over-hold | On-demand purge | `‹scheduled review + backup rotation›` | `‹…›` |
| Insider misuse | Append-only audit trail | `‹access reviews, SIEM forwarding›` | `‹…›` |

## 7. Security measures (software baseline)

The application provides: bcrypt password hashing + policy, account lockout, IP
rate limiting, JWT + rotating/revocable refresh tokens (60-min access default),
OIDC SSO, encrypted secrets at rest (Fernet), SSRF guards + egress allowlist,
HTTP security headers, an append-only audit trail, and a central error log. See
[SECURITY.md](./SECURITY.md). **Encryption of PHI at rest is provided by the
operator's infrastructure, not the application.**

## 8. Consultation & sign-off

| Role | Name | Date | Outcome |
|------|------|------|---------|
| DPO | `‹…›` | `‹…›` | `‹approved / changes required›` |
| Information security | `‹…›` | `‹…›` | `‹…›` |
| Research ethics (if applicable) | `‹…›` | `‹…›` | `‹…›` |

**Review date:** `‹when this DPIA will be revisited›`
