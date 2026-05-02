"""Curriculum ingestion service — lifts the chapter onboarding flow that
previously lived only in `scripts/` into reusable functions the API can
call from a platform-admin UI.

Covers:
  - PDF text extraction (wraps `app.ingestion.ncert_http.extract_pdf_text`)
  - Chapter creation under an existing book (manual full_text or PDF
    extraction)
  - Bulk import / replace of topics on a chapter
  - AI-driven topic extraction from chapter text (mirrors
    `scripts.extract_topics`)
  - Bulk import / replace of learning outcomes on a chapter

Out of scope here (live in scripts for now): topic-text slicing,
manifest-driven bulk import, LLM outcome extraction. Those are bigger
operations that don't fit a single web request well — they stay as
admin-only scripts.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import BackgroundTasks
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.ingestion.ncert_http import extract_pdf_text as _extract_pdf_text
from app.llm import LLMError, get_llm_provider
from app.llm.prompts.topic_extraction import (
    TOPIC_EXTRACTION_SYSTEM_PROMPT,
    build_topic_extraction_user_prompt,
)
from app.llm.prompts.topic_text import (
    TOPIC_TEXT_SYSTEM_PROMPT,
    build_topic_text_user_prompt,
)
from app.llm.schemas.topic_extraction import TopicExtractionOutput
from app.llm.schemas.topic_text import TopicTextOutput
from app.models.curriculum import (
    AcademicYear,
    BloomLevel,
    Book,
    Chapter,
    LearningOutcome,
    SchoolClass,
    Subject,
    Topic,
)
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.schemas.generation import GenerateContentRequest
from app.services.generation_service import create_or_reuse_generated_content
from app.workers.generate import run_generation_job


log = logging.getLogger(__name__)


# Cap chapter text sent to the LLM for topic extraction. Same threshold
# the standalone script uses — keeps us under provider TPM limits.
_MAX_CHAPTER_TEXT_CHARS = 25_000


class IngestError(Exception):
    """Domain error raised when an ingestion step fails for a known reason
    (missing book, validation problem, LLM refusal). Routes catch this and
    map to HTTP 400/404."""


# --------------------------------------------------------------------------
# PDF helpers
# --------------------------------------------------------------------------


def extract_pdf_text_only(data: bytes) -> tuple[str, int]:
    """Pull the full text + page count out of a PDF. Pure function — does
    not write anything. The route uses this when the admin uploads a PDF
    and wants to preview / edit the extracted text before saving the
    Chapter row."""
    text, page_count, _ = _extract_pdf_text(data)
    return text, page_count


# --------------------------------------------------------------------------
# Chapter creation
# --------------------------------------------------------------------------


def create_chapter(
    db: Session,
    *,
    book_id: int,
    chapter_number: int,
    title: str,
    full_text: str,
    source_url: str | None = None,
    page_count: int | None = None,
) -> Chapter:
    """Create a new Chapter row under the given book. Raises IngestError
    on missing book or duplicate (book_id, chapter_number).

    Title and full_text are normalised (stripped); empty titles are
    rejected so we don't end up with blank rows in the catalogue.
    """
    book = db.get(Book, book_id)
    if book is None:
        raise IngestError(f"Book {book_id} not found")

    title = title.strip()
    if not title:
        raise IngestError("title is required")
    if not full_text.strip():
        raise IngestError("full_text is required (paste it or upload a PDF first)")

    existing = db.scalar(
        select(Chapter).where(
            Chapter.book_id == book_id,
            Chapter.chapter_number == chapter_number,
        )
    )
    if existing is not None:
        raise IngestError(
            f"Chapter {chapter_number} already exists in this book "
            f"(id={existing.id}). Pick a different number or delete the "
            f"existing chapter first."
        )

    chapter = Chapter(
        book_id=book_id,
        chapter_number=chapter_number,
        title=title,
        full_text=full_text,
        source_url=source_url,
        page_count=page_count,
        imported_at=datetime.now(timezone.utc),
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


# --------------------------------------------------------------------------
# Topics
# --------------------------------------------------------------------------


def bulk_replace_topics(
    db: Session,
    *,
    chapter_id: int,
    topics: list[dict[str, Any]],
) -> list[Topic]:
    """Replace the chapter's topic list with the given items. Items are
    `{name: str, description?: str}`. Returns the inserted Topic rows.

    "Replace" means: existing Topic rows on the chapter are deleted
    first. Use this when the admin pastes a curated topic list and
    wants the chapter to reflect exactly that. There's no "merge" mode
    here — that's a niche we'll add only if asked.
    """
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise IngestError(f"Chapter {chapter_id} not found")

    # Validate inputs first (don't delete existing rows if the new list is bad).
    cleaned: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for raw in topics:
        name = str(raw.get("name", "")).strip()
        if not name:
            raise IngestError("Every topic needs a non-empty name")
        if name.lower() in seen:
            raise IngestError(f"Duplicate topic name: {name!r}")
        seen.add(name.lower())
        desc = raw.get("description")
        cleaned.append((name, str(desc).strip() if desc else None))

    # Delete existing topics, then insert the new set.
    db.query(Topic).filter(Topic.chapter_id == chapter_id).delete(
        synchronize_session=False
    )
    db.flush()

    rows = [
        Topic(chapter_id=chapter_id, name=name, description=desc)
        for name, desc in cleaned
    ]
    db.add_all(rows)
    db.commit()
    for t in rows:
        db.refresh(t)
    return rows


def extract_topics_with_ai(
    db: Session,
    *,
    chapter_id: int,
    overwrite: bool = False,
) -> list[Topic]:
    """Run the topic-extraction LLM prompt against the chapter's full text
    and upsert Topic rows. Mirrors the logic in `scripts.extract_topics`
    but as a synchronous service call (the LLM is fast enough for a
    single chapter that we don't need a background queue).

    Returns the resulting Topic rows (existing ones if `overwrite=False`
    and topics already exist; freshly created otherwise).
    """
    # Eager-load book → subject → class so the prompt builder gets the
    # full curriculum context (class level, subject name, chapter
    # number). Without these, the LLM doesn't know whether "Number
    # Systems" is being taught to Class 6 (counting numbers) vs Class 10
    # (rationals + irrationals + reals) and may produce off-grade topics.
    chapter = db.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(joinedload(Chapter.book).joinedload(Book.subject))
    )
    if chapter is None:
        raise IngestError(f"Chapter {chapter_id} not found")

    text = chapter.full_text or ""
    if not text.strip():
        raise IngestError(
            "Chapter has no full_text. Add chapter text first (paste or "
            "upload a PDF) before extracting topics."
        )

    if chapter.book is None or chapter.book.subject is None:
        raise IngestError(
            "Chapter is missing its book/subject linkage — can't build "
            "the LLM context. Re-create the chapter under a valid book."
        )
    subject = chapter.book.subject
    school_class = db.get(SchoolClass, subject.class_id)
    if school_class is None:
        raise IngestError("Couldn't resolve class level for this subject")

    existing = db.scalars(
        select(Topic).where(Topic.chapter_id == chapter.id)
    ).all()
    if existing and not overwrite:
        # Idempotent default: if topics already exist, return them rather
        # than spending an LLM call.
        return list(existing)

    if len(text) > _MAX_CHAPTER_TEXT_CHARS:
        text = text[:_MAX_CHAPTER_TEXT_CHARS] + "\n…[truncated for token budget]"

    user_prompt = build_topic_extraction_user_prompt(
        class_level=school_class.level,
        subject_name=subject.name,
        chapter_number=chapter.chapter_number,
        chapter_title=chapter.title,
        chapter_text=text,
    )
    provider = get_llm_provider()
    try:
        result = provider.generate_structured(
            system=TOPIC_EXTRACTION_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=TopicExtractionOutput,
        )
    except LLMError as e:
        raise IngestError(f"LLM topic extraction failed: {e}") from e

    # If overwrite was requested, clear existing rows.
    if existing:
        db.query(Topic).filter(Topic.chapter_id == chapter_id).delete(
            synchronize_session=False
        )
        db.flush()

    rows = [
        Topic(
            chapter_id=chapter.id,
            name=t.name.strip(),
            description=t.description.strip(),
        )
        for t in result.topics
    ]
    db.add_all(rows)
    db.commit()
    for t in rows:
        db.refresh(t)
    return rows


# --------------------------------------------------------------------------
# Learning outcomes
# --------------------------------------------------------------------------


def bulk_replace_learning_outcomes(
    db: Session,
    *,
    chapter_id: int,
    outcomes: list[dict[str, Any]],
) -> list[LearningOutcome]:
    """Replace the chapter's learning outcomes. Items are
    `{code, description, bloom_level, topic_name?}`. The optional
    `topic_name` is matched (case-insensitive) against existing Topic
    rows on this chapter; unmatched names mean topic_id stays null.
    """
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise IngestError(f"Chapter {chapter_id} not found")

    # Build a lookup table for topic-name → id so we don't query in the loop.
    topic_lookup: dict[str, int] = {
        (t.name or "").strip().lower(): t.id
        for t in db.scalars(
            select(Topic).where(Topic.chapter_id == chapter_id)
        ).all()
    }

    cleaned: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    valid_blooms = {b.value for b in BloomLevel}
    for raw in outcomes:
        code = str(raw.get("code", "")).strip()
        if not code:
            raise IngestError("Every outcome needs a non-empty code")
        if code in seen_codes:
            raise IngestError(f"Duplicate outcome code: {code!r}")
        seen_codes.add(code)
        description = str(raw.get("description", "")).strip()
        if not description:
            raise IngestError(f"Outcome {code} needs a description")
        bloom = str(raw.get("bloom_level", "")).strip().lower()
        if bloom not in valid_blooms:
            raise IngestError(
                f"Outcome {code} has unknown bloom_level {bloom!r}. "
                f"Use one of: {sorted(valid_blooms)}"
            )
        topic_name = str(raw.get("topic_name", "")).strip().lower() or None
        topic_id = topic_lookup.get(topic_name) if topic_name else None
        cleaned.append(
            dict(
                code=code,
                description=description,
                bloom_level=BloomLevel(bloom),
                topic_id=topic_id,
            )
        )

    db.query(LearningOutcome).filter(
        LearningOutcome.chapter_id == chapter_id
    ).delete(synchronize_session=False)
    db.flush()

    rows = [
        LearningOutcome(chapter_id=chapter_id, **payload)
        for payload in cleaned
    ]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


# --------------------------------------------------------------------------
# Topic text slicing (per-topic verbatim chapter slice for AI tutor RAG)
# --------------------------------------------------------------------------


class TopicTextExtractionResult:
    """Plain dataclass-style holder for the result of a slicing run.
    Returned to the route, which serialises it for the client. Tracks
    counts so the UI can show "wrote 5, skipped 2 already-populated, 1
    error" instead of a binary success / fail.
    """

    def __init__(
        self,
        *,
        topics: list[Topic],
        written: int,
        skipped: int,
        errored: int,
        errors: list[dict[str, Any]],
    ):
        self.topics = topics
        self.written = written
        self.skipped = skipped
        self.errored = errored
        self.errors = errors


def extract_topic_texts_for_chapter(
    db: Session,
    *,
    chapter_id: int,
    overwrite: bool = False,
) -> TopicTextExtractionResult:
    """For each Topic on the chapter, ask the LLM to slice the chapter's
    verbatim text down to the topic-specific portion and store it on
    `Topic.full_text`. Mirrors `scripts.extract_topic_texts` but as a
    single synchronous service call.

    Idempotent: topics whose `full_text` is already populated are
    skipped unless `overwrite=True`. Each topic commits independently so
    a partial failure doesn't lose previously-written slices.

    Returns counts + the refreshed topic rows. Raises IngestError if the
    chapter is missing, has no `full_text`, or has no topics yet.
    """
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise IngestError(f"Chapter {chapter_id} not found")

    text = chapter.full_text or ""
    if not text.strip():
        raise IngestError(
            "Chapter has no full_text. Add chapter text first before slicing topic texts."
        )

    topics = list(
        db.scalars(
            select(Topic)
            .where(Topic.chapter_id == chapter_id)
            .order_by(Topic.id)
        )
    )
    if not topics:
        raise IngestError(
            "Chapter has no topics yet. Add topics first (manual or AI) before slicing."
        )

    provider = get_llm_provider()
    written = 0
    skipped = 0
    errored = 0
    errors: list[dict[str, Any]] = []

    # Pacing — Groq's free tier caps at ~12k TPM. Each slicing call
    # spends ~6-8k tokens (chapter text + system + topic + response),
    # so back-to-back calls overflow the per-minute budget. We sleep
    # between calls to spread usage over time. The first call doesn't
    # need a wait (no prior usage); subsequent calls do.
    _PACING_SECONDS_BETWEEN_CALLS = 6
    # When the provider replies with a rate-limit error, this is the
    # one-shot back-off we apply before retrying. Empirically a 35-40s
    # wait clears the per-minute window and the second attempt usually
    # succeeds.
    _RATE_LIMIT_BACKOFF_SECONDS = 40

    for i, topic in enumerate(topics):
        if topic.full_text and not overwrite:
            skipped += 1
            continue

        if i > 0:
            time.sleep(_PACING_SECONDS_BETWEEN_CALLS)

        user_prompt = build_topic_text_user_prompt(
            topic_name=topic.name,
            topic_description=topic.description,
            chapter_text=text,
        )

        def _call_provider() -> TopicTextOutput:
            return provider.generate_structured(
                system=TOPIC_TEXT_SYSTEM_PROMPT,
                user=user_prompt,
                response_model=TopicTextOutput,
                temperature=0.1,
            )

        result: TopicTextOutput | None = None
        try:
            result = _call_provider()
        except LLMError as exc:
            # Detect a rate-limit signal in the message and retry once
            # after a back-off. We can't introspect headers here (the
            # provider abstraction hides the HTTP layer), so we sniff
            # the message string for the well-known fragments.
            msg = str(exc).lower()
            is_rate_limit = (
                "rate_limit_exceeded" in msg
                or "tokens per minute" in msg
                or "tpm" in msg
                or "request too large" in msg
                or "error code: 413" in msg
                or "error code: 429" in msg
            )
            if is_rate_limit:
                log.info(
                    "topic_text rate-limited on topic %s; backing off %ss "
                    "and retrying once",
                    topic.id,
                    _RATE_LIMIT_BACKOFF_SECONDS,
                )
                time.sleep(_RATE_LIMIT_BACKOFF_SECONDS)
                try:
                    result = _call_provider()
                except LLMError as retry_exc:
                    errored += 1
                    errors.append(
                        {
                            "topic_id": topic.id,
                            "topic_name": topic.name,
                            "error": (
                                "Rate-limited even after back-off. "
                                "Free Groq tier caps TPM — try again "
                                "in a minute, or upgrade the LLM tier. "
                                f"Detail: {retry_exc}"
                            ),
                        }
                    )
                    log.warning(
                        "topic_text retry failed for topic %s '%s': %s",
                        topic.id,
                        topic.name,
                        retry_exc,
                    )
                    continue
            else:
                errored += 1
                errors.append(
                    {
                        "topic_id": topic.id,
                        "topic_name": topic.name,
                        "error": str(exc),
                    }
                )
                log.warning(
                    "topic_text extraction failed for topic %s '%s': %s",
                    topic.id,
                    topic.name,
                    exc,
                )
                continue

        # Defensive — the only way result is None at this point would be
        # a logic bug above; we'd rather surface that than silently
        # write empty text to the topic.
        if result is None:
            errored += 1
            errors.append(
                {
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "error": "Internal: provider returned no result",
                }
            )
            continue

        topic.full_text = (result.text or "").strip()
        # Commit per topic so a later failure can't roll back earlier
        # successful slices. The user's wait time is the LLM cost; we
        # don't want to also lose data on a network blip.
        db.commit()
        db.refresh(topic)
        written += 1

    return TopicTextExtractionResult(
        topics=topics,
        written=written,
        skipped=skipped,
        errored=errored,
        errors=errors,
    )


# --------------------------------------------------------------------------
# One-click chapter bootstrap
#
# Admin uploads a chapter (text or PDF) → presses one button → backend
# does everything else: extract topics, slice topic texts, fan out
# generation jobs for every supported content type.
#
# Architecture:
#   - Topic extraction runs synchronously (single LLM call, ~5s) so the
#     admin gets immediate feedback that something happened.
#   - Topic-text slicing is slow (one call per topic, 30-90s for 6-8
#     topics) — we schedule it as a background task that owns its own DB
#     session.
#   - Each content-type generation creates a GeneratedContent row in
#     PENDING status, then schedules `run_generation_job` as a background
#     task. The admin tracks progress in the Content library.
#
# Why the worker subset: bootstrap can only run content types whose
# worker is implemented today (worksheet, lesson_plan, ppt, diagram,
# simulation, chapter_summary). classroom_activity, flow_diagram,
# half_yearly_exam, resource_list aren't wired in the worker; scheduling
# them would just produce FAILED rows. Quiz is excluded because it
# generates child Question rows that expect a reviewer step.
# --------------------------------------------------------------------------


# Content types we kick off as part of the bootstrap. Order matters only
# for response readability — they all run concurrently as background
# tasks. Simulation defaults its template to "auto" so the LLM picks a
# fitting visual model for the chapter.
_BOOTSTRAP_CONTENT_TYPES: list[
    tuple[GeneratedContentType, dict[str, Any]]
] = [
    (GeneratedContentType.CHAPTER_SUMMARY, {}),
    (GeneratedContentType.LESSON_PLAN, {}),
    (GeneratedContentType.WORKSHEET, {}),
    (GeneratedContentType.PPT, {}),
    (GeneratedContentType.DIAGRAM, {}),
    (GeneratedContentType.SIMULATION, {"template": "auto"}),
]


class BootstrapJobInfo:
    """Per-row info reported back to the UI so it can link straight into
    the Content library to monitor each job's status."""

    def __init__(
        self,
        *,
        id: int,
        content_type: GeneratedContentType,
        status: GeneratedContentStatus,
        title: str,
    ):
        self.id = id
        self.content_type = content_type
        self.status = status
        self.title = title


class BootstrapResult:
    """Returned by `bootstrap_chapter_content`. Counts are split so the
    UI can show "extracted N topics, scheduled M jobs, skipped K cached
    rows" — the cached path matters because if the admin reruns
    bootstrap, existing rows are reused (cache_key match) instead of
    duplicated."""

    def __init__(
        self,
        *,
        topics_extracted: int,
        topic_texts_scheduled: bool,
        jobs_scheduled: list[BootstrapJobInfo],
        jobs_reused: list[BootstrapJobInfo],
    ):
        self.topics_extracted = topics_extracted
        self.topic_texts_scheduled = topic_texts_scheduled
        self.jobs_scheduled = jobs_scheduled
        self.jobs_reused = jobs_reused


def _topic_text_slicing_background(chapter_id: int) -> None:
    """Background-task wrapper that owns its own DB session. FastAPI
    BackgroundTasks runs after the response is sent, so we can't reuse
    the request's session — it's already closed."""
    db = SessionLocal()
    try:
        try:
            extract_topic_texts_for_chapter(db, chapter_id=chapter_id, overwrite=False)
        except IngestError as exc:
            log.warning("bootstrap topic_text slicing failed: %s", exc)
        except Exception:
            log.exception("bootstrap topic_text slicing crashed")
    finally:
        db.close()


def bootstrap_chapter_content(
    db: Session,
    *,
    chapter_id: int,
    creator_user_id: int,
    background_tasks: BackgroundTasks,
) -> BootstrapResult:
    """Kick off the full chapter content pipeline. Topic extraction runs
    inline; topic-text slicing and per-type content generation are
    scheduled as background tasks. Returns immediately with a summary
    of what was started.

    Idempotent: existing topics + existing GeneratedContent rows
    (matched by cache_key) are reused, not duplicated. To regenerate,
    use the AI tab's force-regenerate option per content type.
    """
    chapter = db.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(joinedload(Chapter.book).joinedload(Book.subject))
    )
    if chapter is None:
        raise IngestError(f"Chapter {chapter_id} not found")
    if not (chapter.full_text or "").strip():
        raise IngestError(
            "Chapter has no full_text. Add chapter text first (paste or "
            "upload a PDF) before bootstrapping."
        )
    if chapter.book is None or chapter.book.subject is None:
        raise IngestError(
            "Chapter is missing its book or subject linkage — bootstrap "
            "needs the curriculum chain to schedule generation jobs."
        )

    subject: Subject = chapter.book.subject
    # Class level lives on the SchoolClass linked from Subject. Single
    # fetch by FK.
    school_class = db.get(SchoolClass, subject.class_id)
    if school_class is None:
        raise IngestError("Couldn't resolve class level for this subject")
    class_level = school_class.level

    # Pick the academic year — same fallback chain the upload flow uses.
    year = db.scalar(select(AcademicYear).where(AcademicYear.is_current.is_(True)))
    if year is None:
        year = db.scalar(select(AcademicYear).order_by(AcademicYear.id.desc()))
    if year is None:
        raise IngestError("No academic year configured on the platform.")
    academic_year = year.name

    # 1. Topics — run synchronously so the admin sees them right away.
    topics_before = db.scalars(
        select(Topic).where(Topic.chapter_id == chapter.id)
    ).all()
    if not topics_before:
        topics = extract_topics_with_ai(db, chapter_id=chapter.id, overwrite=False)
    else:
        topics = list(topics_before)

    # 2. Topic-text slicing — slow, schedule as background task.
    background_tasks.add_task(_topic_text_slicing_background, chapter.id)

    # 3. For each supported content type, create / reuse the row and
    # schedule a worker job if the row is fresh (PENDING).
    scheduled: list[BootstrapJobInfo] = []
    reused: list[BootstrapJobInfo] = []
    for content_type, options in _BOOTSTRAP_CONTENT_TYPES:
        request = GenerateContentRequest(
            content_type=content_type,
            academic_year=academic_year,
            class_level=class_level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            options=options,
            force_regenerate=False,
        )
        row = create_or_reuse_generated_content(
            db, request, creator_user_id=creator_user_id
        )
        info = BootstrapJobInfo(
            id=row.id,
            content_type=row.content_type,
            status=row.status,
            title=row.title,
        )
        if row.status == GeneratedContentStatus.PENDING:
            background_tasks.add_task(run_generation_job, row.id)
            scheduled.append(info)
        else:
            # Cache hit — row already exists from a prior bootstrap or
            # explicit generation. Don't re-queue it.
            reused.append(info)

    return BootstrapResult(
        topics_extracted=len(topics),
        topic_texts_scheduled=True,
        jobs_scheduled=scheduled,
        jobs_reused=reused,
    )
