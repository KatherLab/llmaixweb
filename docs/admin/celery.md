# Task monitoring

**Celery Workers & Queues** (`/admin/celery`) monitors the background task system
that runs preprocessing and trials.

## Workers

Each worker card shows its name, **Online/Offline** status, pool type,
concurrency, and process count. Expand a card to see the raw worker JSON.

## Queues & tasks

The queue table shows **Active**, **Scheduled**, and **Reserved** counts per
queue. LLMAIx Web uses two queues: `default` (general tasks) and `preprocess`
(heavy OCR work).

## Inspecting a task

Paste a **task ID** to see its raw detail. If the task is still pending, started,
or retrying, a **Revoke / Terminate** button lets you cancel it.

!!! tip
    Reach this page quickly from the header **activity bell** → **View all
    activity** (admins only).
