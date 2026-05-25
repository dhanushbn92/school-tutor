"""Add learner_login_days and learner_points_ledger tables

Revision ID: 20260525_0025
Revises: 20260517_0024
Create Date: 2026-05-25

Stage 1.5 of the child-centric roadmap — login streak + points + levels.

`learner_login_days` stores one row per (user, day) the learner was
authenticated on. Append-only (composite PK with no other columns)
because the day flag is the entire payload — presence == proof. The
auth dependency upserts today's row on every authenticated request,
which is cheap and idempotent.

`learner_points_ledger` is an append-only ledger of point awards.
Each row carries the source kind + a free-form source id so we can
audit / replay / dedupe. Current writers:
  - CORRECT_ANSWER     +1 per correct auto-graded answer on a submission
  - PERFECT_SCORE_BONUS +5 on a perfect submission
  - PRACTICE_DAY_BONUS  +2 on the first submission of a day
  - WEEKLY_GOAL_BONUS  +10 when the weekly target is hit

The ledger approach (vs a single `total_points` column on User) lets
us recompute totals from the source-of-truth events at any time,
which is cheap when learners have hundreds of rows, not millions.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260525_0025"
down_revision: Union[str, None] = "20260517_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learner_login_days",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Date, nullable=False),
        sa.PrimaryKeyConstraint("user_id", "day", name="pk_learner_login_days"),
    )
    op.create_index(
        "ix_learner_login_days_user_id", "learner_login_days", ["user_id"]
    )

    op.create_table(
        "learner_points_ledger",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_kind", sa.String(40), nullable=False),
        # Free-form integer reference into the source row (e.g. submission_id
        # for CORRECT_ANSWER / PERFECT_SCORE_BONUS). Nullable so future
        # sources without a single integer key can still be recorded.
        sa.Column("source_id", sa.Integer, nullable=True),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Optional natural-key dedupe field. For source kinds that are
        # awarded once per (user, day) or per (user, week), we encode
        # the natural key here so a UNIQUE constraint blocks doubles
        # even under racy concurrent writes.
        sa.Column("dedupe_key", sa.String(80), nullable=True),
        sa.UniqueConstraint(
            "user_id", "dedupe_key", name="uq_points_ledger_user_dedupe"
        ),
    )
    op.create_index(
        "ix_learner_points_ledger_awarded_at",
        "learner_points_ledger",
        ["awarded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learner_points_ledger_awarded_at", table_name="learner_points_ledger"
    )
    op.drop_table("learner_points_ledger")
    op.drop_index(
        "ix_learner_login_days_user_id", table_name="learner_login_days"
    )
    op.drop_table("learner_login_days")
