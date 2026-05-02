"""AI tutor chat — premium feature flag, sessions, messages, topic.full_text

Revision ID: 20260428_0018
Revises: 20260427_0017
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260428_0018"
down_revision: Union[str, None] = "20260427_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-user premium flag.
    op.add_column(
        "users",
        sa.Column(
            "ai_chat_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Topic-specific text slice for topic-scoped chat sessions.
    op.add_column("topics", sa.Column("full_text", sa.Text(), nullable=True))

    # Each enum is used in exactly one table below — let SQLAlchemy emit
    # the CREATE TYPE during create_table.
    chat_scope = sa.Enum("CHAPTER", "TOPIC", name="chatscope")
    chat_role = sa.Enum("USER", "ASSISTANT", name="chatrole")

    # Sessions table.
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope", chat_scope, nullable=False),
        sa.Column(
            "chapter_id",
            sa.Integer(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(scope = 'CHAPTER' AND chapter_id IS NOT NULL AND topic_id IS NULL)"
            " OR (scope = 'TOPIC' AND topic_id IS NOT NULL)",
            name="ck_chat_sessions_scope_xor",
        ),
    )
    op.create_index(op.f("ix_chat_sessions_student_id"), "chat_sessions", ["student_id"])
    op.create_index(op.f("ix_chat_sessions_scope"), "chat_sessions", ["scope"])
    op.create_index(op.f("ix_chat_sessions_chapter_id"), "chat_sessions", ["chapter_id"])
    op.create_index(op.f("ix_chat_sessions_topic_id"), "chat_sessions", ["topic_id"])

    # Messages table.
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", chat_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_messages_session_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index(op.f("ix_chat_sessions_topic_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_chapter_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_scope"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_student_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")

    sa.Enum(name="chatrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="chatscope").drop(op.get_bind(), checkfirst=True)

    op.drop_column("topics", "full_text")
    op.drop_column("users", "ai_chat_enabled")
