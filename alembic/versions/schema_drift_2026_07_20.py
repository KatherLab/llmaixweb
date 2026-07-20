"""align schema with models: app_settings.updated_at NOT NULL

Revision ID: schema_drift_2026_07_20
Revises: fk_indexes_2026_07_17
Create Date: 2026-07-20 00:00:00.000000

Closes the model↔migration drift reported by `alembic check`:
- app_settings.updated_at is non-nullable on the model (Mapped[datetime],
  always populated via server_default) but the initial migration created it
  nullable.

The other drift `alembic check` flagged (a redundant single-column index on
documents.is_latest, from a stray index=True on the column) was resolved in the
model instead — the column already has the ix_documents_latest index declared
explicitly in __table_args__, so no second index is created here.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "schema_drift_2026_07_20"
down_revision: Union[str, None] = "fk_indexes_2026_07_17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE app_settings SET updated_at = now() WHERE updated_at IS NULL")
    op.alter_column(
        "app_settings",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "app_settings",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
