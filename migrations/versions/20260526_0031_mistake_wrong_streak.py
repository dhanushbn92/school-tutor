"""Add wrong_streak to learner_mistakes

Revision ID: 20260526_0031
Revises: 20260526_0030
Create Date: 2026-05-26

Stage 9 of the child-centric roadmap — kinder UX for wrong answers.

Tracks how many times a learner has gotten the same mistake-question
wrong IN A ROW, so the UI can surface a "Want a hint?" button after
the third failed attempt. Resets to 0 on every correct retry. This
is the wrong-side counterpart to the existing `consecutive_corrects`
field (which counts right-in-a-row for the twice-right rule).

Storing it server-side rather than in component state means the
trigger survives page reloads + cross-device sessions — a learner
who's been stuck on a question for two days should see the hint
even if they restart their browser.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0031"
down_revision: Union[str, None] = "20260526_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learner_mistakes",
        sa.Column(
            "wrong_streak",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("learner_mistakes", "wrong_streak")
