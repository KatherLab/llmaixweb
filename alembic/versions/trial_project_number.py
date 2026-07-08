"""per-project trial numbering (trials.project_trial_number)

Adds a per-project sequence number to each trial so the UI display fallback
reads "Trial #N" with N counted within the project, instead of the global
autoincrement `id` (which reflects every trial ever created across every
project and is meaningless to users).

The number is assigned at creation as MAX(project_trial_number)+1 within the
project, and enforced unique per project via uq_trials_project_number. It's
stable across deletions (gaps, not renumbering).

This migration:
  1. adds trials.project_trial_number (nullable first, so existing rows can
     be populated before the NOT NULL constraint is applied);
  2. backfills existing rows with a per-project 1-based sequence ordered by
     created_at, id (Postgres window function; SQLite falls back to a
     per-project Python loop since its window-function support is version-
     dependent and the dev backend should not depend on it);
  3. applies NOT NULL;
  4. creates the unique constraint.

Downgrade reverses the four steps.

Revision ID: trial_project_number
Revises: fix_ts_defaults_2026_07_07
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "trial_project_number"
down_revision: Union[str, None] = "fix_ts_defaults_2026_07_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column nullable so existing rows can be backfilled.
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("project_trial_number", sa.Integer(), nullable=True)
        )

    bind = op.get_bind()

    # 2. Backfill a per-project 1-based sequence ordered by created_at, id.
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE trials
                SET project_trial_number = sub.rn
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY project_id
                               ORDER BY created_at, id
                           ) AS rn
                    FROM trials
                ) AS sub
                WHERE trials.id = sub.id
                """
            )
        )
    else:
        # SQLite (dev): avoid relying on window-function support. Assign a
        # 1-based sequence per project, ordered by created_at, id.
        rows = bind.execute(
            sa.text(
                "SELECT id, project_id FROM trials ORDER BY project_id, created_at, id"
            )
        ).fetchall()

        per_project_counter: dict[int, int] = {}
        for row in rows:
            project_id = row[1]
            per_project_counter[project_id] = per_project_counter.get(project_id, 0) + 1
            bind.execute(
                sa.text("UPDATE trials SET project_trial_number = :n WHERE id = :id"),
                {"n": per_project_counter[project_id], "id": row[0]},
            )

    # 3. Apply NOT NULL now that every row has a value.
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.alter_column(
            "project_trial_number",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # 4. Enforce uniqueness per project.
    op.create_unique_constraint(
        "uq_trials_project_number", "trials", ["project_id", "project_trial_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_trials_project_number", "trials", type_="unique")

    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.alter_column(
            "project_trial_number",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.drop_column("project_trial_number")
