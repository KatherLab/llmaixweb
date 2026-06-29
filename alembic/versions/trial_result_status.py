"""Add status column to trial_results

Trial results previously had no first-class status: success/failure was derived
from `result IS NULL` plus `additional_content->>'status'` (a JSON string set by
`_determine_result_status` in `utils/info_extraction.py`). Filtering and counting
by outcome therefore required JSON inspection.

This adds a real, indexed `status` column (String, native_enum=False to match the
`TrialStatus` convention) and backfills it from the existing JSON status so
legacy rows are correct. The extraction write path (`_store_result`) now sets the
column alongside the JSON field. The column is nullable so the migration is safe
even if some rows have no `additional_content.status`.

Revision ID: trial_result_status
Revises: invitation_expiry
Create Date: 2026-06-29

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "trial_result_status"
down_revision: Union[str, None] = "invitation_expiry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trial_results",
        sa.Column("status", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_trial_results_status", "trial_results", ["status"])

    # Backfill from the JSON status that's already being written. PostgreSQL and
    # SQLite both support `->>` for JSON columns, but the column type differs
    # (JSONB on postgres, JSON on sqlite) — the `->>'status'` operator works on
    # both. Guard with a dialect check to avoid surprising behavior on other DBs.
    bind = op.get_bind()
    if bind.dialect.name in ("postgresql", "sqlite"):
        bind.execute(
            sa.text(
                "UPDATE trial_results SET status = additional_content->>'status' "
                "WHERE status IS NULL AND additional_content IS NOT NULL "
                "AND additional_content->>'status' IS NOT NULL"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_trial_results_status", table_name="trial_results")
    op.drop_column("trial_results", "status")
