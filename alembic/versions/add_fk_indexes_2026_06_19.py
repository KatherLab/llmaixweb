"""Add missing FK indexes on fast-growing tables

PostgreSQL does not auto-index foreign-key columns. Several of the tables that
grow with document count (trial_results, evaluation_metrics,
file_preprocessing_tasks, evaluations, ground_truth, and the
document_set_association link table) had unindexed FK columns, causing
seq-scans on the most common access patterns (per-document lookups,
per-evaluation metric lists, set membership) at 100k+ rows.

Revision ID: add_fk_indexes_2026_06_19
Revises: add_trial_schema_prompt_snapshot
Create Date: 2026-06-19

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_fk_indexes_2026_06_19"
down_revision = "add_trial_schema_prompt_snapshot"
branch_labels = None
depends_on = None


def upgrade():
    # trial_results: (trial_id, document_id) unique constraint covers
    # trial_id-leading lookups, but document_id-only lookups (deletes,
    # downloads, stats) seq-scan without this.
    op.create_index(
        "ix_trial_results_document_id",
        "trial_results",
        ["document_id"],
        if_not_exists=True,
    )

    # evaluation_metrics: hot path for evaluation detail views (by
    # evaluation_id) and per-document checks (by document_id).
    op.create_index(
        "ix_evaluation_metrics_evaluation_id",
        "evaluation_metrics",
        ["evaluation_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_evaluation_metrics_document_id",
        "evaluation_metrics",
        ["document_id"],
        if_not_exists=True,
    )

    # file_preprocessing_tasks: listing subtasks per task / per file.
    op.create_index(
        "ix_file_preprocessing_tasks_preprocessing_task_id",
        "file_preprocessing_tasks",
        ["preprocessing_task_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_file_preprocessing_tasks_file_id",
        "file_preprocessing_tasks",
        ["file_id"],
        if_not_exists=True,
    )

    # evaluations: lookups by trial / by ground truth.
    op.create_index(
        "ix_evaluations_trial_id",
        "evaluations",
        ["trial_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_evaluations_groundtruth_id",
        "evaluations",
        ["groundtruth_id"],
        if_not_exists=True,
    )

    # ground_truth: listing ground-truth files for a project.
    op.create_index(
        "ix_ground_truth_project_id",
        "ground_truth",
        ["project_id"],
        if_not_exists=True,
    )

    # document_set_association: PK leads with document_id, so reverse
    # lookups ("all documents in a set") seq-scan without this.
    op.create_index(
        "ix_document_set_association_document_set_id",
        "document_set_association",
        ["document_set_id"],
        if_not_exists=True,
    )


def downgrade():
    op.drop_index(
        "ix_document_set_association_document_set_id", "document_set_association"
    )
    op.drop_index("ix_ground_truth_project_id", "ground_truth")
    op.drop_index("ix_evaluations_groundtruth_id", "evaluations")
    op.drop_index("ix_evaluations_trial_id", "evaluations")
    op.drop_index("ix_file_preprocessing_tasks_file_id", "file_preprocessing_tasks")
    op.drop_index(
        "ix_file_preprocessing_tasks_preprocessing_task_id", "file_preprocessing_tasks"
    )
    op.drop_index("ix_evaluation_metrics_document_id", "evaluation_metrics")
    op.drop_index("ix_evaluation_metrics_evaluation_id", "evaluation_metrics")
    op.drop_index("ix_trial_results_document_id", "trial_results")
