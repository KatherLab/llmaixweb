# Task monitoring

**Celery Workers & Queues** (`/admin/celery`) monitors the background task system
that runs preprocessing and trials. A **Refresh** button in the header re-fetches
worker and queue state on demand; the page loads a snapshot on open and does not
auto-poll.

## Workers

Each worker card shows its **name**, an **Online/Offline** status pill, and, when
reported, its **pool** type (e.g. `prefork`, `solo`, `threads`), **concurrency**
(max concurrent tasks), and **process count**. Cards are derived from Celery's
`inspect.ping` and `inspect.stats` payloads.

If no workers respond, the section shows a "no workers" message — usually
meaning the Celery workers aren't running or can't reach the broker. Expand
**Show raw worker JSON** to see the full, unformatted inspection output for
debugging.

!!! note "Expected workers"
    LLMAIx Web runs workers for two queues — a `default` worker (general tasks,
    with the embedded Celery beat scheduler) and a `preprocess` worker (heavy
    OCR). Seeing both online is the healthy state. Their pool types depend on
    platform and `CELERY_*_POOL` configuration (for example `preprocess`
    defaults to `solo` on macOS and `prefork` elsewhere).

## Queues & tasks

The queue table shows **Active**, **Scheduled**, and **Reserved** counts per
queue:

- **Active** — tasks a worker is currently executing.
- **Scheduled** — tasks queued with a future ETA/countdown.
- **Reserved** — tasks a worker has prefetched but not yet started.

LLMAIx Web uses two queues: `default` (general tasks) and `preprocess` (heavy OCR
work). If no queue data is available, the table is replaced by a note.
**Show raw queue JSON** exposes the underlying `active`/`scheduled`/`reserved`
inspection payloads.

## Inspecting a task

Paste a **task ID** into the inspection field and **Inspect** to see its raw
detail (status and result payload) as JSON. If the task is still **PENDING**,
**STARTED**, or **RETRY**, a **Revoke / Terminate** button appears that cancels
it; after revoking, the queue counts refresh and a confirmation with the revoked
id is shown briefly.

!!! warning "Revoke is forceful"
    Revoke/terminate signals the worker to stop the task. For in-flight OCR or
    extraction this abandons the work rather than rolling it back cleanly; prefer
    the in-app cancel controls on a preprocessing task or trial (which support
    optional rollback) when they're available. Use this page's revoke mainly for
    stuck or orphaned tasks.

!!! tip
    Reach this page quickly from the header **activity bell** → **View all
    activity** (admins only).
