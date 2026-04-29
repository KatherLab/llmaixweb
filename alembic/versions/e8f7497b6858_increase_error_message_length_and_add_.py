"""increase error_message length

Revision ID: e8f7497b6858
Revises: 2d2bfbbdcc04
Create Date: 2026-04-28 19:36:03.344429

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e8f7497b6858'
down_revision: Union[str, None] = '2d2bfbbdcc04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase error_message length from 1000 to 4000 characters
    op.alter_column(
        'file_preprocessing_tasks',
        'error_message',
        existing_type=sa.String(length=1000),
        type_=sa.String(length=4000),
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert error_message length back to 1000 characters
    op.alter_column(
        'file_preprocessing_tasks',
        'error_message',
        existing_type=sa.String(length=4000),
        type_=sa.String(length=1000),
        existing_nullable=True
    )
