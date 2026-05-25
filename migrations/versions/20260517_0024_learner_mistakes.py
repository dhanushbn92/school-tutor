"""Add learner_mistakes table

Revision ID: 20260517_0024
Revises: 20260517_0023
Create Date: 2026-05-17

Stage 2 of the child-centric roadmap. One row per (user, question)
where the user has at some point answered the question incorrectly.
`consecutive_corrects` tracks subsequent attempts; rows with
`consecutive_corrects >= 2` are considered resolved and filtered out
of the active "things I got wrong" list.

The UNIQUE(user_id, question_id) constraint lets the upsert path
write idempotently — same question wrong twice doesn't insert two
rows. Adding ON CONFLICT DO UPDATE at the service layer keeps the
write path single-statement.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260517_0024"
down_revision: Union[str, None] = "20260517_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learner_mistakes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "first_wrong_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "consecutive_corrects",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint(
            "user_id", "question_id", name="uq_learner_mistake_user_question"
        ),
    )
    op.create_index(
        "ix_learner_mistakes_user_id", "learner_mistakes", ["user_id"]
    )
    op.create_index(
        "ix_learner_mistakes_question_id",
        "learner_mistakes",
        ["question_id"],
    )
    op.create_index(
        "ix_learner_mistakes_last_attempted_at",
        "learner_mistakes",
        ["last_attempted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learner_mistakes_last_attempted_at", table_name="learner_mistakes"
    )
    op.drop_index(
        "ix_learner_mistakes_question_id", table_name="learner_mistakes"
    )
    op.drop_index(
        "ix_learner_mistakes_user_id", table_name="learner_mistakes"
    )
    op.drop_table("learner_mistakes")
