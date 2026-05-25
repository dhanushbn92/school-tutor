"""Add learner_audio_preferences table

Revision ID: 20260526_0030
Revises: 20260526_0029
Create Date: 2026-05-26

Stage 8 of the child-centric roadmap — read-aloud everywhere.

One row per learner storing audio preferences:
  - `autoplay_questions`   — start reading the question aloud when
                              it first appears on screen (off by
                              default; bright kids find it
                              distracting, quieter ones love it)
  - `preferred_voice_uri`  — the browser SpeechSynthesisVoice URI
                              the learner picked from the dropdown.
                              Stored as a free-form string so we
                              don't need to enumerate every voice
                              the browser might expose.

Read-aloud itself uses the browser's native SpeechSynthesis API —
no server-side TTS, no API key cost. The backend just remembers
what the learner asked for.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0030"
down_revision: Union[str, None] = "20260526_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learner_audio_preferences",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "autoplay_questions",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "preferred_voice_uri",
            sa.String(200),
            nullable=True,
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
        sa.UniqueConstraint("user_id", name="uq_learner_audio_user"),
    )


def downgrade() -> None:
    op.drop_table("learner_audio_preferences")
