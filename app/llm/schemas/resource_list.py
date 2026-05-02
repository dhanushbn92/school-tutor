from pydantic import BaseModel, Field, HttpUrl


class ResourceItem(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    url: HttpUrl
    kind: str = Field(
        description="Short kind label, e.g. 'video', 'article', 'simulation', 'image', 'pdf'.",
        min_length=2,
        max_length=30,
    )
    summary: str = Field(min_length=10, max_length=400)
    estimated_time_minutes: int | None = Field(default=None, ge=1, le=120)
    note_for_teacher: str | None = Field(default=None, max_length=300)


class ResourceListOutput(BaseModel):
    """Curated extra resources for a chapter (LLM-suggested, admin-approved)."""

    chapter_focus: str = Field(min_length=5, max_length=200)
    intro: str = Field(min_length=10, max_length=500)
    items: list[ResourceItem] = Field(min_length=1, max_length=12)
