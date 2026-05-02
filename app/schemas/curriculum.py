from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AcademicYearRead(BaseModel):
    id: int
    name: str
    is_current: bool

    model_config = ConfigDict(from_attributes=True)


class SchoolClassRead(BaseModel):
    id: int
    level: int
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class SubjectRead(BaseModel):
    id: int
    class_id: int
    name: str
    language: str
    # Syllabus board (CBSE / NIOS / ICSE / State Board / Other). Always
    # present; backfill migration pinned legacy rows to "CBSE".
    board: str

    model_config = ConfigDict(from_attributes=True)


class BookRead(BaseModel):
    id: int
    subject_id: int
    title: str
    ncert_code: str
    academic_year: str
    source_url: str | None

    model_config = ConfigDict(from_attributes=True)


class TopicRead(BaseModel):
    id: int
    chapter_id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class ChapterSectionRead(BaseModel):
    id: int
    chapter_id: int
    section_number: str
    title: str
    section_text: str
    page_start: int | None
    page_end: int | None

    model_config = ConfigDict(from_attributes=True)


class ChapterRead(BaseModel):
    id: int
    book_id: int
    chapter_number: int
    title: str
    source_url: str | None
    page_count: int | None

    model_config = ConfigDict(from_attributes=True)


class ChapterDetailRead(ChapterRead):
    full_text: str
    sections: list[ChapterSectionRead] = []
    topics: list[TopicRead] = []
    # Denormalised subject context — populated by the route handler from
    # the eager-loaded `chapter.book.subject` relationship. Optional so
    # that the field stays additive (older clients keep working) and the
    # response degrades gracefully if the relationship isn't loaded.
    subject_id: int | None = None
    subject_name: str | None = None


class LearningOutcomeRead(BaseModel):
    code: str
    description: str
    bloom_level: str
    topic_id: int | None = None


class CurriculumContextRead(BaseModel):
    academic_year: str
    class_level: int
    subject: str
    book: str
    chapter_id: int
    chapter_number: int
    chapter_title: str
    chapter_text: str
    context_text: str
    topic: str | None
    topics: list[str] = []
    outcomes: list[LearningOutcomeRead] = []
    source_url: str | None


# ---------------------------------------------------------------------------
# Ingestion request payloads (platform-admin chapter onboarding from UI).
# Match the curriculum_ingest_service signatures.
# ---------------------------------------------------------------------------


class CreateSubjectRequest(BaseModel):
    """Body for `POST /curriculum/subjects` — platform-admin endpoint to
    seed a new subject under an existing class for a given board. The
    `(class_id, name, language, board)` tuple is uniquely constrained,
    so duplicates surface as HTTP 400."""

    class_id: int
    name: str = Field(min_length=2, max_length=120)
    language: str = Field(default="en", min_length=2, max_length=20)
    board: str = Field(default="CBSE")


class CreateBookRequest(BaseModel):
    """Body for `POST /curriculum/books` — platform-admin endpoint to
    seed a new book under an existing subject. Mirrors the structure of
    the NCERT manifest entries."""

    subject_id: int
    title: str = Field(min_length=2, max_length=200)
    ncert_code: str = Field(min_length=1, max_length=20)
    academic_year: str = Field(min_length=4, max_length=20)
    source_url: str | None = None


class CreateChapterRequest(BaseModel):
    """Body for `POST /curriculum/chapters` — create a chapter under an
    existing book. The full text is provided directly (paste / extracted
    from PDF on the client side, or via the `extract-pdf-text` helper)."""

    book_id: int
    chapter_number: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=300)
    full_text: str = Field(min_length=10)
    source_url: str | None = None
    page_count: int | None = Field(default=None, ge=0)


class TopicItem(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=2000)


class BulkTopicsRequest(BaseModel):
    """Body for `POST /curriculum/chapters/{id}/topics` — replace the
    chapter's topics with the supplied list."""

    topics: list[TopicItem] = Field(min_length=1, max_length=30)


class ExtractTopicsRequest(BaseModel):
    """Body for `POST /curriculum/chapters/{id}/topics/extract` — kick
    off LLM topic extraction. Defaults to the idempotent "skip if topics
    exist" mode; pass `overwrite=True` to replace."""

    overwrite: bool = False


class LearningOutcomeItem(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=2, max_length=2000)
    bloom_level: Literal[
        "remember", "understand", "apply", "analyze", "evaluate", "create"
    ]
    # Optional human-readable topic name (case-insensitive match against
    # the chapter's topics). Resolves to topic_id server-side.
    topic_name: str | None = None


class BulkOutcomesRequest(BaseModel):
    """Body for `POST /curriculum/chapters/{id}/learning-outcomes`."""

    outcomes: list[LearningOutcomeItem] = Field(min_length=1, max_length=50)


class ExtractedPdfTextResponse(BaseModel):
    """Response shape for `POST /curriculum/extract-pdf-text`."""

    text: str
    page_count: int


class TopicsResponse(BaseModel):
    """Response shape for the topic ingestion endpoints."""

    topics: list[TopicRead]


class LearningOutcomesResponse(BaseModel):
    """Response shape for the outcomes ingestion endpoint."""

    outcomes: list[LearningOutcomeRead]


class TopicTextExtractionError(BaseModel):
    topic_id: int
    topic_name: str
    error: str


class TopicTextExtractionResponse(BaseModel):
    """Response for `POST /curriculum/chapters/{id}/topics/extract-texts`.

    Reports per-topic outcome so the UI can show "wrote 5, skipped 2,
    1 errored" — useful because slicing is slow (one LLM call per topic)
    and partial success is the common case on a flaky API.
    """

    topics: list[TopicRead]
    written: int
    skipped: int
    errored: int
    errors: list[TopicTextExtractionError] = []


class BootstrapJobInfoOut(BaseModel):
    """One scheduled (or reused) generation job in a bootstrap response."""

    id: int
    content_type: str
    status: str
    title: str


class BootstrapChapterResponse(BaseModel):
    """Response for `POST /curriculum/chapters/{id}/bootstrap-content`.

    Splits the work into three signals so the UI can write a clear
    summary toast: "Extracted N topics, queued M jobs, K were already
    cached and reused."
    """

    topics_extracted: int
    topic_texts_scheduled: bool
    jobs_scheduled: list[BootstrapJobInfoOut] = []
    jobs_reused: list[BootstrapJobInfoOut] = []
