"""project sharing: project_shares table

Grants a non-owner user read or write access to a project. One row per
(project, collaborator); the owner is not represented here (ownership stays on
``projects.owner_id``).

Revision ID: project_shares_2026_08_04
Revises: schema_drift_2026_07_20
Create Date: 2026-08-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "project_shares_2026_08_04"
down_revision: Union[str, None] = "schema_drift_2026_07_20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "permission",
            sa.Enum("READ", "WRITE", name="projectpermission", native_enum=False,
                    length=10),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "user_id", name="uq_project_share_project_user"
        ),
    )
    op.create_index(
        "ix_project_shares_project_id", "project_shares", ["project_id"], unique=False
    )
    op.create_index(
        "ix_project_shares_user_id", "project_shares", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_project_shares_user_id", table_name="project_shares")
    op.drop_index("ix_project_shares_project_id", table_name="project_shares")
    op.drop_table("project_shares")
