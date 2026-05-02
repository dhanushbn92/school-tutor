from pydantic import BaseModel, Field, model_validator

from app.llm.schemas.worksheet import WorksheetQuestion


class QuizOutput(BaseModel):
    """A quiz is a set of discrete, bank-worthy questions.

    Shape is identical to WorksheetOutput; kept separate so prompt/validation
    can diverge later (e.g. quiz can require question-level timers).
    """

    title: str = Field(min_length=5, max_length=200)
    instructions: str = Field(min_length=10, max_length=1000)
    total_marks: int = Field(ge=1)
    questions: list[WorksheetQuestion] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _check_total_marks(self) -> "QuizOutput":
        computed = sum(q.marks for q in self.questions)
        if computed != self.total_marks:
            raise ValueError(
                f"total_marks={self.total_marks} does not match sum of question marks={computed}."
            )
        return self
