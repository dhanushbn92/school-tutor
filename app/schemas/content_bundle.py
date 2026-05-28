"""JSON-bundle format for uploading a chapter's content into the platform.

Authors prepare ONE JSON file per chapter with curriculum coordinates
(board, class, subject, chapter) plus any subset of content blocks
(chapter text, topics, learning outcomes, chapter summary, lesson plan,
worksheet, ppt, diagram, simulation, questions). The ingester loads
whatever is present — nothing besides the curriculum coordinates is
mandatory.

The schema deliberately reuses the existing LLM-output schemas
(`ChapterSummaryOutput`, `LessonPlanOutput`, etc.) so a bundle is
exactly the union of those blobs that the SPA already understands. No
new shapes to teach the frontend.

See `scripts/content_bundle_examples/` for full + minimal worked
examples and the authoring README.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.boards import VALID_BOARDS
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import BloomLevel
from app.models.question import QuestionDifficulty, QuestionType


# ---------- curriculum coordinates (MANDATORY) ------------------------------


class CurriculumCoordinates(BaseModel):
    """Identifiers that tell the ingester WHERE the content belongs.

    Only `subject` and `chapter_title` are mandatory. The other fields
    are disambiguators — provide them when the (subject, chapter_title)
    combination would otherwise be ambiguous (e.g. you have multiple
    boards / classes that share both a subject name and a chapter title).

    Lookup precedence in the resolver:
      1. Filter the Subject table by everything provided (board / class /
         language / subject name).
      2. Look up the Chapter by `chapter_number` if given, otherwise by
         `chapter_title` (case-insensitive).
      3. If exactly one Chapter row matches across all candidate
         Subjects, use it. Otherwise return an actionable error listing
         the candidate rows so the author can add a disambiguator.
    """

    subject: str = Field(
        min_length=2,
        max_length=120,
        description="Subject name as it exists in the curriculum (case-insensitive match).",
        examples=["Physics"],
    )
    chapter_title: str = Field(
        min_length=2,
        max_length=300,
        description="Chapter title to look up (case-insensitive match against the DB).",
        examples=["Motion in a Plane"],
    )

    # ----- optional disambiguators (omit unless ambiguity demands them) -----

    board: str | None = Field(
        default=None,
        description=(
            "Optional. Provide when the same subject + chapter exists "
            "across multiple boards. Must be one of: "
            + ", ".join(VALID_BOARDS)
        ),
        examples=["NIOS", "CBSE"],
    )
    class_level: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional. Class / grade level (1-12). Provide to disambiguate across classes.",
        examples=[12],
    )
    chapter_number: int | None = Field(
        default=None,
        ge=1,
        le=99,
        description=(
            "Optional. If provided, used as the primary lookup key within "
            "the resolved Subject + Book. chapter_title is then used only as a sanity check."
        ),
        examples=[4],
    )
    book_title: str | None = Field(
        default=None,
        description=(
            "Optional. If multiple books exist for the same (subject, class), "
            "supply this to disambiguate."
        ),
        examples=["NIOS Senior Secondary Physics"],
    )
    language: str = Field(
        default="en",
        max_length=20,
        description="ISO language tag for the subject row (default 'en').",
    )
    academic_year: str = Field(
        default="2026-27",
        max_length=20,
        description="Academic year tag for generated_content rows.",
    )

    @model_validator(mode="after")
    def _check_board(self) -> "CurriculumCoordinates":
        if self.board is not None and self.board not in VALID_BOARDS:
            raise ValueError(
                f"board, when provided, must be one of {list(VALID_BOARDS)}, got {self.board!r}"
            )
        return self


# ---------- topics and learning outcomes (OPTIONAL) -------------------------


class BundleTopic(BaseModel):
    """One topic under the chapter. Topics are inserted idempotently —
    a topic with the same name on the same chapter is left untouched
    (existing description / full_text wins)."""

    name: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=10, max_length=2000)
    full_text: str | None = Field(
        default=None,
        description=(
            "Verbatim-style slice of the chapter text covering only this "
            "topic. Used by the topic-scoped AI tutor. Omit if you don't "
            "want a per-topic slice."
        ),
    )


class BundleOutcome(BaseModel):
    """One learning outcome. Codes must be unique within the chapter.
    Bloom level uses the canonical 6-level scale; lowercase strings
    'remember' / 'understand' / 'apply' / 'analyze' / 'evaluate' /
    'create' (matching `BloomLevel`)."""

    code: str = Field(
        min_length=3,
        max_length=40,
        description="Outcome code, e.g. '12-NIOS-PHY-MIP-06'. Must be unique within the chapter.",
    )
    description: str = Field(min_length=10, max_length=1000)
    bloom: BloomLevel = Field(description="One of: remember, understand, apply, analyze, evaluate, create. Case-insensitive on input.")
    topic_name: str | None = Field(
        default=None,
        description=(
            "Optional. If set, must match an existing or newly-inserted "
            "topic.name in this bundle. Lets the outcome be filtered by topic in the SPA."
        ),
    )

    @field_validator("bloom", mode="before")
    @classmethod
    def _normalize_bloom(cls, v):
        # BloomLevel values are lowercase; existing authored JSONs often use
        # uppercase. Normalise so either case works.
        if isinstance(v, str):
            return v.lower()
        return v


# ---------- questions (OPTIONAL) --------------------------------------------


class BundleQuestion(BaseModel):
    """One question. Re-uses the same shape as the
    chapter-question loader (lib.py `load_questions_from_file`) so an
    existing chXX_questions.json file is a valid `questions: [...]` block.

    Idempotency: questions are deduped by exact `question` text within
    the chapter — re-running the loader is safe.
    """

    type: QuestionType
    question: str = Field(min_length=5, max_length=2000, description="The question text. For CASE_BASED questions, include the passage in the text itself.")
    options: list[str] | None = Field(
        default=None,
        description="For MCQ (exactly 4) or TRUE_FALSE (exactly 2, ['True','False']). Omit otherwise.",
    )
    answer: str = Field(min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=2000)
    marks: int = Field(default=1, ge=1, le=10)
    difficulty: QuestionDifficulty = Field(default=QuestionDifficulty.MEDIUM)
    cognitive_level: BloomLevel = Field(default=BloomLevel.UNDERSTAND)
    outcome_code: str | None = Field(
        default=None,
        description="Optional outcome code to link the question to. If the code doesn't resolve, the question is still inserted with outcome=None.",
    )

    @field_validator("cognitive_level", mode="before")
    @classmethod
    def _normalize_bloom(cls, v):
        # BloomLevel values are lowercase; existing authored JSONs use uppercase.
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("type", "difficulty", mode="before")
    @classmethod
    def _normalize_uppercase(cls, v):
        # QuestionType and QuestionDifficulty values are uppercase; tolerate
        # mixed case on input.
        if isinstance(v, str):
            return v.upper()
        return v

    @model_validator(mode="after")
    def _check_options(self) -> "BundleQuestion":
        if self.type == QuestionType.MCQ:
            if not self.options or len(self.options) != 4:
                raise ValueError("MCQ questions must have exactly 4 options.")
            if self.answer not in self.options:
                raise ValueError("MCQ answer must be one of the options.")
        elif self.type == QuestionType.TRUE_FALSE:
            if not self.options or {o.lower() for o in self.options} != {"true", "false"}:
                raise ValueError("TRUE_FALSE options must be ['True', 'False'].")
        return self


# ---------- the bundle itself -----------------------------------------------


class ContentBundleMeta(BaseModel):
    """Optional metadata for provenance / auditing — not used for routing."""

    source: str | None = Field(default=None, max_length=200, description="Where the content came from, e.g. 'NIOS Official', 'in-house'.")
    author: str | None = Field(default=None, max_length=200, description="Person or team who prepared this bundle.")
    notes: str | None = Field(default=None, max_length=2000)


class ContentBundle(BaseModel):
    """Top-level bundle. Only `curriculum` is mandatory; every other
    field is optional and only acted on when present.

    Replace-vs-append behaviour:
      - topics, learning_outcomes, questions: INSERTED idempotently. Existing
        rows with matching natural keys (topic.name, outcome.code, question.text)
        are left untouched.
      - chapter_text: REPLACES the chapter.full_text if provided (the
        chapter must exist).
      - chapter_summary, lesson_plan, worksheet, ppt, diagram, simulation:
        REPLACE any existing GeneratedContent row of that type for the
        chapter. (The artefact file — pdf/pptx/svg/html — is re-rendered.)
    """

    curriculum: CurriculumCoordinates

    meta: ContentBundleMeta | None = Field(
        default=None,
        description="Optional provenance metadata. Stored on each GeneratedContent row's llm_provider / llm_model fields when present.",
    )

    chapter_text: str | None = Field(
        default=None,
        description="If present, replaces chapter.full_text. Useful for the topic-scoped AI tutor.",
    )

    topics: list[BundleTopic] = Field(default_factory=list)
    learning_outcomes: list[BundleOutcome] = Field(default_factory=list)

    chapter_summary: ChapterSummaryOutput | None = None
    lesson_plan: LessonPlanOutput | None = None
    worksheet: WorksheetOutput | None = None
    ppt: PPTOutlineOutput | None = None
    diagram: DiagramOutput | None = None
    simulation: SimulationOutput | None = None

    questions: list[BundleQuestion] = Field(default_factory=list)

    schema_version: Literal["1.0"] = Field(
        default="1.0",
        description="Bundle schema version. Currently 1.0. Future schema-breaking changes will bump this.",
    )
