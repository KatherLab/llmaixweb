"""CASCADE junction-table FKs + password_reset_tokens index/server_default

Two LOW findings from the backend review:

1. Junction-table foreign keys lacked ``ON DELETE CASCADE``, inconsistent with
   the prior ``add_fk_ondelete_2026_06_24`` hardening. The ORM cleans up
   association rows via cascade, but a direct DB-level delete of a parent
   (file / document / preprocessing_task / preprocessing_configuration /
   document_set) was blocked by the backend default (NO ACTION on PostgreSQL).
   This adds ``ON DELETE CASCADE`` to every junction-table FK so the DB matches
   the ORM's intent. Junction tables:

   - ``preprocessing_task_file_association`` (preprocessing_task_id, file_id)
   - ``preprocessing_task_document_association`` (preprocessing_task_id, document_id)
   - ``preprocessing_configuration_file_association`` (configuration_id, file_id)
   - ``document_set_association`` (document_id, document_set_id)

2. ``password_reset_tokens.user_id`` had no index (scanned per user on
   cleanup/invalidation lookups) and ``created_at`` used a Python default
   instead of ``server_default`` (raw inserts / fresh DBs left it NULL until the
   ORM set it). This adds the index and a ``server_default = now()``.

Note: the SQLite dev/test DB is bootstrapped via ``Base.metadata.create_all()``
(not Alembic), so the model changes already produce the correct schema there.
This migration only affects PostgreSQL prod stacks, where constraint names are
reflected at runtime (not assumed) — see ``_find_fk``.

Revision ID: junction_fk_ondelete_2026_06_29
Revises: trial_result_status
Create Date: 2026-06-29

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "junction_fk_ondelete_2026_06_29"
down_revision: Union[str, None] = "trial_result_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, referenced_table, referenced_column, new_constraint_name).
# All become ON DELETE CASCADE. ``new_constraint_name`` makes the recreated
# constraint deterministic regardless of its original (auto-named) name.
_FKS = [
    (
        "preprocessing_task_file_association",
        "preprocessing_task_id",
        "preprocessing_tasks",
        "id",
        "ptf_assoc_preprocessing_task_id_fkey",
    ),
    (
        "preprocessing_task_file_association",
        "file_id",
        "files",
        "id",
        "ptf_assoc_file_id_fkey",
    ),
    (
        "preprocessing_task_document_association",
        "preprocessing_task_id",
        "preprocessing_tasks",
        "id",
        "ptd_assoc_preprocessing_task_id_fkey",
    ),
    (
        "preprocessing_task_document_association",
        "document_id",
        "documents",
        "id",
        "ptd_assoc_document_id_fkey",
    ),
    (
        "preprocessing_configuration_file_association",
        "configuration_id",
        "preprocessing_configurations",
        "id",
        "pcf_assoc_configuration_id_fkey",
    ),
    (
        "preprocessing_configuration_file_association",
        "file_id",
        "files",
        "id",
        "pcf_assoc_file_id_fkey",
    ),
    (
        "document_set_association",
        "document_id",
        "documents",
        "id",
        "dsa_document_id_fkey",
    ),
    (
        "document_set_association",
        "document_set_id",
        "document_sets",
        "id",
        "dsa_document_set_id_fkey",
    ),
]


def _find_fk(inspector, table: str, column: str, ref_table: str) -> dict | None:
    """Return the FK dict on ``table(column)`` → ``ref_table``.

    Matches by the constrained column + referenced table, so the original
    constraint name (auto-named vs explicit) doesn't matter. Returns None if no
    such FK exists (e.g. SQLite dev DB without FK enforcement, or an
    environment where the constraint was never created).
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

    # --- Junction-table FKs → ON DELETE CASCADE ---
    for table, column, ref_table, ref_col, new_name in _FKS:
        # Re-inspect per table: a fresh inspector reflects the current DB state
        # (previous loop iterations may have already altered a table; inspectors
        # can cache reflected metadata).
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
        if fk.get("ondelete") == "CASCADE":
            continue

        old_name = fk.get("name")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(old_name, type_="foreignkey")
            batch_op.create_foreign_key(
                new_name,
                ref_table,
                [column],
                [ref_col],
                ondelete="CASCADE",
            )

    # --- password_reset_tokens.user_id index ---
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        if_not_exists=True,
    )

    # --- password_reset_tokens.created_at server_default ---
    # Backfill any NULLs first, then set the server default so raw inserts
    # populate the column without the ORM. Existing rows keep their timestamps.
    op.execute(
        "UPDATE password_reset_tokens SET created_at = NOW() WHERE created_at IS NULL"
    )
    op.alter_column(
        "password_reset_tokens",
        "created_at",
        server_default=sa.func.now(),
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Revert created_at server_default (drop the default).
    op.alter_column(
        "password_reset_tokens",
        "created_at",
        server_default=None,
    )

    op.drop_index("ix_password_reset_tokens_user_id", "password_reset_tokens")

    # Revert junction-table FKs to NO ACTION (the previous behavior).
    for table, column, ref_table, ref_col, new_name in _FKS:
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
