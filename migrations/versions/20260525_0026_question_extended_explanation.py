"""Add question_extended_explanation table

Revision ID: 20260525_0026
Revises: 20260525_0025
Create Date: 2026-05-25

Stage 3 of the child-centric roadmap — the "Why?" / "Tell me more"
chain on every revealed explanation. One row per (question_id, tier).

The three tiers map to the three escalating clicks in the UI:
  - DEEPER   — a fuller paragraph explanation of the same answer
  - ANALOGY  — a relatable real-world parallel
  - EXAMPLE  — a worked example at the same concept

Generation is on-demand via LLM and cached forever per question.
Cache invalidation is intentionally absent: the source question is
immutable once APPROVED, so the explanation should be stable too.
If we ever need to refresh, a manual DELETE is enough.

`generated_by_id` is a FK into users so we can credit the user whose
click first triggered generation (debugging + auditing tool — never
shown in the UI).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260525_0026"
down_revision: Union[str, None] = "20260525_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_extended_explanation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "generated_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # One row per (question, tier). Idempotent generation: a
        # concurrent click during a slow LLM call will lose the
        # race on UNIQUE and fall back to the cached read.
        sa.UniqueConstraint(
            "question_id", "tier", name="uq_question_extended_explanation"
        ),
    )
    op.create_index(
        "ix_question_extended_explanation_question_id",
        "question_extended_explanation",
        ["question_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_question_extended_explanation_question_id",
        table_name="question_extended_explanation",
    )
    op.drop_table("question_extended_explanation")
