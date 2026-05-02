from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterventionNoteRead(BaseModel):
    id: int
    student_id: int
    teacher_id: int
    chapter_id: int | None
    topic_id: int | None
    note: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateInterventionNoteRequest(BaseModel):
    student_id: int
    note: str = Field(min_length=5, max_length=2000)
    chapter_id: int | None = None
    topic_id: int | None = None
