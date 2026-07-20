# Upgrading

The frontend and backend are shipped as **separate Docker images** and can be
updated independently.

## Before you upgrade

1. **Read the [changelog](https://github.com/KatherLab/llmaixweb/blob/main/CHANGELOG.md)**
   for the versions between your current and target release — note any breaking
   changes.
2. **Back up first** — take a database and object-storage backup. See
   [Backup & restore](backup-restore.md).
3. **Check pinned versions** — for reproducible clinical deployments, pin image
   tags (e.g. `:0.6.8`) rather than `:latest`.

## Performing the upgrade

```bash
docker compose -f compose.yml pull
docker compose -f compose.yml up -d
```

**Database migrations run automatically** on backend container startup (Alembic).
Watch the backend logs to confirm migrations applied cleanly before directing
traffic to the new version.

## Rolling back

If an upgrade fails, redeploy the previous image tags. Because migrations may
have already run, restore the database from the backup you took **before** the
upgrade if the schema changed. This is why the pre-upgrade backup is not
optional.

## Version information

The running frontend and backend versions (with git commit hashes on hover) are
shown in the application footer, so you can confirm what is deployed.
