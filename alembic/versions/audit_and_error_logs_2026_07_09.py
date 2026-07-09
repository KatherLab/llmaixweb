"""add audit_logs and error_logs (append-only accountability + central error log)

Introduces the accountability substrate for clinical deployment:

  - audit_logs: append-only "who did what, when, from where" trail covering
    authentication, PHI access, data mutations, external egress, and admin
    changes. Populated only by ``utils.audit.record_audit``; no update/delete
    path exists in the app.
  - error_logs: one row per unhandled server error, keyed by the user-facing
    error id (the request correlation id) so an admin can look up the id a user
    reported and see the full traceback.

Neither table stores PHI. Both FK to users.id with ON DELETE SET NULL so the
history survives account removal (with an email snapshot for readability).

Revision ID: audit_error_logs_2026_07_09
Revises: trial_project_number
Create Date: 2026-07-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "audit_error_logs_2026_07_09"
down_revision: Union[str, None] = "trial_project_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_email", sa.String(length=254), nullable=True),
        sa.Column("actor_ip", sa.String(length=45), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_project_id", "audit_logs", ["project_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index(
        "ix_audit_logs_project_created", "audit_logs", ["project_id", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"]
    )

    op.create_table(
        "error_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("error_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_email", sa.String(length=254), nullable=True),
        sa.Column("method", sa.String(length=8), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("exception_type", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("traceback", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_error_logs_error_id", "error_logs", ["error_id"], unique=True
    )
    op.create_index("ix_error_logs_created_at", "error_logs", ["created_at"])
    op.create_index("ix_error_logs_request_id", "error_logs", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_error_logs_request_id", table_name="error_logs")
    op.drop_index("ix_error_logs_created_at", table_name="error_logs")
    op.drop_index("ix_error_logs_error_id", table_name="error_logs")
    op.drop_table("error_logs")

    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_project_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_project_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
