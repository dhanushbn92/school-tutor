"""add cognitive_level to questions (6-level Bloom) + backfill from outcome

Revision ID: 20260426_0011
Revises: 20260425_0010
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260426_0011"
down_revision: Union[str, None] = "20260425_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Reuse the existing `bloomlevel` Postgres enum (created when LearningOutcome shipped).
bloom_enum = sa.Enum(
    "REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE",
    name="bloomlevel",
    create_type=False,
)


def upgrade() -> None:
    # 1) Add the column nullable so we can backfill cleanly.
    op.add_column("questions", sa.Column("cognitive_level", bloom_enum, nullable=True))
    op.create_index(
        op.f("ix_questions_cognitive_level"), "questions", ["cognitive_level"], unique=False
    )

    # 2) Backfill: every Question with a linked outcome inherits its bloom_level.
    #    Questions with no outcome (rare) default to UNDERSTAND — a reasonable middle.
    op.execute(
        """
        UPDATE questions q
        SET cognitive_level = lo.bloom_level
        FROM learning_outcomes lo
        WHERE q.outcome_id = lo.id AND q.cognitive_level IS NULL
        """
    )
    op.execute(
        "UPDATE questions SET cognitive_level = 'UNDERSTAND' WHERE cognitive_level IS NULL"
    )

    # 3) Now lock the column NOT NULL.
    op.alter_column("questions", "cognitive_level", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_questions_cognitive_level"), table_name="questions")
    op.drop_column("questions", "cognitive_level")
