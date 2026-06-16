"""add_document_versioning

Revision ID: add_document_versioning
Revises: bfa301b18a99
Create Date: 2025-06-12

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_document_versioning"
down_revision = "bfa301b18a99"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_latest column (default True for existing rows)
    op.add_column(
        "documents",
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Add version_of column (nullable, links to parent document in version chain)
    op.add_column("documents", sa.Column("version_of", sa.Integer(), nullable=True))

    # Create foreign key constraint for version_of
    op.create_foreign_key(
        "fk_documents_version_of", "documents", "documents", ["version_of"], ["id"]
    )

    # Create indexes for performance
    op.create_index("ix_documents_latest", "documents", ["is_latest"])
    op.create_index("ix_documents_version_of", "documents", ["version_of"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_documents_version_of", table_name="documents")
    op.drop_index("ix_documents_latest", table_name="documents")

    # Drop foreign key constraint
    op.drop_constraint("fk_documents_version_of", "documents", type_="foreignkey")

    # Drop columns
    op.drop_column("documents", "version_of")
    op.drop_column("documents", "is_latest")
