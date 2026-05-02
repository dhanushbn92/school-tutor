"""add learning_outcomes table

Revision ID: 20260423_0002
Revises: 20260423_0001
Create Date: 2026-04-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260423_0002"
down_revision: Union[str, None] = "20260423_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


bloom_enum = sa.Enum(
    "REMEMBER",
    "UNDERSTAND",
    "APPLY",
    "ANALYZE",
    "EVALUATE",
    "CREATE",
    name="bloomlevel",
)


def upgrade() -> None:
    op.create_table(
        "learning_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("bloom_level", bloom_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "code", name="uq_learning_outcomes_chapter_code"),
    )
    op.create_index(op.f("ix_learning_outcomes_chapter_id"), "learning_outcomes", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_learning_outcomes_topic_id"), "learning_outcomes", ["topic_id"], unique=False)
    op.create_index(op.f("ix_learning_outcomes_code"), "learning_outcomes", ["code"], unique=False)
    op.create_index(op.f("ix_learning_outcomes_bloom_level"), "learning_outcomes", ["bloom_level"], unique=False)


def downgrade() -> None:
    op.drop_table("learning_outcomes")
    bloom_enum.drop(op.get_bind(), checkfirst=True)
