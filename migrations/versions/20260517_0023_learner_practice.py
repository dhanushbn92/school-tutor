"""Add learner_weekly_goals + learner_stamps tables

Revision ID: 20260517_0023
Revises: 20260430_0022
Create Date: 2026-05-17

First migration in support of the child-centric roadmap (Stage 1 —
streaks + small rewards). Both tables are tiny, single-tenant per
user, and have no foreign keys outside `users`.

  learner_weekly_goals  one row per (user, ISO-week-start). The number
                        of practice days the learner is aiming for that
                        week. Defaults to 4. Re-set freely week to week.

  learner_stamps        one row per stamp earned. PRACTICE_DAY and
                        WEEKLY_GOAL_MET kinds are deduplicated at the
                        service layer (the natural key lives inside
                        the JSON metadata blob, not a column we could
                        UNIQUE).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260517_0023"
down_revision: Union[str, None] = "20260430_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learner_weekly_goals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("target_days", sa.Integer, nullable=False, server_default="4"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "week_start", name="uq_learner_weekly_goal_user_week"
        ),
    )
    op.create_index(
        "ix_learner_weekly_goals_user_id",
        "learner_weekly_goals",
        ["user_id"],
    )
    op.create_index(
        "ix_learner_weekly_goals_week_start",
        "learner_weekly_goals",
        ["week_start"],
    )

    op.create_table(
        "learner_stamps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "earned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("stamp_metadata", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_learner_stamps_user_id", "learner_stamps", ["user_id"]
    )
    op.create_index("ix_learner_stamps_kind", "learner_stamps", ["kind"])
    op.create_index(
        "ix_learner_stamps_earned_at", "learner_stamps", ["earned_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_learner_stamps_earned_at", table_name="learner_stamps")
    op.drop_index("ix_learner_stamps_kind", table_name="learner_stamps")
    op.drop_index("ix_learner_stamps_user_id", table_name="learner_stamps")
    op.drop_table("learner_stamps")
    op.drop_index(
        "ix_learner_weekly_goals_week_start", table_name="learner_weekly_goals"
    )
    op.drop_index(
        "ix_learner_weekly_goals_user_id", table_name="learner_weekly_goals"
    )
    op.drop_table("learner_weekly_goals")
