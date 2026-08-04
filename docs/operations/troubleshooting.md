# Troubleshooting

Common issues when running LLMAIx Web with Docker Compose.

## Port 5173 already in use

The frontend binds to `5173:8080`. Change the host port in `compose.yml`:

```yaml
ports: ["5174:8080"]
```

## Backend won't start / "Connection refused" errors

The backend waits for Postgres, Redis, RustFS, and docling-serve to be healthy.
Ensure they're up:

```bash
docker compose ps                    # check all services are running
docker compose logs backend | tail   # check backend logs
docker compose logs postgres | tail  # check database logs
```

## "OpenAI API connection failed"

Your `.env` has `OPENAI_API_KEY` / `OPENAI_API_BASE` / `OPENAI_API_MODEL` empty
or unreachable. These are required for extraction. To skip the startup check
(e.g. if you configure providers in the admin UI later), set:

```bash
OPENAI_NO_API_CHECK=true
```

## Database migration errors

Migrations run automatically when the schema changes between versions. If needed,
reset the database (⚠️ **destroys all data**):

```bash
docker compose down -v        # removes volumes including pgdata
docker compose up -d          # fresh start
```

## Slow preprocessing / stuck tasks

Celery workers may not be starting. Check:

```bash
docker compose logs worker_default
docker compose logs worker_preprocess
```

On macOS, multiprocessing issues can occur — set `CELERY_PREPROCESS_POOL=solo`
in `.env`.

## Every document in an extraction run fails with "is a required property"

The model returned JSON that your endpoint's structured output considered valid,
but that LLMAIx rejected. Almost always the schema lists a field in `required`
that is not defined in `properties` (typically after a hand-edit or rename):
constrained decoding builds its grammar from `properties` and ignores the orphan
entry, so the field can never appear in the output.

Open the schema and fix the `required` list — saving now rejects this, and the
error message names the field. Note that an extraction run freezes a **snapshot** of the
schema at creation time, so a running or completed run keeps the broken copy;
create a new extraction run after fixing the schema.

## Extraction results come back truncated ("incomplete")

The model hit its completion-token cap. LLMAIx retries such a call once with a
larger budget automatically; if the retry is still cut off, the result is stored
as `incomplete` with the partial output and tuning advice attached. Raise
**max_completion_tokens** in the extraction run's advanced settings, lower
**reasoning_effort** if the model emits long reasoning traces, or trim the schema
(fewer fields, shorter descriptions) so less output is needed.

## Still stuck?

Open an issue at
[github.com/KatherLab/llmaixweb/issues](https://github.com/KatherLab/llmaixweb/issues).
