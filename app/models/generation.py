from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedContentType(StrEnum):
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    HALF_YEARLY_EXAM = "half_yearly_exam"
    PPT = "ppt"
    DIAGRAM = "diagram"
    SIMULATION = "simulation"
    LESSON_PLAN = "lesson_plan"
    CHAPTER_SUMMARY = "chapter_summary"
    CLASSROOM_ACTIVITY = "classroom_activity"
    # Curated external-link list — no longer surfaced in the SPA. Kept on the
    # enum so existing rows still validate; new ones are no longer generated.
    RESOURCE_LIST = "resource_list"
    FLOW_DIAGRAM = "flow_diagram"
    # Platform-admin-uploaded supplementary documents (PDF/DOCX). Stored as a
    # raw file artefact, viewed inline in the SPA, never downloadable in-UI.
    EXTRA_CONTENT = "extra_content"


class GeneratedContentStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    APPROVED = "approved"
    FAILED = "failed"


class GeneratedContent(Base):
    __tablename__ = "generated_contents"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_generated_contents_cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content_type: Mapped[GeneratedContentType] = mapped_column(Enum(GeneratedContentType), index=True)
    status: Mapped[GeneratedContentStatus] = mapped_column(
        Enum(GeneratedContentStatus), default=GeneratedContentStatus.PENDING, index=True
    )
    cache_key: Mapped[str] = mapped_column(String(128), index=True)
    academic_year: Mapped[str] = mapped_column(String(20), index=True)
    class_level: Mapped[int] = mapped_column(Integer, index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    prompt: Mapped[str | None] = mapped_column(Text)
    source_context: Mapped[str | None] = mapped_column(Text)
    output_text: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[dict | None] = mapped_column(JSON)
    artifact_url: Mapped[str | None] = mapped_column(Text)
    llm_provider: Mapped[str | None] = mapped_column(String(80))
    llm_model: Mapped[str | None] = mapped_column(String(120))
    request_options: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

