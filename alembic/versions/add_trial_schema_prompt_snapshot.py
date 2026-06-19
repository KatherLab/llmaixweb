"""add schema_snapshot and prompt_snapshot to trials

Stores frozen copies of the schema + prompt used for a trial so the record
stays accurate even if the source schema/prompt is edited afterwards.

Revision ID: add_trial_schema_prompt_snapshot
Revises: a1b2c3d4e5f6
Create Date: 2026-06-19

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_trial_schema_prompt_snapshot"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trials", sa.Column("schema_snapshot", sa.JSON(), nullable=True))
    op.add_column("trials", sa.Column("prompt_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trials", "prompt_snapshot")
    op.drop_column("trials", "schema_snapshot")
