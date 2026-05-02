"""Add CLASSROOM_ACTIVITY and RESOURCE_LIST labels to generatedcontenttype enum

Revision ID: 20260427_0014
Revises: 20260427_0013
Create Date: 2026-04-27

Two new content types for the student/teacher Learn experience: per-chapter
classroom activities (teacher-facing) and curated additional resources
(admin-approved external links).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260427_0014"
down_revision: Union[str, None] = "20260427_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'CLASSROOM_ACTIVITY'"
        )
        op.execute(
            "ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'RESOURCE_LIST'"
        )


def downgrade() -> None:
    pass
