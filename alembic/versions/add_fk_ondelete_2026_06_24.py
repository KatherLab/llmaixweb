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

Constraint names are NOT assumed: different FKs were created at different
times (the initial migration created some unnamed → PostgreSQL auto-named them
``{table}_{column}_fkey``; ``documents.version_of`` was added later with the
explicit name ``fk_documents_version_of``). We reflect each table's actual FK
constraint names via the Alembic inspector and match by referenced
table+columns, so this works regardless of how each constraint was originally
named.

Revision ID: add_fk_ondelete_2026_06_24
Revises: ptask_api_key_enc
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_fk_ondelete_2026_06_24"
down_revision: Union[str, None] = "ptask_api_key_enc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, referenced_table, referenced_column, new_constraint_name,
#  ondelete). ``new_constraint_name`` is what we (re)create the constraint as,
#  so downstream is deterministic regardless of the original name.
_FKS = [
    ("projects", "owner_id", "users", "id", "projects_owner_id_fkey", "CASCADE"),
    (
        "documents",
        "version_of",
        "documents",
        "id",
        "documents_version_of_fkey",
        "SET NULL",
    ),
    (
        "trial_results",
        "document_id",
        "documents",
        "id",
        "trial_results_document_id_fkey",
        "RESTRICT",
    ),
    (
        "evaluation_metrics",
        "document_id",
        "documents",
        "id",
        "evaluation_metrics_document_id_fkey",
        "RESTRICT",
    ),
]


def _find_fk(inspector, table: str, column: str, ref_table: str) -> dict | None:
    """Return the FK dict on ``table(column)`` → ``ref_table``.

    Matches by the constrained column + referenced table, so the original
    constraint name (which varies — auto-named vs explicit) doesn't matter.
    Returns None if no such FK exists (e.g. already migrated, or the column
    was added without a constraint in some environment).
    """
    for fk in inspector.get_foreign_keys(table):
        if not fk.get("constrained_columns"):
            continue
        if (
            column in fk["constrained_columns"]
            and fk.get("referred_table") == ref_table
        ):
            return fk
    return None


def upgrade() -> None:
    bind = op.get_bind()

    for table, column, ref_table, ref_col, new_name, ondelete in _FKS:
        # Re-inspect per table: a fresh inspector reflects the current DB
        # state (previous loop iterations may have already altered a table;
        # inspectors can cache reflected metadata).
        inspector = sa.inspect(bind)
        fk = _find_fk(inspector, table, column, ref_table)
        if fk is None:
            # No matching FK present (e.g. SQLite dev DB without FK enforcement,
            # or an environment where the constraint was never created). Skip
            # rather than fail — the model still declares ondelete for fresh
            # create_all() databases.
            continue
        # Skip if the constraint already has the desired ondelete (idempotent:
        # recovers from a partial apply where earlier tables were already done).
        if fk.get("ondelete") == ondelete:
            continue

        old_name = fk.get("name")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(old_name, type_="foreignkey")
            batch_op.create_foreign_key(
                new_name,
                ref_table,
                [column],
                [ref_col],
                ondelete=ondelete,
            )


def downgrade() -> None:
    bind = op.get_bind()

    for table, column, ref_table, ref_col, new_name, _ondelete in _FKS:
        inspector = sa.inspect(bind)
        fk = _find_fk(inspector, table, column, ref_table)
        if fk is None:
            continue
        old_name = fk.get("name")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(old_name, type_="foreignkey")
            batch_op.create_foreign_key(
                new_name,
                ref_table,
                [column],
                [ref_col],
            )
