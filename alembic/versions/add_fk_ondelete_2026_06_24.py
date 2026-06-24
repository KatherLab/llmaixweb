"""Add ON DELETE behavior to foreign keys

Several foreign keys had no explicit ON DELETE action, so their behavior
depended on the backend default (NO ACTION on PostgreSQL, unenforced on the
SQLite dev DB). This migration makes the intent explicit and consistent with
how the application already manages these references:

- ``projects.owner_id`` → CASCADE. Matches the existing ORM cascade
  (``User.projects`` has ``cascade="all, delete-orphan"``): deleting a user
  removes their projects. Defense-in-depth for direct DB-level user deletion.
- ``documents.version_of`` → SET NULL. Deleting a root document orphans its
  archived versions rather than cascade-deleting version history (or blocking).
- ``trial_results.document_id`` → RESTRICT. Matches the ``delete_document``
  endpoint, which rejects deletion of a document referenced by a trial result.
- ``evaluation_metrics.document_id`` → RESTRICT. Same rationale: the endpoint
  rejects deleting a document referenced by evaluation metrics.

Trial.schema_id / Trial.prompt_id are intentionally left at the backend
default (effectively RESTRICT): the delete_schema / delete_prompt endpoints
already reject deletion when a trial references them, and trials carry frozen
schema/prompt snapshots. The DB-level RESTRICT provides matching
defense-in-depth without changing the columns' NOT NULL constraint.

Revision ID: add_fk_ondelete_2026_06_24
Revises: ptask_api_key_enc
Create Date: 2026-06-24

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_fk_ondelete_2026_06_24"
down_revision: Union[str, None] = "ptask_api_key_enc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table keeps this portable to the SQLite dev backend (which
    # can't ALTER a constraint in-place and needs a table rebuild). Constraint
    # names follow PostgreSQL's default "{table}_{column}_fkey" convention.

    # projects.owner_id → CASCADE
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_constraint("projects_owner_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "projects_owner_id_fkey",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # documents.version_of → SET NULL
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("documents_version_of_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "documents_version_of_fkey",
            "documents",
            ["version_of"],
            ["id"],
            ondelete="SET NULL",
        )

    # trial_results.document_id → RESTRICT
    with op.batch_alter_table("trial_results", schema=None) as batch_op:
        batch_op.drop_constraint("trial_results_document_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "trial_results_document_id_fkey",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # evaluation_metrics.document_id → RESTRICT
    with op.batch_alter_table("evaluation_metrics", schema=None) as batch_op:
        batch_op.drop_constraint(
            "evaluation_metrics_document_id_fkey", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "evaluation_metrics_document_id_fkey",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Restore the original (no explicit ondelete) constraints.
    with op.batch_alter_table("evaluation_metrics", schema=None) as batch_op:
        batch_op.drop_constraint(
            "evaluation_metrics_document_id_fkey", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "evaluation_metrics_document_id_fkey",
            "documents",
            ["document_id"],
            ["id"],
        )

    with op.batch_alter_table("trial_results", schema=None) as batch_op:
        batch_op.drop_constraint("trial_results_document_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "trial_results_document_id_fkey",
            "documents",
            ["document_id"],
            ["id"],
        )

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("documents_version_of_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "documents_version_of_fkey",
            "documents",
            ["version_of"],
            ["id"],
        )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_constraint("projects_owner_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "projects_owner_id_fkey",
            "users",
            ["owner_id"],
            ["id"],
        )
