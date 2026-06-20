"""Rename trials.api_key -> api_key_encrypted

The Trial model now stores the LLM API key encrypted (Fernet) in a column
named ``api_key_encrypted`` and exposes it as a plain ``api_key`` property
that decrypts on read / encrypts on write. Existing rows already hold
Fernet tokens (written by the former ``@validates("api_key")`` hook), so this
is a pure column rename — the data is preserved and decrypts correctly under
the new property.

Batch mode is used so the rename works on both PostgreSQL (pass-through) and
SQLite (table rebuild, which is required for column renames there).

Revision ID: rename_trial_apikey
Revises: add_fk_indexes_2026_06_19
Create Date: 2026-06-20

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "rename_trial_apikey"
down_revision = "add_fk_indexes_2026_06_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.alter_column(
            "api_key",
            new_column_name="api_key_encrypted",
            existing_type=sa.String(length=512),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.alter_column(
            "api_key_encrypted",
            new_column_name="api_key",
            existing_type=sa.String(length=512),
            nullable=False,
        )
