"""schools.is_personal/brand_name/logo_url; generated_contents.published_at/published_by_id

Revision ID: 20260425_0010
Revises: 20260425_0009
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260425_0010"
down_revision: Union[str, None] = "20260425_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schools",
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("schools", sa.Column("brand_name", sa.String(length=200), nullable=True))
    op.add_column("schools", sa.Column("logo_url", sa.Text(), nullable=True))
    op.create_index(op.f("ix_schools_is_personal"), "schools", ["is_personal"], unique=False)

    op.add_column(
        "generated_contents",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "generated_contents",
        sa.Column("published_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_generated_contents_published_by_id_users",
        "generated_contents",
        "users",
        ["published_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_generated_contents_published_at"),
        "generated_contents",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_contents_published_by_id"),
        "generated_contents",
        ["published_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_contents_published_by_id"), table_name="generated_contents")
    op.drop_index(op.f("ix_generated_contents_published_at"), table_name="generated_contents")
    op.drop_constraint(
        "fk_generated_contents_published_by_id_users", "generated_contents", type_="foreignkey"
    )
    op.drop_column("generated_contents", "published_by_id")
    op.drop_column("generated_contents", "published_at")
    op.drop_index(op.f("ix_schools_is_personal"), table_name="schools")
    op.drop_column("schools", "logo_url")
    op.drop_column("schools", "brand_name")
    op.drop_column("schools", "is_personal")
