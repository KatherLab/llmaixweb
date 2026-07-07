"""add password_reset_tokens table

Revision ID: f9a8b2c3d4e8
Revises: f9a8b2c3d4e7
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a8b2c3d4e8"
down_revision: Union[str, None] = "f9a8b2c3d4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_token"),
        "password_reset_tokens",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_password_reset_tokens_token"),
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")
