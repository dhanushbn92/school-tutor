from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.curriculum import BloomLevel


class QuestionType(StrEnum):
    MCQ = "MCQ"
    SHORT_ANSWER = "SHORT_ANSWER"
    LONG_ANSWER = "LONG_ANSWER"
    FILL_BLANK = "FILL_BLANK"
    TRUE_FALSE = "TRUE_FALSE"
    CASE_BASED = "CASE_BASED"


class QuestionDifficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_outcomes.id", ondelete="SET NULL"), index=True
    )
    outcome_code: Mapped[str | None] = mapped_column(String(40), index=True)

    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), index=True)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(Enum(QuestionDifficulty), index=True)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus), default=QuestionStatus.DRAFT, index=True
    )
    # 6-level Bloom — canonical signal. The student/teacher UI usually rolls
    # this up to a 3-bucket label (FACTUAL/UNDERSTANDING/APPLICATION) via
    # app.services.cognitive.to_bucket().
    cognitive_level: Mapped[BloomLevel] = mapped_column(
        Enum(BloomLevel, name="bloomlevel", create_type=False),
        default=BloomLevel.UNDERSTAND,
        index=True,
    )

    text: Mapped[str] = mapped_column(Text)
    options: Mapped[dict | None] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    # Optional structured rich-explanation blocks for subjective/long-answer
    # questions. Shape: {"blocks": [{"type":"text"|"list"|"mind_map"|"flow_diagram", ...}, ...]}.
    # Frontend renders each block based on its type. Plain `explanation` is
    # still authoritative for short questions; this is a richer alternative.
    explanation_rich: Mapped[dict | None] = mapped_column(JSON)
    # Optional rubric for keyword-based auto-grading of subjective answers.
    # Shape: {"method":"keywords","min_words":int,"groups":[
    #   {"label": "...","any_of": ["phrase1","phrase2"],"marks": float}, ...
    # ]}.
    auto_grade: Mapped[dict | None] = mapped_column(JSON)
    marks: Mapped[int] = mapped_column(Integer, default=1)

    source_generated_content_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_contents.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chapter = relationship("Chapter")
    topic = relationship("Topic")
    outcome = relationship("LearningOutcome")
    source_generated_content = relationship("GeneratedContent")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
