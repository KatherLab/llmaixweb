"""add_document_ids_to_file_preprocessing_task

Revision ID: bfa301b18a99
Revises: f9a8b2c3d4e9
Create Date: 2026-06-10 17:15:41.273309

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bfa301b18a99"
down_revision: Union[str, None] = "f9a8b2c3d4e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add document_ids column to file_preprocessing_tasks table
    op.add_column(
        "file_preprocessing_tasks", sa.Column("document_ids", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove document_ids column from file_preprocessing_tasks table
    op.drop_column("file_preprocessing_tasks", "document_ids")
