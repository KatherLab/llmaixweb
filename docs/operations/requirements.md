# Requirements & sizing

Hardware guidance for an LLMAIx Web deployment.

!!! summary "Bottom line"
    For hosted OCR and LLM services, 8 GB system RAM can be enough for
    evaluation. When running local CPU Docling alongside the full LLMAIx Web
    stack, use **16 GB system RAM** as the practical minimum and **24–32 GB** for
    a more robust deployment. The default 8 GB Docling container memory limit is
    a safety ceiling, not its normal memory footprint.

## What drives load

Size on these, not on login count:

- **OCR locality** — local OCR (docling-serve or a self-hosted GPU model) is the
  heaviest part of the stack. Against hosted OCR/LLM APIs the core stack is light.
- **Concurrent processing jobs** — preprocessing and extraction run as Celery
  background jobs, largely serialized per worker.
- **Document volume** — object storage and Postgres grow with cumulative files,
  extracted text, and trial results.

## Minimum

Depends on whether OCR runs locally.

**Hosted OCR + hosted LLM APIs** (no local Docling):

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU | 4 cores | 8 cores |
| System RAM | 8 GB | 16 GB |
| Disk | 20 GB SSD | 50+ GB SSD |
| GPU | none | none |

**Local CPU `docling-serve`:**

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU | 8 cores | 8+ cores |
| System RAM | 16 GB | 24–32 GB (larger / OCR-heavy documents) |
| Disk | 50 GB SSD | 100+ GB SSD |
| GPU | none | none |

The `docling-serve` container sets a **container memory limit** of `8g`. This is
a protective ceiling to contain pathological or unusually large jobs — it is not
reserved memory and not a measured steady-state requirement. Actual consumption
is workload-dependent and commonly a few GB.

An 8 GB hosted-only deployment assumes the local Docling service is **not
running**. `DOCLING_SERVE_ENABLED=false` only stops the application from calling
Docling — the `docling-serve` container still starts under the base
`compose.yml` and consumes system RAM. To reclaim it, use a deployment profile or
Compose override that omits the `docling-serve` service.

## Component footprint

Base `compose.yml` services under light load:

| Service | Role | System RAM | Notes |
| --- | --- | --- | --- |
| `frontend` | nginx + SPA | ~50–100 MB | Static. |
| `backend` | FastAPI API | ~300–600 MB | |
| `worker_default` | Celery general queue + beat | ~0.4–1 GB | Keep at 1 replica (holds beat). |
| `worker_preprocess` | Celery OCR/preprocess queue | workload-dependent | CPU-heavy during OCR. |
| `docling-serve` | CPU OCR / conversion | workload-dependent; commonly a few GB, capped at 8 GB by default | Depends on page count, scan resolution, OCR, tables, images, and complexity. Tune `DOCLING_CPU_THREADS`. |
| `postgres` | Database | ~0.2–1 GB+ | Grows with text + results. |
| `redis` | Broker + pub/sub | ~50–200 MB | |
| `rustfs` | S3 storage | ~0.1–0.3 GB | Disk grows with volume. |

!!! note
    These memory figures are indicative sizing estimates, not formal benchmarks.
    Measure representative documents before setting production limits. The default
    8 GB Docling container limit is intended to contain pathological or unusually
    large jobs.

## Sizing by workload

Assumes hosted LLM extraction. "Users" is a proxy for concurrent processing jobs,
not a direct driver of memory.

| Scenario | ~Users | Concurrent jobs | OCR | Host |
| --- | --- | --- | --- | --- |
| Evaluation / single user | 1–3 | 1 | Hosted API | 4 cores / 8–16 GB / 20 GB |
| Small team | 5–15 | 1–2 | Hosted API | 8 cores / 16 GB / 100 GB |
| Small team | 5–15 | 1–2 | Local CPU Docling | 8 cores / 16–32 GB / 100 GB |
| Department | 15–50 | 2–4 | Local CPU Docling or GPU | 16 cores / 32–64 GB / 250+ GB |
| Heavy / batch | 50+ | 4+ | GPU | 16+ cores / 64+ GB / 500+ GB + GPU |

Self-hosting the LLM adds the GPU requirements below on top.

## GPU (self-hosted OCR / LLM)

Only needed for the optional overlays. Requires an NVIDIA GPU + NVIDIA Container
Toolkit. Model weights download to `~/.cache/huggingface` (tens of GB per model).
vLLM also uses host **shared memory** (`shm_size: 8gb`).

| Overlay | Purpose | VRAM |
| --- | --- | --- |
| `compose.deepseek.yml` | Local OCR (DeepSeek-OCR-2 + KatDocExtract) | 8 GB min, 12+ GB for concurrency |
| `compose.vllm.yml` | Local OpenAI-compatible LLM (extraction / vision OCR) | model-dependent |

VRAM for `compose.vllm.yml`, bf16 weights:

- **Gemma 4 E4B** — 24 GB
- **Gemma 4 31B-it** — 96 GB (original bf16 weights)

Quantized (4-bit) weights roughly halve VRAM; the KV cache adds headroom on top,
scaling with context length and concurrency. `VLLM_TENSOR_PARALLEL_SIZE` spreads
a model across multiple GPUs. Running both overlays means two vLLM instances —
size for both or split across GPUs/hosts.

## Benchmarking Docling memory

Set the container memory limit from measurement, not the default. Process
representative documents and watch peak usage:

```bash
docker stats docling-serve   # or: podman stats docling-serve
```

Cover these cases:

- small born-digital PDF
- scanned PDF (OCR)
- table-heavy PDF
- the largest document you permit
- several documents processed sequentially (retained memory can exceed
  single-document peaks)

Set the production container memory limit to the **worst observed peak + ~25%
headroom**. The limit is configurable in Compose:

```yaml
mem_limit: ${DOCLING_MEMORY_LIMIT:-8g}
```

Lowering to 6 GB may be reasonable after testing; 4 GB is likely too restrictive
for OCR-heavy documents.

## Production caveats

- A container memory limit triggers an **OOM kill** when exceeded — size it above
  the measured peak.
- The OS and the rest of the LLMAIx stack need their own system RAM on top of
  Docling's limit.
- Test **sequentially**: memory retained across documents can differ from a
  single document's peak.
- Configure page limits and `MAX_UPLOAD_SIZE_BYTES` to prevent pathological jobs.
- Keep **20–30% system-RAM headroom** in production.

## Storage growth

- **Object storage (rustfs / S3)** — uploaded files plus generated artifacts
  (per-page OCR images, row-split CSV documents). Budget corpus size × a
  multiple.
- **Postgres** — extracted text, trial results, evaluation metrics, audit/error
  logs. Smaller than object storage but keep on SSD and back up.

Both grow with cumulative usage. See [Data retention](../DATA_RETENTION.md) and
[Backup & restore](backup-restore.md).

## Scaling levers

In order of impact:

1. Offload OCR/LLM to hosted APIs (omit `docling-serve`, point base URLs at the provider).
2. Scale `worker_preprocess` replicas/concurrency. Keep `worker_default` at 1 (beat).
3. Raise `DOCLING_CPU_THREADS` toward physical core count.
4. Move Postgres to a dedicated host / managed service.
5. Use managed Redis and S3 instead of the bundled sidecars.
6. Run the vLLM overlays on separate GPU nodes; point base URLs at them.

## See also

- [Configuration](configuration.md) — tuning knobs.
- [OCR engines](../user-guide/ocr-engines.md) — local vs. hosted OCR.
- [Deployment](deployment.md) — production hardening.
