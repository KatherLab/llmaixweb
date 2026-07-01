"""trials.document_set_id ON DELETE SET NULL

Revision ID: trial_docset_setnull
Revises: add_project_id_indexes
Create Date: 2026-06-20 00:00:00.000000

Drop the "delete-orphan" ORM cascade on DocumentSet.trials and make the
trials.document_set_id foreign key ON DELETE SET NULL at the DB level.

Previously the relationship used cascade="all, delete-orphan", which meant
unlinking a Trial from its DocumentSet (setting document_set = None) silently
deleted the Trial — and with it its TrialResults and Evaluations. Trials are
designed to exist without a set (document_set_id is nullable, and TrialCreate
allows creating trials via document_ids only), so that cascade was a data-loss
hazard. Deleting a DocumentSet now NULLs the referencing trials instead of
destroying them; the delete_document_set endpoint still rejects sets that a
trial currently references.

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "trial_docset_setnull"
down_revision: Union[str, None] = "add_project_id_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate the FK with ondelete="SET NULL". batch_alter_table keeps this
    # portable to the SQLite dev backend (which can't ALTER a constraint
    # in-place and needs the table rebuild).
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.drop_constraint("trials_document_set_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "trials_document_set_id_fkey",
            "document_sets",
            ["document_set_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("trials", schema=None) as batch_op:
        batch_op.drop_constraint("trials_document_set_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "trials_document_set_id_fkey",
            "document_sets",
            ["document_set_id"],
            ["id"],
        )
