from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CognitiveBucket(StrEnum):
    """Coarse 3-level grouping shown to students and teachers.

    Maps from the question's 6-level Bloom (REMEMBER/UNDERSTAND/APPLY/...)
    via `app.services.cognitive.to_bucket()`. The 6-level signal stays
    canonical on `Question.cognitive_level`; this 3-level label is for UI
    + per-bucket mastery tracking.
    """

    FACTUAL = "FACTUAL"
    UNDERSTANDING = "UNDERSTANDING"
    APPLICATION = "APPLICATION"


class SkillMastery(Base):
    """Running mastery estimate per (student, outcome).

    Updated via EWMA when a submission transitions to EVALUATED.
    `mastery` is in [0, 1].
    """

    __tablename__ = "skill_mastery"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "outcome_id",
            "cognitive_bucket",
            name="uq_skill_mastery_student_outcome_bucket",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    outcome_id: Mapped[int] = mapped_column(
        ForeignKey("learning_outcomes.id", ondelete="CASCADE"), index=True
    )
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )
    cognitive_bucket: Mapped[CognitiveBucket] = mapped_column(
        Enum(CognitiveBucket), index=True
    )
    mastery: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student")
    outcome = relationship("LearningOutcome")
    chapter = relationship("Chapter")
    topic = relationship("Topic")
