"""Per-subject teacher assignments — content visibility scope

Revision ID: 20260428_0019
Revises: 20260428_0018
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260428_0019"
down_revision: Union[str, None] = "20260428_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teacher_subject_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "teacher_id",
            sa.Integer(),
            sa.ForeignKey("teachers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("teacher_id", "subject_id", name="uq_teacher_subject"),
    )


def downgrade() -> None:
    op.drop_table("teacher_subject_assignments")
