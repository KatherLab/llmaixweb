"""add warnings field to file_preprocessing_tasks

Revision ID: f9a8b2c3d4e5
Revises: e8f7497b6858
Create Date: 2026-04-28 19:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f9a8b2c3d4e5'
down_revision: Union[str, None] = 'e8f7497b6858'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add warnings column to file_preprocessing_tasks table
    op.add_column(
        'file_preprocessing_tasks',
        sa.Column('warnings', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove warnings column from file_preprocessing_tasks table
    op.drop_column('file_preprocessing_tasks', 'warnings')
