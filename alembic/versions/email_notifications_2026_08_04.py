"""email notifications: preferences, user locale, job initiator

Adds:
- ``notification_preferences`` — per-user opt-outs for notification email. A
  user without a row uses ``NotificationPreference.DEFAULTS``, so existing
  accounts need no backfill.
- ``users.preferred_language`` — the UI locale, mirrored from the frontend
  language switcher so notification email can be rendered in it.
- ``trials.created_by_id`` / ``preprocessing_tasks.created_by_id`` — who started
  a run, so the "finished" notification reaches the initiator instead of every
  project member. NULL for pre-existing rows; those fall back to the owner.

Revision ID: email_notifications_2026_08_04
Revises: project_shares_2026_08_04
Create Date: 2026-08-04 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "email_notifications_2026_08_04"
down_revision: Union[str, None] = "project_shares_2026_08_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "job_finished", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "project_shared", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("security", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "admin_alerts", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "only_when_away", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("min_job_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
        unique=True,
    )

    op.add_column(
        "users", sa.Column("preferred_language", sa.String(length=5), nullable=True)
    )

    # `created_by_id` on both job tables. Named FK constraints so the SQLite
    # downgrade path (batch_alter_table) can drop them by name.
    with op.batch_alter_table("trials") as batch:
        batch.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_trials_created_by_id_users",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("preprocessing_tasks") as batch:
        batch.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_preprocessing_tasks_created_by_id_users",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("preprocessing_tasks") as batch:
        batch.drop_constraint(
            "fk_preprocessing_tasks_created_by_id_users", type_="foreignkey"
        )
        batch.drop_column("created_by_id")

    with op.batch_alter_table("trials") as batch:
        batch.drop_constraint("fk_trials_created_by_id_users", type_="foreignkey")
        batch.drop_column("created_by_id")

    op.drop_column("users", "preferred_language")

    op.drop_index(
        "ix_notification_preferences_user_id", table_name="notification_preferences"
    )
    op.drop_table("notification_preferences")
