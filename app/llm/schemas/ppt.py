from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SlideType(StrEnum):
    TITLE = "TITLE"
    OBJECTIVES = "OBJECTIVES"
    CONCEPT = "CONCEPT"
    EXAMPLE = "EXAMPLE"
    ACTIVITY = "ACTIVITY"
    QUICK_CHECK = "QUICK_CHECK"
    SUMMARY = "SUMMARY"


class Slide(BaseModel):
    slide_type: SlideType
    title: str = Field(min_length=2, max_length=120)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    speaker_notes: str | None = Field(default=None, max_length=2000)


class PPTOutlineOutput(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    class_level: int = Field(ge=1, le=12)
    subject: str = Field(min_length=2, max_length=80)
    chapter_title: str = Field(min_length=3, max_length=200)
    slides: list[Slide] = Field(min_length=4, max_length=20)
    outcome_codes_covered: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_structure(self) -> "PPTOutlineOutput":
        if self.slides[0].slide_type != SlideType.TITLE:
            raise ValueError("First slide must be of type TITLE.")
        last_types = {self.slides[-1].slide_type, self.slides[-2].slide_type if len(self.slides) > 1 else None}
        if SlideType.SUMMARY not in last_types:
            raise ValueError("Deck must end with a SUMMARY slide (in the last 2 positions).")
        return self
