"""Combined (derived) documents

Revision ID: combined_documents_2026_08_07
Revises: email_notifications_2026_08_04
Create Date: 2026-08-07 00:00:00.000000

Multi-document extraction support: several documents of one patient can be
merged into a single "combined" document whose text is the concatenation of
its sources. Combined documents are ordinary Document rows so the whole
downstream pipeline (trials, results, evaluation) works unchanged.

- documents.original_file_id and documents.preprocessing_config_id become
  nullable: combined documents have no single backing file or preprocessing
  configuration.
- New document_source_association table records which source documents a
  combined document was built from (ordered via `position`). Deleting either
  side removes only the link; the combined document keeps its materialized
  text.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "combined_documents_2026_08_07"
down_revision: Union[str, None] = "email_notifications_2026_08_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table keeps this portable to the SQLite dev backend (which
    # can't ALTER a column's nullability in-place and needs a table rebuild).
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.alter_column(
            "original_file_id", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "preprocessing_config_id", existing_type=sa.Integer(), nullable=True
        )

    op.create_table(
        "document_source_association",
        sa.Column("derived_document_id", sa.Integer(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["derived_document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("derived_document_id", "source_document_id"),
    )
    op.create_index(
        "ix_document_source_association_source",
        "document_source_association",
        ["source_document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_source_association_source",
        table_name="document_source_association",
    )
    op.drop_table("document_source_association")

    # Combined documents (NULL original_file_id) cannot survive the NOT NULL
    # restore — remove them first, together with their dependent rows.
    conn = op.get_bind()
    doc_ids = [
        row[0]
        for row in conn.execute(
            sa.text("SELECT id FROM documents WHERE original_file_id IS NULL")
        )
    ]
    if doc_ids:
        params = {"ids": tuple(doc_ids)}
        conn.execute(
            sa.text(
                "DELETE FROM evaluation_metrics WHERE document_id IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True)),
            params,
        )
        conn.execute(
            sa.text("DELETE FROM trial_results WHERE document_id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            params,
        )
        conn.execute(
            sa.text("DELETE FROM documents WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            params,
        )

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.alter_column(
            "original_file_id", existing_type=sa.Integer(), nullable=False
        )
        batch_op.alter_column(
            "preprocessing_config_id", existing_type=sa.Integer(), nullable=False
        )
