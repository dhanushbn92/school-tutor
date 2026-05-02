"""Add CHAPTER_SUMMARY label to generatedcontenttype enum

Revision ID: 20260427_0013
Revises: 20260426_0012
Create Date: 2026-04-27

SQLAlchemy maps Python `StrEnum` columns to Postgres enum labels using the
attribute NAME (uppercase), so we add 'CHAPTER_SUMMARY' even though the
Python value is "chapter_summary".
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260427_0013"
down_revision: Union[str, None] = "20260426_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'CHAPTER_SUMMARY'"
        )


def downgrade() -> None:
    # PostgreSQL has no DROP VALUE on enums; the label stays.
    pass
