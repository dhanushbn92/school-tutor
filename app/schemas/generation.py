from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.generation import GeneratedContentStatus, GeneratedContentType


class GenerateContentRequest(BaseModel):
    content_type: GeneratedContentType
    academic_year: str = "2026-27"
    class_level: int = Field(ge=6, le=12)
    subject_id: int
    chapter_id: int | None = None
    topic_id: int | None = None
    title: str | None = None
    prompt: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    force_regenerate: bool = False


class UploadStructuredContentRequest(BaseModel):
    """Platform-admin payload for uploading hand-crafted structured content
    (chapter summary, lesson plan, worksheet, …) without going through the
    LLM pipeline. The payload's `output_json` is validated server-side
    against the appropriate Pydantic schema for `content_type`."""

    content_type: GeneratedContentType
    class_level: int = Field(ge=1, le=12)
    subject_id: int
    chapter_id: int | None = None
    topic_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    output_json: dict[str, Any]


class GeneratedContentRead(BaseModel):
    id: int
    content_type: GeneratedContentType
    status: GeneratedContentStatus
    cache_key: str
    academic_year: str
    class_level: int
    subject_id: int | None
    chapter_id: int | None
    topic_id: int | None
    title: str
    prompt: str | None
    output_text: str | None
    output_json: dict[str, Any] | None
    artifact_url: str | None
    request_options: dict[str, Any] | None
    error_message: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    created_by_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

