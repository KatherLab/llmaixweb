"""Add expiry to invitation tokens

Invitation tokens are bearer tokens that grant account registration, yet they
previously had no ``expires_at``: an unused invitation stayed valid forever and
could only be revoked by deleting it. A leaked invitation link therefore
granted registration indefinitely.

This adds ``created_at`` (server-defaulted to now()) and ``expires_at`` to the
``invitations`` table. The invite endpoint sets ``expires_at`` based on
``INVITATION_EXPIRE_HOURS`` (default 7 days); the registration and
validate-invitation endpoints reject tokens past it.

Existing rows are left with ``expires_at = NULL`` (= "no expiry"), so this
migration does not invalidate any pending invitation that an admin has already
sent. Only invitations created after the upgrade are time-bounded; an admin
can revoke a legacy one explicitly via DELETE /users/invitations/{id}.

Revision ID: invitation_expiry
Revises: add_fk_ondelete_2026_06_24
Create Date: 2026-06-29

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "invitation_expiry"
down_revision: Union[str, None] = "add_fk_ondelete_2026_06_24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # created_at: server_default so raw inserts also work. Existing rows get
    # now() via the server default applied during the add.
    op.add_column(
        "invitations",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # expires_at: NULL for legacy rows (treated as "no expiry"); new rows get
    # a value from the invite endpoint.
    op.add_column(
        "invitations",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invitations", "expires_at")
    op.drop_column("invitations", "created_at")
