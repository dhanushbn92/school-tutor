"""assessments, assessment_questions, submissions, submission_answers

Revision ID: 20260424_0006
Revises: 20260424_0005
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_0006"
down_revision: Union[str, None] = "20260424_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


assessment_type_enum = sa.Enum(
    "WORKSHEET", "QUIZ", "UNIT_TEST", "EXAM", name="assessmenttype"
)
assessment_status_enum = sa.Enum("DRAFT", "PUBLISHED", "CLOSED", name="assessmentstatus")
submission_status_enum = sa.Enum(
    "DRAFT", "SUBMITTED", "EVALUATED", "LATE", name="submissionstatus"
)


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("type", assessment_type_enum, nullable=False),
        sa.Column("status", assessment_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("total_marks", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessments_section_id"), "assessments", ["section_id"], unique=False)
    op.create_index(op.f("ix_assessments_subject_id"), "assessments", ["subject_id"], unique=False)
    op.create_index(op.f("ix_assessments_chapter_id"), "assessments", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_assessments_type"), "assessments", ["type"], unique=False)
    op.create_index(op.f("ix_assessments_status"), "assessments", ["status"], unique=False)

    op.create_table(
        "assessment_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("marks_override", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "question_id", name="uq_assessment_questions_aq"),
        sa.UniqueConstraint("assessment_id", "order", name="uq_assessment_questions_order"),
    )
    op.create_index(op.f("ix_assessment_questions_assessment_id"), "assessment_questions", ["assessment_id"], unique=False)
    op.create_index(op.f("ix_assessment_questions_question_id"), "assessment_questions", ["question_id"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("status", submission_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_awarded", sa.Integer(), nullable=True),
        sa.Column("max_marks", sa.Integer(), nullable=False),
        sa.Column("uploaded_file_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "student_id", name="uq_submissions_assessment_student"),
    )
    op.create_index(op.f("ix_submissions_assessment_id"), "submissions", ["assessment_id"], unique=False)
    op.create_index(op.f("ix_submissions_student_id"), "submissions", ["student_id"], unique=False)
    op.create_index(op.f("ix_submissions_status"), "submissions", ["status"], unique=False)

    op.create_table(
        "submission_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("marks_awarded", sa.Integer(), nullable=True),
        sa.Column("max_marks", sa.Integer(), nullable=False),
        sa.Column("auto_graded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("teacher_remark", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "question_id", name="uq_submission_answers_sq"),
    )
    op.create_index(op.f("ix_submission_answers_submission_id"), "submission_answers", ["submission_id"], unique=False)
    op.create_index(op.f("ix_submission_answers_question_id"), "submission_answers", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_table("submission_answers")
    op.drop_table("submissions")
    op.drop_table("assessment_questions")
    op.drop_table("assessments")
    submission_status_enum.drop(op.get_bind(), checkfirst=True)
    assessment_status_enum.drop(op.get_bind(), checkfirst=True)
    assessment_type_enum.drop(op.get_bind(), checkfirst=True)
