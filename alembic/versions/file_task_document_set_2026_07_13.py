"""add document_set_id to file_preprocessing_tasks

Revision ID: file_task_doc_set_2026_07_13
Revises: audit_error_logs_2026_07_09
Create Date: 2026-07-13 00:00:00.000000

Links a row-by-row CSV/XLSX file task to its auto-generated document set so the
UI can deep-link to the group viewer instead of the first document.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "file_task_doc_set_2026_07_13"
down_revision: Union[str, None] = "audit_error_logs_2026_07_09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("file_preprocessing_tasks") as batch_op:
        batch_op.add_column(sa.Column("document_set_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_file_preprocessing_tasks_document_set_id",
            "document_sets",
            ["document_set_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("file_preprocessing_tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_file_preprocessing_tasks_document_set_id", type_="foreignkey"
        )
        batch_op.drop_column("document_set_id")
