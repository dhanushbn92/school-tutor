"""intervention_notes

Revision ID: 20260424_0008
Revises: 20260424_0007
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_0008"
down_revision: Union[str, None] = "20260424_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intervention_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_intervention_notes_student_id"), "intervention_notes", ["student_id"], unique=False)
    op.create_index(op.f("ix_intervention_notes_teacher_id"), "intervention_notes", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_intervention_notes_chapter_id"), "intervention_notes", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_intervention_notes_topic_id"), "intervention_notes", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_table("intervention_notes")
