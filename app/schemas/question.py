from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.curriculum import BloomLevel
from app.models.question import QuestionDifficulty, QuestionStatus, QuestionType


class QuestionRead(BaseModel):
    id: int
    chapter_id: int
    topic_id: int | None
    outcome_id: int | None
    outcome_code: str | None
    type: QuestionType
    difficulty: QuestionDifficulty
    cognitive_level: BloomLevel
    status: QuestionStatus
    text: str
    options: dict[str, Any] | None
    correct_answer: str
    explanation: str | None
    explanation_rich: dict[str, Any] | None = None
    marks: int
    source_generated_content_id: int | None
    created_by_id: int
    reviewed_by_id: int | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionUpdate(BaseModel):
    """Partial update. Any omitted field is left untouched."""

    text: str | None = Field(default=None, min_length=5, max_length=2000)
    options: dict[str, Any] | None = None
    correct_answer: str | None = Field(default=None, min_length=1, max_length=2000)
    explanation: str | None = None
    marks: int | None = Field(default=None, ge=1, le=10)
    difficulty: QuestionDifficulty | None = None
    cognitive_level: BloomLevel | None = None
    type: QuestionType | None = None
    outcome_id: int | None = None
    topic_id: int | None = None
    review_notes: str | None = None


class ApprovalRequest(BaseModel):
    review_notes: str | None = None
