"""SSO group mapping and env-managed providers

Revision ID: sso_group_mapping_2026_11_05
Revises: combined_documents_2026_08_07
Create Date: 2026-11-05 00:00:00.000000

- identity_providers.groups_claim / user_groups / admin_groups: derive access and
  role from the IdP's groups claim. Empty groups keep the previous behavior.
- identity_providers.managed_by_env: provider declared through SSO_OIDC_* and
  read-only in the admin API.

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "sso_group_mapping_2026_11_05"
down_revision: Union[str, None] = "combined_documents_2026_08_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("identity_providers", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "groups_claim",
                sa.String(length=100),
                nullable=False,
                server_default="groups",
            )
        )
        batch_op.add_column(
            sa.Column(
                "user_groups", sa.String(length=1024), nullable=False, server_default=""
            )
        )
        batch_op.add_column(
            sa.Column(
                "admin_groups",
                sa.String(length=1024),
                nullable=False,
                server_default="",
            )
        )
        batch_op.add_column(
            sa.Column(
                "managed_by_env",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("identity_providers", schema=None) as batch_op:
        batch_op.drop_column("managed_by_env")
        batch_op.drop_column("admin_groups")
        batch_op.drop_column("user_groups")
        batch_op.drop_column("groups_claim")
