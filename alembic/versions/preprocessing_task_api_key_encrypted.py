"""Add api_key_encrypted to preprocessing_tasks

The OCR API key for a custom preprocessing backend (Mistral / Vision LLM OCR)
was previously stored as plaintext in ``preprocessing_tasks.task_metadata`` (a
JSON column), so anyone with DB read access — or a DB dump — could read it.
``Trial`` already stores its LLM key encrypted (Fernet) in
``api_key_encrypted``; this mirrors that pattern for ``PreprocessingTask``.

The key is now written via the ``PreprocessingTask.api_key`` property, which
encrypts on set and decrypts on read, so the plaintext never persists. Old
plaintext values left in ``task_metadata["api_key"]`` by prior runs are simply
ignored (they belong to already-finalized task rows).

Revision ID: ptask_api_key_enc
Revises: add_file_task_heartbeat
Create Date: 2026-06-20

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ptask_api_key_enc"
down_revision = "add_file_task_heartbeat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "preprocessing_tasks",
        sa.Column(
            "api_key_encrypted",
            sa.String(length=512),
            nullable=True,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("preprocessing_tasks", "api_key_encrypted")
