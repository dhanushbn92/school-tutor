from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment import AssessmentStatus, AssessmentType, SubmissionStatus


class AssessmentQuestionRead(BaseModel):
    id: int
    question_id: int
    order: int
    marks_override: int | None
    marks: int = Field(
        default=0,
        description="Effective marks for this slot — marks_override if set, else the question's default marks.",
    )
    question_text: str | None = Field(
        default=None,
        description="Convenience copy of the question text so the assessment detail page can render without an N+1.",
    )
    question_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentRead(BaseModel):
    id: int
    section_id: int
    subject_id: int
    chapter_id: int | None
    type: AssessmentType
    status: AssessmentStatus
    title: str
    instructions: str | None
    total_marks: int
    duration_minutes: int | None
    due_at: datetime | None
    published_at: datetime | None
    created_by_id: int
    created_at: datetime
    questions: list[AssessmentQuestionRead] = []

    model_config = ConfigDict(from_attributes=True)


class CreateAssessmentRequest(BaseModel):
    section_id: int
    subject_id: int
    chapter_id: int | None = None
    type: AssessmentType = AssessmentType.QUIZ
    title: str = Field(min_length=3, max_length=300)
    instructions: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    due_at: datetime | None = None
    question_ids: list[int] = Field(min_length=1, max_length=100)
    marks_overrides: dict[int, int] | None = None


class FromBankRequest(BaseModel):
    """Build a quiz by sampling questions from the global bank.

    Pass `chapter_id` for a single-chapter quiz or `chapter_ids` for a
    cumulative test that spans multiple chapters of the same subject.
    Exactly one of the two must be set.
    """

    section_id: int
    subject_id: int
    chapter_id: int | None = None
    chapter_ids: list[int] | None = Field(
        default=None,
        description="For a cumulative test across chapters; pass at least 2 chapter IDs.",
    )
    topic_id: int | None = None
    type: AssessmentType = AssessmentType.QUIZ
    title: str = Field(min_length=3, max_length=300)
    instructions: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    due_at: datetime | None = None
    question_count: int = Field(ge=1, le=50)
    difficulty_mix: dict[str, int] | None = Field(
        default=None,
        description='Per-difficulty counts, e.g. {"EASY": 4, "MEDIUM": 4, "HARD": 2}. Sums must equal question_count.',
    )
    type_mix: dict[str, int] | None = Field(
        default=None,
        description='Per-type counts, e.g. {"MCQ": 6, "SHORT_ANSWER": 2, "TRUE_FALSE": 2}. Sums must equal question_count.',
    )
    cognitive_mix: dict[str, int] | None = Field(
        default=None,
        description=(
            'Per-cognitive-bucket counts, e.g. {"FACTUAL": 3, "UNDERSTANDING": 4, "APPLICATION": 3}. '
            "Sums must equal question_count. Buckets roll up Bloom: "
            "FACTUAL=REMEMBER, UNDERSTANDING=UNDERSTAND, APPLICATION=APPLY/ANALYZE/EVALUATE/CREATE. "
            "When combined with difficulty_mix or type_mix, the cognitive mix is the outer constraint."
        ),
    )


class SubmissionAnswerRead(BaseModel):
    id: int
    question_id: int
    answer_text: str | None
    marks_awarded: int | None
    max_marks: int
    auto_graded: bool
    grading_details: dict | None = None
    teacher_remark: str | None

    model_config = ConfigDict(from_attributes=True)


class SubmissionRead(BaseModel):
    id: int
    assessment_id: int
    student_id: int
    status: SubmissionStatus
    submitted_at: datetime | None
    evaluated_at: datetime | None
    total_awarded: int | None
    max_marks: int
    uploaded_file_url: str | None
    answers: list[SubmissionAnswerRead] = []

    model_config = ConfigDict(from_attributes=True)


class SubmitAssessmentRequest(BaseModel):
    """Student submits: `answers` maps `question_id -> answer_text`."""

    answers: dict[int, str]


class GradeAnswerRequest(BaseModel):
    marks_awarded: int = Field(ge=0)
    teacher_remark: str | None = None
