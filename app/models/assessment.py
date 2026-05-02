from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentType(StrEnum):
    WORKSHEET = "WORKSHEET"
    QUIZ = "QUIZ"
    UNIT_TEST = "UNIT_TEST"
    EXAM = "EXAM"


class AssessmentStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class SubmissionStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    EVALUATED = "EVALUATED"
    LATE = "LATE"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), index=True)

    type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType), index=True)
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus), default=AssessmentStatus.DRAFT, index=True
    )

    title: Mapped[str] = mapped_column(String(300))
    instructions: Mapped[str | None] = mapped_column(Text)
    total_marks: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    section = relationship("Section")
    subject = relationship("Subject")
    chapter = relationship("Chapter")
    created_by = relationship("User")
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.order"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "question_id", name="uq_assessment_questions_aq"),
        UniqueConstraint("assessment_id", "order", name="uq_assessment_questions_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    marks_override: Mapped[int | None] = mapped_column(Integer)

    assessment: Mapped[Assessment] = relationship(back_populates="questions")
    question = relationship("Question")

    @property
    def marks(self) -> int:
        """Effective marks — override if set, else the question's default."""
        if self.marks_override is not None:
            return self.marks_override
        return self.question.marks if self.question is not None else 0

    @property
    def question_text(self) -> str | None:
        return self.question.text if self.question is not None else None

    @property
    def question_type(self) -> str | None:
        return self.question.type.value if self.question is not None else None


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", name="uq_submissions_assessment_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.DRAFT, index=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_awarded: Mapped[int | None] = mapped_column(Integer)
    max_marks: Mapped[int] = mapped_column(Integer)
    uploaded_file_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assessment: Mapped[Assessment] = relationship(back_populates="submissions")
    student = relationship("Student")
    answers: Mapped[list["SubmissionAnswer"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"
    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_submission_answers_sq"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"), index=True)
    answer_text: Mapped[str | None] = mapped_column(Text)
    marks_awarded: Mapped[int | None] = mapped_column(Integer)
    max_marks: Mapped[int] = mapped_column(Integer)
    auto_graded: Mapped[bool] = mapped_column(Boolean, default=False)
    # Per-answer breakdown produced by the rubric grader for subjective answers.
    # Shape: {"method":"keywords","matched":[{"label","matched_phrase"}],"missed":[{"label","any_of"}],"min_words_ok":bool}.
    grading_details: Mapped[dict | None] = mapped_column(JSON)
    teacher_remark: Mapped[str | None] = mapped_column(Text)

    submission: Mapped[Submission] = relationship(back_populates="answers")
    question = relationship("Question")
