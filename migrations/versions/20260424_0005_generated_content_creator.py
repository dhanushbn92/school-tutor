"""track creator on generated_contents

Revision ID: 20260424_0005
Revises: 20260424_0004
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_0005"
down_revision: Union[str, None] = "20260424_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_contents",
        sa.Column("created_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_generated_contents_created_by_id_users",
        "generated_contents",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_generated_contents_created_by_id"),
        "generated_contents",
        ["created_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_contents_created_by_id"), table_name="generated_contents")
    op.drop_constraint(
        "fk_generated_contents_created_by_id_users",
        "generated_contents",
        type_="foreignkey",
    )
    op.drop_column("generated_contents", "created_by_id")
