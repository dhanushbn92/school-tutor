"""Add learner_mascot_state table

Revision ID: 20260526_0027
Revises: 20260525_0026
Create Date: 2026-05-26

Stage 5 of the child-centric roadmap — the Vidyārthi mascot
companion. One row per learner stores whether the mascot is enabled
on their pages and which outfit they've equipped. Outfits are
forward-compatible: the column is a free-form string so adding a
new outfit ("monsoon-kurta", "diwali-special") is a config change,
not a migration. Until Stage 5.x ships the unlock pipeline, only
"default" is a valid value.

The table is per-user with no FK chain to schools — mascot
preferences are personal and follow the learner across enrolment
changes (same pattern as stamps).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0027"
down_revision: Union[str, None] = "20260525_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learner_mascot_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "current_outfit",
            sa.String(40),
            nullable=False,
            server_default="default",
        ),
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
        sa.UniqueConstraint("user_id", name="uq_learner_mascot_user"),
    )


def downgrade() -> None:
    op.drop_table("learner_mascot_state")
