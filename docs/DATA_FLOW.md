# Data Flow & PHI Map

Where patient data (PHI) lives in LLMAIx Web and every point at which it can
leave the system. Use this with your DPIA to identify sub-processors and
mitigations.

## Trust boundaries

```
   ┌──────────────────────────── Clinic network (trusted) ─────────────────────────────┐
   │                                                                                    │
   │  Browser ──TLS──► Reverse proxy ──► nginx (SPA) ──► FastAPI backend                │
   │                                          │             │                           │
   │                                          │             ├─► PostgreSQL (PHI: text)   │
   │                                          │             ├─► Object/local storage     │
   │                                          │             │     (PHI: uploaded files)  │
   │                                          │             ├─► Redis (Celery broker)     │
   │                                          │             └─► Celery workers            │
   │                                                                     │               │
   └─────────────────────────────────────────────────────────────────────┼─────────────┘
                                                                          │
                        PHI EGRESS (deliberate, audited) ─────────────────┤
                                                                          ▼
                    ┌───────────────────────────────────────────────────────────────┐
                    │ External / self-hosted services (sub-processors):             │
                    │  • LLM extraction endpoint (OpenAI-compatible)                │
                    │  • Remote OCR (Mistral / Vision LLM) — off by default         │
                    └───────────────────────────────────────────────────────────────┘
```

## Where PHI is stored

| Data | Location | At rest | Notes |
|------|----------|---------|-------|
| Uploaded files (PDF/image/CSV…) | Local dir or S3, UUID filename | **Plaintext** — operator must encrypt volume/bucket | `File` model |
| Extracted document text | PostgreSQL `documents.text` | **Plaintext** — operator must encrypt DB volume | The text sent to the LLM |
| Trial results | PostgreSQL `trial_results.result` (JSON) | Plaintext | Extracted structured values |
| Ground truth | PostgreSQL `ground_truth.data_cache` + original file | Plaintext | Uploaded reference values |
| Evaluation metrics | PostgreSQL `evaluation_metrics.*_value` | Plaintext | Predicted/GT values per field |

> **The application does not encrypt PHI at rest.** Provide encryption at the
> infrastructure layer (encrypted DB volume, encrypted object storage). This is
> a hard deployment requirement for a clinical setting.

## Where PHI can leave

| Egress point | Trigger | Control | Audited as |
|--------------|---------|---------|-----------|
| **LLM extraction** | Running a trial | SSRF-validated endpoint; no redirect-follow; keep self-hosted | `llm_extraction_call` (host + model + doc count) |
| **Remote OCR** | Preprocessing with Mistral/Vision OCR or a custom endpoint | Off by default (`REMOTE_OCR_FALLBACK_ENABLED=false`); SSRF-validated + optional `ALLOWED_OCR_ENDPOINTS` allowlist | `ocr_external_call` (engine + host + file count) |
| **Document/file download** | User downloads a document, ZIP, or report | AuthZ (owner/admin); audited | `document_download` / `export` |
| **Audit export** | Admin exports the audit CSV | Admin-only; the export itself is audited | `export` |
| **Email** | Invitation / password-reset mail | Contains links + email address, not clinical PHI | — |

## Controls on egress

- **Keep it local.** Point `OPENAI_API_BASE`, `MISTRAL_API_BASE`, and
  `VISION_OCR_API_BASE` at self-hosted, on-premise services (see the
  `compose.vllm.yml` / `compose.deepseek.yml` overlays). Only enable a remote
  provider after clearing it as a permitted sub-processor.
- **SSRF guardrails.** User-supplied endpoints are validated
  (`backend/src/utils/url_safety.py`) to block cloud-metadata hosts and
  non-HTTP(S) schemes; extraction clients disable redirect following.
- **Egress allowlist.** Optionally restrict LLM/OCR destinations to an approved
  set of hosts via `ALLOWED_LLM_ENDPOINTS` / `ALLOWED_OCR_ENDPOINTS` — a trial or
  OCR run pointed anywhere else is rejected with a 400.
- **Accountability.** Every LLM egress is recorded in the audit log with the
  destination host, model, and document count (never content). See
  [AUDIT_LOGGING.md](./AUDIT_LOGGING.md).
- **No PHI in logs.** Application logs, the audit trail, and the error log never
  contain document text or extracted values.
