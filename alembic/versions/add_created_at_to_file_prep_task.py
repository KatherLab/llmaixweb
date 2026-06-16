"""add created_at to file_preprocessing_task

Revision ID: a1b2c3d4e5f6
Revises: add_perf_indexes_2026_06_16
Create Date: 2026-06-16

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "add_perf_indexes_2026_06_16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at column to file_preprocessing_tasks table
    op.add_column(
        "file_preprocessing_tasks",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Remove created_at column from file_preprocessing_tasks table
    op.drop_column("file_preprocessing_tasks", "created_at")
