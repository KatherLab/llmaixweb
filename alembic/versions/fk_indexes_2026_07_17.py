"""add missing FK indexes for delete/orphan/sweeper hot paths

Revision ID: fk_indexes_2026_07_17
Revises: file_task_doc_set_2026_07_13
Create Date: 2026-07-17 00:00:00.000000

Single-column indexes for FK lookups the existing composite indexes can't
serve: preprocessed-file orphan checks, per-task document loads, trial→set
reference guards, and the orphan sweeper's periodic scan by file-task status.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fk_indexes_2026_07_17"
down_revision: Union[str, None] = "file_task_doc_set_2026_07_13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_preprocessed_file_id",
        "documents",
        ["preprocessed_file_id"],
    )
    op.create_index(
        "ix_documents_file_preprocessing_task_id",
        "documents",
        ["file_preprocessing_task_id"],
    )
    op.create_index(
        "ix_trials_document_set_id",
        "trials",
        ["document_set_id"],
    )
    op.create_index(
        "ix_file_preprocessing_tasks_status",
        "file_preprocessing_tasks",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_preprocessing_tasks_status", "file_preprocessing_tasks")
    op.drop_index("ix_trials_document_set_id", "trials")
    op.drop_index("ix_documents_file_preprocessing_task_id", "documents")
    op.drop_index("ix_documents_preprocessed_file_id", "documents")
