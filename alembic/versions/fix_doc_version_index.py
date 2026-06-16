"""fix_doc_version_index

Revision ID: fix_doc_version_index
Revises: fix_document_unique_constraint
Create Date: 2025-06-16

This migration replaces the unique constraint (which includes is_latest)
with a partial unique index. This allows unlimited archived versions
(is_latest=False) while ensuring only ONE latest version (is_latest=True)
per (original_file_id, preprocessing_config_id, document_name).

The previous migration (fix_document_unique_constraint) added is_latest to
the constraint, which still prevented multiple archived versions. This
migration uses a PostgreSQL partial unique index to only enforce uniqueness
when is_latest=True.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_doc_version_index"
down_revision = "fix_document_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint from fix_document_unique_constraint
    # (which includes is_latest and prevents multiple archived versions)
    op.drop_constraint("_document_uniqueness", "documents", type_="unique")

    # Create a partial unique index that only enforces uniqueness when is_latest=True
    # This ensures only ONE latest version per (file, config, name) but allows
    # unlimited archived versions (is_latest=False)
    # Note: We use an index instead of a constraint because PostgreSQL partial
    # uniqueness is only supported via unique indexes, not check constraints.
    op.execute(
        sa.text("""
        CREATE UNIQUE INDEX _document_uniqueness
        ON documents (original_file_id, preprocessing_config_id, document_name)
        WHERE is_latest = true
    """)
    )


def downgrade() -> None:
    # Drop the partial unique index
    op.drop_index("_document_uniqueness", table_name="documents")

    # Restore the constraint from fix_document_unique_constraint
    op.create_unique_constraint(
        "_document_uniqueness",
        "documents",
        ["original_file_id", "preprocessing_config_id", "document_name", "is_latest"],
    )
