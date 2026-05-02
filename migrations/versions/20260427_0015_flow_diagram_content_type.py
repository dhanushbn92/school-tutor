"""Add FLOW_DIAGRAM label to generatedcontenttype enum

Revision ID: 20260427_0015
Revises: 20260427_0014
Create Date: 2026-04-27
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260427_0015"
down_revision: Union[str, None] = "20260427_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'FLOW_DIAGRAM'")


def downgrade() -> None:
    pass
