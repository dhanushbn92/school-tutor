from pydantic import BaseModel, Field


class ActivityStep(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    detail: str = Field(min_length=10, max_length=600)


class ClassroomActivity(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    duration_minutes: int = Field(ge=5, le=60)
    objective: str = Field(min_length=10, max_length=300)
    materials: list[str] = Field(default_factory=list, max_length=15)
    steps: list[ActivityStep] = Field(min_length=2, max_length=10)
    guiding_questions: list[str] = Field(default_factory=list, max_length=8)
    safety_notes: list[str] = Field(default_factory=list, max_length=5)
    variations: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional ways to extend or simplify the activity for different classes.",
    )


class ClassroomActivitySetOutput(BaseModel):
    """Bundle of classroom activities authored together for a single chapter."""

    title: str = Field(min_length=3, max_length=200)
    chapter_focus: str = Field(min_length=5, max_length=200)
    activities: list[ClassroomActivity] = Field(min_length=1, max_length=8)
