"""Remove legacy preprocessing config fields (now in additional_settings)

Revision ID: f9a8b2c3d4e6
Revises: f9a8b2c3d4e5
Create Date: 2026-05-20 10:02:29.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a8b2c3d4e6"
down_revision: Union[str, None] = "f9a8b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("preprocessing_configurations", "pdf_backend")
    op.drop_column("preprocessing_configurations", "ocr_backend")
    op.drop_column("preprocessing_configurations", "use_ocr")
    op.drop_column("preprocessing_configurations", "force_ocr")
    op.drop_column("preprocessing_configurations", "ocr_languages")
    op.drop_column("preprocessing_configurations", "ocr_model")
    op.drop_column("preprocessing_configurations", "llm_model")


def downgrade() -> None:
    op.add_column(
        "preprocessing_configurations",
        sa.Column("pdf_backend", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("ocr_backend", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("use_ocr", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("force_ocr", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("ocr_languages", sa.JSON(), nullable=True),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("ocr_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "preprocessing_configurations",
        sa.Column("llm_model", sa.String(length=100), nullable=True),
    )
