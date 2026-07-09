# Data Retention & Deletion

LLMAIx Web performs deletion **on demand**; it does not currently automate
retention windows. This document describes the deletion mechanics, what they
cover, and the operational process to keep data minimised in a clinical setting.

## What deletion covers

Deleting a **project** (or a **user**, which cascades their projects) removes:

- All DB rows for the project: files, documents, document sets, preprocessing
  tasks/configs, schemas, prompts, trials + results, ground truth, evaluations +
  metrics (SQLAlchemy `cascade="all, delete-orphan"` + FK `ON DELETE`).
- The stored **bytes** for uploaded files and ground-truth files in local/S3
  storage (`remove_file`), performed after the DB commit.

Finer-grained deletes exist for individual files, documents, trials, ground
truth, and evaluations.

> **Accountability is preserved.** The append-only audit trail records the
> deletion (actor, resource, count of blobs removed) and retains an actor email
> snapshot even after the user is deleted. Audit rows are not removed by
> application deletes — see "Pruning the audit trail" below.

## Known gaps to compensate for operationally

1. **No scheduled auto-purge.** Establish a retention schedule (e.g. delete
   project data N months after study completion) and action it via the admin UI
   or an operational runbook.
2. **Best-effort blob removal.** If a storage delete fails, the DB row is
   already gone and the failure is logged; periodically reconcile storage keys
   against `File.file_uuid` / `GroundTruth.file_uuid` and remove orphans.
3. **Backups retain deleted data.** Deletion does not rewrite historical
   database/storage backups. Apply your backup retention/rotation policy so that
   deleted PHI ages out of backups on a defined schedule.

## Recommended retention process

1. **Classify** each project with a study id and a retention end date at intake.
2. **Minimise** — prefer self-hosted OCR/LLM so PHI never leaves; delete raw
   uploads once documents are extracted if the source is no longer needed.
3. **Review** on a schedule (e.g. quarterly): list projects past their retention
   date and delete them.
4. **Verify** deletion via the audit log (filter `action=delete`,
   `resource_type=project`) and by reconciling storage.
5. **Age out backups** per your backup rotation so deleted PHI is not retained
   indefinitely in snapshots.

## Pruning the audit trail

The audit and error tables grow over time and are intentionally not deletable
from the application. If your retention policy requires pruning them, do so at
the database layer (e.g. delete `audit_logs`/`error_logs` rows older than your
audit-retention window) as a controlled DBA operation, and prefer forwarding the
records to an external archive first (see [AUDIT_LOGGING.md](./AUDIT_LOGGING.md)).

## Subject-access / erasure requests

To fully remove an individual's data: identify the owning project(s), export any
required records first, delete the project(s)/user, reconcile storage, and let
the deletion age out of backups. Record the action (it is captured in the audit
trail) for your governance evidence.
