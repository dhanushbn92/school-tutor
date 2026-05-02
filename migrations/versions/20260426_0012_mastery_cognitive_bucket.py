"""add cognitive_bucket to skill_mastery (3-bucket grouping for student-facing splits)

Revision ID: 20260426_0012
Revises: 20260426_0011
Create Date: 2026-04-26

Mastery moves from one row per (student, outcome) to one row per
(student, outcome, cognitive_bucket). The bucket is FACTUAL / UNDERSTANDING /
APPLICATION, derived from the question's 6-level Bloom (REMEMBER → FACTUAL,
UNDERSTAND → UNDERSTANDING, APPLY/ANALYZE/EVALUATE/CREATE → APPLICATION).

Existing rows can't be split mid-flight (we don't know which bucket the prior
EWMA observation belonged to), so we DROP existing rows and provide
`scripts/recompute_mastery.py` to re-derive from EVALUATED submissions.
Demo data is small; the script runs in seconds.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260426_0012"
down_revision: Union[str, None] = "20260426_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


bucket_enum = sa.Enum(
    "FACTUAL", "UNDERSTANDING", "APPLICATION", name="cognitivebucket"
)


def upgrade() -> None:
    bucket_enum.create(op.get_bind(), checkfirst=True)

    # Existing rows have no bucket information — flush them. Operator runs
    # `scripts.recompute_mastery` afterwards to repopulate from submissions.
    op.execute("TRUNCATE TABLE skill_mastery")

    op.add_column(
        "skill_mastery",
        sa.Column("cognitive_bucket", bucket_enum, nullable=False),
    )
    op.create_index(
        op.f("ix_skill_mastery_cognitive_bucket"),
        "skill_mastery",
        ["cognitive_bucket"],
        unique=False,
    )

    # Replace the old (student_id, outcome_id) unique with the new triple.
    op.drop_constraint(
        "uq_skill_mastery_student_outcome", "skill_mastery", type_="unique"
    )
    op.create_unique_constraint(
        "uq_skill_mastery_student_outcome_bucket",
        "skill_mastery",
        ["student_id", "outcome_id", "cognitive_bucket"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_skill_mastery_student_outcome_bucket", "skill_mastery", type_="unique"
    )
    op.create_unique_constraint(
        "uq_skill_mastery_student_outcome", "skill_mastery", ["student_id", "outcome_id"]
    )
    op.drop_index(op.f("ix_skill_mastery_cognitive_bucket"), table_name="skill_mastery")
    op.drop_column("skill_mastery", "cognitive_bucket")
    bucket_enum.drop(op.get_bind(), checkfirst=True)
