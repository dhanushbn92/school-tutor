"""Video lectures attached to a chapter.

A chapter can have several ordered parts (e.g. "The Lesson", then
"Word by Word - Part 1..4"). Rows are kept in their own table rather than as a
``GeneratedContent`` type so that:

* adding videos never touches the native Postgres ``generatedcontenttype``
  enum (an ``ALTER TYPE ... ADD VALUE`` cannot be rolled back), and
* the hosting provider is a column, so lectures can move from a Google Drive
  embed to self-hosted storage later without a schema change.

Only the provider-specific identifier is stored (``external_id``); the player
URL is built by the client from a validated id, never taken from the database
as a free-form URL.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VideoProvider(StrEnum):
    """Where the video bytes live. Stored as a plain string so a new provider
    needs no migration."""

    GDRIVE = "gdrive"


class ChapterVideo(Base):
    __tablename__ = "chapter_videos"
    __table_args__ = (
        UniqueConstraint("chapter_id", "sequence", name="uq_chapter_videos_chapter_sequence"),
        UniqueConstraint(
            "provider", "external_id", "chapter_id", name="uq_chapter_videos_provider_external"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    # 1-based play order within the chapter.
    sequence: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    # "lesson" (the main lecture) or "word_by_word" (verse-by-verse walkthrough).
    kind: Mapped[str] = mapped_column(String(30), default="lesson")
    provider: Mapped[str] = mapped_column(String(20), default=VideoProvider.GDRIVE.value)
    external_id: Mapped[str] = mapped_column(String(200))
    # Draft rows are hidden from learners.
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
