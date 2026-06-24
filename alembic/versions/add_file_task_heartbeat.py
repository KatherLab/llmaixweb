"""Add last_heartbeat_at to file_preprocessing_tasks

The orphan sweeper previously used ``started_at`` to decide a file task's
worker was dead: any PENDING/IN_PROGRESS task with ``started_at`` older than
30 minutes was marked FAILED. Per-file OCR timeouts can be configured up to
two hours, so a slow-but-legitimate file whose timeout exceeds the sweeper
cutoff was wrongly marked FAILED while still processing (the worker would
then overwrite it with COMPLETED, leaving the parent FAILED).

This adds ``last_heartbeat_at``, which the pipeline bumps every few seconds
while actively processing. The sweeper now treats a stale
``last_heartbeat_at`` (falling back to ``started_at`` for pre-existing rows
that have never heartbeated) as the dead-worker signal, so legitimately slow
files are no longer killed.

Revision ID: add_file_task_heartbeat
Revises: trial_docset_setnull
Create Date: 2026-06-20

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_file_task_heartbeat"
down_revision = "trial_docset_setnull"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "file_preprocessing_tasks",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("file_preprocessing_tasks", "last_heartbeat_at")
