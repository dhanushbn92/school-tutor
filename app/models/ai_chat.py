"""Premium AI tutor chat — sessions and messages.

A session is bound to exactly one chapter or one topic. Each LLM turn is
RAG-style: the chapter or topic text is the only source of truth and the
prompt instructs the model to refuse off-topic questions.
"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatScope(StrEnum):
    CHAPTER = "CHAPTER"
    TOPIC = "TOPIC"


class ChatRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        # Exactly one of chapter_id or topic_id must be set, matching `scope`.
        CheckConstraint(
            "(scope = 'CHAPTER' AND chapter_id IS NOT NULL AND topic_id IS NULL)"
            " OR (scope = 'TOPIC' AND topic_id IS NOT NULL)",
            name="ck_chat_sessions_scope_xor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    scope: Mapped[ChatScope] = mapped_column(Enum(ChatScope), index=True)
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))

    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student = relationship("Student")
    chapter = relationship("Chapter")
    topic = relationship("Topic")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
