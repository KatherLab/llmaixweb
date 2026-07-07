"""set server_default=now() on timestamp columns missing it

Several tables were created with `created_at` / `updated_at` declared
NOT NULL but without a database-level default. Their ORM models declare only
`server_default=func.now()` (no Python `default=`), so SQLAlchemy omits the
column from INSERT and relies on the DB to populate it — which it couldn't,
because the column had no default. The result was a NotNullViolation on the
first insert, e.g. a 500 when saving a new SSO identity provider.

    sqlalchemy.exc.IntegrityError: (psycopg.errors.NotNullViolation)
      null value in column "created_at" of relation "identity_providers"
      violates not-null constraint

This adds the missing `DEFAULT now()` at the DB level for the affected
columns so the schema matches what the models already declare:

  - identity_providers.created_at / updated_at
  - user_identities.created_at
  - refresh_tokens.created_at
  - password_reset_tokens.created_at  (latent: model also has a Python
    default, so ORM inserts worked, but raw inserts and the schema were wrong)

The corresponding `create_table` migrations have also been corrected, so fresh
deployments get the right schema from the start; this migration brings
existing deployments back in line.

Revision ID: fix_ts_defaults_2026_07_07
Revises: sso_auth_hardening_2026_06_30
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fix_ts_defaults_2026_07_07"
down_revision: Union[str, None] = "sso_auth_hardening_2026_06_30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # identity_providers
    op.alter_column(
        "identity_providers",
        "created_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "identity_providers",
        "updated_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    # user_identities
    op.alter_column(
        "user_identities",
        "created_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    # refresh_tokens
    op.alter_column(
        "refresh_tokens",
        "created_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    # password_reset_tokens (latent defect; fix the schema to match the model)
    op.alter_column(
        "password_reset_tokens",
        "created_at",
        server_default=sa.func.now(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "password_reset_tokens",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "refresh_tokens",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "user_identities",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "identity_providers",
        "updated_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "identity_providers",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
