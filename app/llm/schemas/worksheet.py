from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class WorksheetQuestionType(StrEnum):
    MCQ = "MCQ"
    SHORT_ANSWER = "SHORT_ANSWER"
    LONG_ANSWER = "LONG_ANSWER"
    FILL_BLANK = "FILL_BLANK"
    TRUE_FALSE = "TRUE_FALSE"
    CASE_BASED = "CASE_BASED"


class WorksheetDifficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class WorksheetCognitiveLevel(StrEnum):
    """6-level Bloom's taxonomy. Stored as the canonical signal on every
    question. The student/teacher UI rolls these up to a 3-bucket label
    (REMEMBER -> Factual, UNDERSTAND -> Understanding, the rest -> Application)."""

    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class WorksheetQuestion(BaseModel):
    type: WorksheetQuestionType
    question: str = Field(min_length=5, max_length=2000)
    options: list[str] | None = Field(
        default=None,
        description="For MCQ and TRUE_FALSE. Exactly 4 for MCQ, exactly 2 for TRUE_FALSE.",
    )
    answer: str = Field(
        min_length=1,
        max_length=2000,
        description="Correct answer for objective questions; model answer for subjective.",
    )
    explanation: str | None = Field(default=None, max_length=2000)
    marks: int = Field(ge=1, le=10)
    difficulty: WorksheetDifficulty
    cognitive_level: WorksheetCognitiveLevel = Field(
        default=WorksheetCognitiveLevel.UNDERSTAND,
        description=(
            "Bloom's taxonomy level the question is testing. Pick from REMEMBER, "
            "UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE."
        ),
    )
    outcome_code: str | None = Field(
        default=None,
        description="Learning outcome code the question targets, e.g. '6-SCI-MOS-01'.",
    )

    @model_validator(mode="after")
    def _check_options(self) -> "WorksheetQuestion":
        if self.type == WorksheetQuestionType.MCQ:
            if not self.options or len(self.options) != 4:
                raise ValueError("MCQ questions must have exactly 4 options.")
            if self.answer not in self.options:
                raise ValueError("MCQ answer must be one of the options.")
        elif self.type == WorksheetQuestionType.TRUE_FALSE:
            if not self.options or set(opt.lower() for opt in self.options) != {"true", "false"}:
                raise ValueError("TRUE_FALSE options must be ['True', 'False'].")
        return self


class WorksheetOutput(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    instructions: str = Field(min_length=10, max_length=1000)
    total_marks: int = Field(ge=1)
    questions: list[WorksheetQuestion] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _check_total_marks(self) -> "WorksheetOutput":
        computed = sum(q.marks for q in self.questions)
        if computed != self.total_marks:
            raise ValueError(
                f"total_marks={self.total_marks} does not match sum of question marks={computed}."
            )
        return self
