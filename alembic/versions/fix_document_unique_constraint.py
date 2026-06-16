"""fix_document_unique_constraint

Revision ID: fix_document_unique_constraint
Revises: add_document_versioning
Create Date: 2026-06-16

This migration fixes the unique constraint on documents to properly support
document versioning. The old constraint prevented multiple versions of the
same document from existing, even with is_latest=False.

The new constraint includes is_latest, allowing:
- Only ONE document with is_latest=True per (file, config, name)
- MULTIPLE documents with is_latest=False per (file, config, name) for history

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_document_unique_constraint"
down_revision = "add_document_versioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old unique constraint that doesn't account for versioning
    op.drop_constraint("_document_uniqueness", "documents", type_="unique")

    # Create new unique constraint that includes is_latest
    # This allows multiple versions (is_latest=False) while ensuring
    # only one "latest" version exists per file/config/name combination
    op.create_unique_constraint(
        "_document_uniqueness",
        "documents",
        ["original_file_id", "preprocessing_config_id", "document_name", "is_latest"],
    )


def downgrade() -> None:
    # Revert to the old constraint
    op.drop_constraint("_document_uniqueness", "documents", type_="unique")
    op.create_unique_constraint(
        "_document_uniqueness",
        "documents",
        ["original_file_id", "preprocessing_config_id", "document_name"],
    )
