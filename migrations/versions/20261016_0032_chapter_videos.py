"""Add chapter_videos

Revision ID: 20261016_0032
Revises: 20260526_0031
Create Date: 2026-10-16

Video lectures attached to a chapter, shown on the learn page between the
summary and the worksheets. A separate table (not a GeneratedContent type) so
the native `generatedcontenttype` Postgres enum is left untouched and several
ordered parts per chapter are first-class. Purely additive.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261016_0032"
down_revision: Union[str, None] = "20260526_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chapter_videos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "chapter_id",
            sa.Integer,
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False, server_default="lesson"),
        sa.Column("provider", sa.String(20), nullable=False, server_default="gdrive"),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("chapter_id", "sequence", name="uq_chapter_videos_chapter_sequence"),
        sa.UniqueConstraint(
            "provider", "external_id", "chapter_id", name="uq_chapter_videos_provider_external"
        ),
    )
    op.create_index("ix_chapter_videos_chapter_id", "chapter_videos", ["chapter_id"])


def downgrade() -> None:
    op.drop_index("ix_chapter_videos_chapter_id", table_name="chapter_videos")
    op.drop_table("chapter_videos")
