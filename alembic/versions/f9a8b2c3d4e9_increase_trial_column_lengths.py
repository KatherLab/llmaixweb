"""increase trial llm_model, api_key, base_url column lengths

Revision ID: f9a8b2c3d4e9
Revises: f9a8b2c3d4e8
Create Date: 2026-05-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a8b2c3d4e9"
down_revision: Union[str, None] = "f9a8b2c3d4e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("trials", "llm_model", type_=sa.String(255), existing_type=sa.String(100))
    op.alter_column("trials", "api_key", type_=sa.String(512), existing_type=sa.String(100))
    op.alter_column("trials", "base_url", type_=sa.String(512), existing_type=sa.String(100))


def downgrade() -> None:
    op.alter_column("trials", "llm_model", type_=sa.String(100), existing_type=sa.String(255))
    op.alter_column("trials", "api_key", type_=sa.String(100), existing_type=sa.String(512))
    op.alter_column("trials", "base_url", type_=sa.String(100), existing_type=sa.String(512))
