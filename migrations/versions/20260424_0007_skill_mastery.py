"""skill_mastery

Revision ID: 20260424_0007
Revises: 20260424_0006
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_0007"
down_revision: Union[str, None] = "20260424_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skill_mastery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("outcome_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outcome_id"], ["learning_outcomes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "outcome_id", name="uq_skill_mastery_student_outcome"),
    )
    op.create_index(op.f("ix_skill_mastery_student_id"), "skill_mastery", ["student_id"], unique=False)
    op.create_index(op.f("ix_skill_mastery_outcome_id"), "skill_mastery", ["outcome_id"], unique=False)
    op.create_index(op.f("ix_skill_mastery_chapter_id"), "skill_mastery", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_skill_mastery_topic_id"), "skill_mastery", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_table("skill_mastery")
