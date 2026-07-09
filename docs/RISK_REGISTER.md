# Residual Risks & Operator Responsibilities

This lists the security/privacy considerations that are **not** fully handled by
the software and therefore require action or awareness from the deploying
institution. Controls that the application already enforces are described in
[SECURITY.md](./SECURITY.md); they are not repeated here.

Use this alongside your own risk assessment / [DPIA](./DPIA_TEMPLATE.md). Rate
each item's likelihood and impact for *your* environment and record how you've
addressed it.

| # | Consideration | Why it matters | What you must do |
|---|---------------|----------------|------------------|
| 1 | **Encryption at rest** | Document text, uploaded files, trial results and ground truth are stored unencrypted by the application. | Provide encryption at the infrastructure layer: an encrypted database volume and encrypted object storage (SSE). See [DATA_FLOW.md](./DATA_FLOW.md). |
| 2 | **PHI egress to external LLM/OCR services** | Running a trial or remote OCR sends patient text/images to the configured endpoint — a data sub-processor. | Keep endpoints self-hosted/on-prem where possible; set `ALLOWED_LLM_ENDPOINTS` / `ALLOWED_OCR_ENDPOINTS` to your approved hosts; clear any external endpoint as a sub-processor and record it in your DPIA. Every egress is recorded in the audit log. |
| 3 | **Data retention & deletion** | Deletion is on-demand; there is no automatic retention/purge. | Define and operate a retention schedule; periodically delete data past its retention date. See [DATA_RETENTION.md](./DATA_RETENTION.md). |
| 4 | **Backups retain deleted data** | Deleting data in the app does not remove it from existing database/storage backups. | Apply a backup retention/rotation policy so deleted PHI ages out of backups on a defined schedule; encrypt backups. |
| 5 | **TLS termination** | The app serves plain HTTP behind a reverse proxy; it does not terminate TLS itself. | Terminate TLS at your reverse proxy, forward `X-Forwarded-Proto: https`, and set HSTS there. See [DEPLOY.md](../DEPLOY.md). |
| 6 | **`SECRET_KEY` protection** | The single `SECRET_KEY` signs tokens and derives the key that encrypts stored API keys / SSO secrets. | Generate a strong random value, store it securely (secrets manager / restricted `.env`), never commit it, and back it up — losing it invalidates encrypted secrets. |
| 7 | **Network exposure & rate limiting** | Auth endpoints are rate-limited, but there is no global request-rate limit. | If the app is reachable from untrusted networks, add a global rate limit / WAF at your reverse proxy and restrict `BACKEND_CORS_ORIGINS` to the exact public origin. |
| 8 | **Access model granularity** | A project is visible to its owner and to admins; there is no per-field or per-cohort access control. | Scope projects accordingly (one study/cohort per project as needed) and manage admin membership tightly. |
| 9 | **Orphaned storage on failed deletion** | Blob removal after a DB delete is best-effort; a storage failure can leave an orphaned file. | Periodically reconcile stored objects against `File.file_uuid` / `GroundTruth.file_uuid` and remove orphans. |
| 10 | **Log handling** | Application and audit logs contain no PHI, but they do contain identifiers, IPs and (in the error log) tracebacks. | Treat logs as sensitive: restrict access, and if you forward them to a SIEM/Loki, secure that pipeline. See [AUDIT_LOGGING.md](./AUDIT_LOGGING.md). |

## How to use this document

1. During deployment planning, work through each row and record your control +
   residual rating in your risk assessment / DPIA.
2. Re-check it when your deployment topology changes (new LLM endpoint, new
   storage backend, exposure to a wider network).
