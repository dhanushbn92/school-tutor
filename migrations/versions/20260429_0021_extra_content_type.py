"""Add EXTRA_CONTENT to generatedcontenttype enum

Revision ID: 20260429_0021
Revises: 20260428_0020
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260429_0021"
down_revision: Union[str, None] = "20260428_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres enums don't support `ADD VALUE` inside a transaction by
    # default, so we run the change with an autocommit block.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'extra_content'"
        )


def downgrade() -> None:
    # Postgres can't drop enum values without recreating the type. Since
    # downgrade for an additive enum value is rarely needed and risky, we
    # leave the value in place. Code that no longer references it will
    # simply ignore it.
    pass
