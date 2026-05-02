"""question bank

Revision ID: 20260424_0004
Revises: 20260424_0003
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_0004"
down_revision: Union[str, None] = "20260424_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


question_type_enum = sa.Enum(
    "MCQ",
    "SHORT_ANSWER",
    "LONG_ANSWER",
    "FILL_BLANK",
    "TRUE_FALSE",
    "CASE_BASED",
    name="questiontype",
)
question_difficulty_enum = sa.Enum("EASY", "MEDIUM", "HARD", name="questiondifficulty")
question_status_enum = sa.Enum(
    "DRAFT", "APPROVED", "REJECTED", "RETIRED", name="questionstatus"
)


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("outcome_id", sa.Integer(), nullable=True),
        sa.Column("outcome_code", sa.String(length=40), nullable=True),
        sa.Column("type", question_type_enum, nullable=False),
        sa.Column("difficulty", question_difficulty_enum, nullable=False),
        sa.Column("status", question_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("marks", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_generated_content_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outcome_id"], ["learning_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_generated_content_id"], ["generated_contents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_chapter_id"), "questions", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_questions_topic_id"), "questions", ["topic_id"], unique=False)
    op.create_index(op.f("ix_questions_outcome_id"), "questions", ["outcome_id"], unique=False)
    op.create_index(op.f("ix_questions_outcome_code"), "questions", ["outcome_code"], unique=False)
    op.create_index(op.f("ix_questions_type"), "questions", ["type"], unique=False)
    op.create_index(op.f("ix_questions_difficulty"), "questions", ["difficulty"], unique=False)
    op.create_index(op.f("ix_questions_status"), "questions", ["status"], unique=False)
    op.create_index(
        op.f("ix_questions_source_generated_content_id"),
        "questions",
        ["source_generated_content_id"],
        unique=False,
    )
    op.create_index(op.f("ix_questions_created_by_id"), "questions", ["created_by_id"], unique=False)


def downgrade() -> None:
    op.drop_table("questions")
    question_status_enum.drop(op.get_bind(), checkfirst=True)
    question_difficulty_enum.drop(op.get_bind(), checkfirst=True)
    question_type_enum.drop(op.get_bind(), checkfirst=True)
