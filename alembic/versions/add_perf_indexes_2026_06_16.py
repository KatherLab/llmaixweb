"""Add performance indexes for documents and files tables

Revision ID: add_perf_indexes_2026_06_16
Revises: f9a8b2c3d4e6, fix_doc_version_index
Create Date: 2026-06-16

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_perf_indexes_2026_06_16"
down_revision = ("f9a8b2c3d4e6", "fix_doc_version_index")
branch_labels = None
depends_on = None


def upgrade():
    # Document indexes for common query patterns (optimized for 50k+ documents)
    # Note: Some indexes may already exist from model changes - use IF NOT EXISTS
    op.create_index(
        "ix_documents_project_created",
        "documents",
        ["project_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_documents_project_latest",
        "documents",
        ["project_id", "is_latest"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_documents_project_file",
        "documents",
        ["project_id", "original_file_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_documents_project_config",
        "documents",
        ["project_id", "preprocessing_config_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_documents_project_task",
        "documents",
        ["project_id", "file_preprocessing_task_id"],
        if_not_exists=True,
    )

    # File indexes for common query patterns (optimized for 50k+ files)
    op.create_index(
        "ix_files_project_created",
        "files",
        ["project_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_files_project_type",
        "files",
        ["project_id", "file_type"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_files_project_creator",
        "files",
        ["project_id", "file_creator"],
        if_not_exists=True,
    )

    # Trigram indexes for fast ILIKE pattern matching (optimized for document search)
    # Requires pg_trgm extension - enables GIN/GiST indexes for text similarity searches
    # Performance: Reduces ILIKE '%...%' queries from minutes to milliseconds on 100k+ rows
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_documents_text_trgm",
        "documents",
        ["text"],
        if_not_exists=True,
        postgresql_using="gin",
        postgresql_ops={"text": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_files_file_name_trgm",
        "files",
        ["file_name"],
        if_not_exists=True,
        postgresql_using="gin",
        postgresql_ops={"file_name": "gin_trgm_ops"},
    )


def downgrade():
    # Drop trigram indexes first
    op.drop_index("ix_files_file_name_trgm", "files")
    op.drop_index("ix_documents_text_trgm", "documents")

    # Drop regular indexes in reverse order
    op.drop_index("ix_files_project_creator", "files")
    op.drop_index("ix_files_project_type", "files")
    op.drop_index("ix_files_project_created", "files")

    op.drop_index("ix_documents_project_task", "documents")
    op.drop_index("ix_documents_project_config", "documents")
    op.drop_index("ix_documents_project_file", "documents")
    op.drop_index("ix_documents_project_latest", "documents")
    op.drop_index("ix_documents_project_created", "documents")

    # Note: pg_trgm extension is not dropped as it may be used by other tables
