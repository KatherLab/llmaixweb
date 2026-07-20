# Backup & restore

LLMAIx Web keeps state in two places. **Both** must be backed up together to get
a consistent restore point:

1. **The database** (PostgreSQL in production) — projects, files metadata,
   documents, schemas, prompts, trials, results, evaluations, users, settings.
2. **Object / file storage** — the actual uploaded files and generated
   artifacts, stored either in the local storage directory or an S3-compatible
   bucket under UUID-based filenames.

!!! warning "Keep the two in sync"
    The database references stored files by UUID. A database backup without the
    matching file storage (or vice versa) will restore to a broken state with
    dangling references. Snapshot both as close together as possible.

## Database backup

For PostgreSQL:

```bash
pg_dump --format=custom --file=llmaixweb-$(date +%F).dump "$DATABASE_URL"
```

Restore into an empty database:

```bash
pg_restore --clean --if-exists --dbname "$DATABASE_URL" llmaixweb-YYYY-MM-DD.dump
```

## File storage backup

- **Local storage** — back up the configured storage directory (e.g. with
  `tar`, `rsync`, or a filesystem snapshot).
- **S3-compatible** — enable bucket versioning and/or replicate the bucket
  (`aws s3 sync`, or your provider's backup tooling).

## Restore procedure

1. Stand up the app pointed at an **empty** database and storage location.
2. Restore the **file storage** first.
3. Restore the **database** from the matching dump.
4. Start the backend — Alembic will confirm the schema matches the app version.
   Restore a dump only into the app version it was taken from (or newer, letting
   migrations run forward).

## Retention

Align backup retention with your institution's
[data-retention policy](../DATA_RETENTION.md) and DPIA. Backups of clinical data
are themselves in scope for information governance.
