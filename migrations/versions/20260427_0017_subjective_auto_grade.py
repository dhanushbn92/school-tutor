"""Add Question.auto_grade rubric + SubmissionAnswer.grading_details

Revision ID: 20260427_0017
Revises: 20260427_0016
Create Date: 2026-04-27

The rubric on Question lets authors define keyword groups that the submission
grader uses to award partial marks for subjective answers. The breakdown is
cached on SubmissionAnswer so the student's results page can show what the
grader matched and missed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260427_0017"
down_revision: Union[str, None] = "20260427_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("auto_grade", sa.JSON(), nullable=True))
    op.add_column(
        "submission_answers", sa.Column("grading_details", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("submission_answers", "grading_details")
    op.drop_column("questions", "auto_grade")
