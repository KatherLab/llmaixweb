"""add token_version column to users table

Revision ID: f9a8b2c3d4e7
Revises: f9a8b2c3d4e6
Create Date: 2026-05-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a8b2c3d4e7"
down_revision: Union[str, None] = "f9a8b2c3d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
