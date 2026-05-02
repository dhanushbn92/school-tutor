from pydantic import BaseModel, Field


class LessonActivity(BaseModel):
    phase: str = Field(
        description="Phase label: 'Engage' / 'Explore' / 'Explain' / 'Elaborate' / 'Evaluate' / 'Assign'.",
        min_length=3,
        max_length=40,
    )
    duration_minutes: int = Field(ge=1, le=60)
    description: str = Field(min_length=10, max_length=2000)
    teacher_actions: list[str] = Field(min_length=1)
    student_actions: list[str] = Field(default_factory=list)


class LessonPlanOutput(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    class_level: int = Field(ge=1, le=12)
    subject: str = Field(min_length=2, max_length=80)
    chapter_title: str = Field(min_length=3, max_length=200)
    duration_minutes: int = Field(ge=20, le=120)

    objectives: list[str] = Field(
        min_length=2,
        description="Student-facing 'learning objectives' in outcome language.",
    )
    prerequisites: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    key_vocabulary: list[str] = Field(default_factory=list)

    activities: list[LessonActivity] = Field(
        min_length=2,
        description="Sequenced phases; should cover the full duration.",
    )

    homework: list[str] = Field(default_factory=list)
    assessment_ideas: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    outcome_codes_covered: list[str] = Field(
        default_factory=list,
        description="LearningOutcome codes covered, e.g. ['6-SCI-WOS-02', '6-SCI-WOS-03'].",
    )
