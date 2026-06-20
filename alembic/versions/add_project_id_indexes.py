"""Add project_id (and Trial status) indexes for list endpoints

Several project-scoped models had no index on ``project_id`` despite every
list endpoint filtering ``WHERE project_id = :project_id`` (often with
``ORDER BY created_at``). This seq-scans at scale. The sibling models
(File, Document, GroundTruth, Evaluation) were already indexed; this adds
the missing indexes for DocumentSet, PreprocessingConfiguration,
PreprocessingTask, Prompt, Schema and Trial, plus a (project_id, status)
index for Trial to support the "recent trials" activity query.

Revision ID: add_project_id_indexes
Revises: rename_trial_apikey
Create Date: 2026-06-20

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_project_id_indexes"
down_revision = "rename_trial_apikey"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_document_sets_project_created",
        "document_sets",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_preprocessing_configurations_project_created",
        "preprocessing_configurations",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_preprocessing_tasks_project_created",
        "preprocessing_tasks",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_preprocessing_tasks_configuration_id",
        "preprocessing_tasks",
        ["configuration_id"],
        unique=False,
    )
    op.create_index(
        "ix_prompts_project_created",
        "prompts",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_schemas_project_created",
        "schemas",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trials_project_created",
        "trials",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trials_project_status",
        "trials",
        ["project_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trials_project_status", table_name="trials")
    op.drop_index("ix_trials_project_created", table_name="trials")
    op.drop_index("ix_schemas_project_created", table_name="schemas")
    op.drop_index("ix_prompts_project_created", table_name="prompts")
    op.drop_index(
        "ix_preprocessing_tasks_configuration_id", table_name="preprocessing_tasks"
    )
    op.drop_index(
        "ix_preprocessing_tasks_project_created", table_name="preprocessing_tasks"
    )
    op.drop_index(
        "ix_preprocessing_configurations_project_created",
        table_name="preprocessing_configurations",
    )
    op.drop_index("ix_document_sets_project_created", table_name="document_sets")
