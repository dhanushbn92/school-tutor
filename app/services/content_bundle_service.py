"""Service for ingesting a `ContentBundle` JSON into the database.

One public entrypoint: `ingest_bundle(db, bundle, *, created_by_id)`.

Behaviour summary:
  - Looks up the chapter via (board, class_level, subject, chapter_number)
    plus optional book_title. Fails with `ContentBundleError` if not found.
  - Optional `chapter_text` replaces `chapter.full_text`.
  - Topics and learning outcomes inserted idempotently (by name / code).
  - Questions inserted idempotently (by exact question text on the chapter).
  - chapter_summary / lesson_plan / worksheet / ppt / diagram / simulation:
    REPLACE any existing GeneratedContent row of that type. Artefact
    files (PDF/PPTX/SVG/HTML) are re-rendered where applicable.

The service is transactional — caller is expected to wrap in a session
and commit on success. Failures raise `ContentBundleError`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import (
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
from app.models.question import (
    Question,
    QuestionStatus,
)
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.schemas.content_bundle import ContentBundle
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key


class ContentBundleError(Exception):
    """Raised when a bundle can't be ingested (chapter not found, etc.)."""


@dataclass
class IngestReport:
    """Returned by `ingest_bundle` — quick at-a-glance summary of what
    actually changed in the database. Useful for CLI output and for
    showing the user 'here's what your upload did'."""

    chapter_id: int
    chapter_text_replaced: bool = False
    topics_inserted: int = 0
    topics_skipped: int = 0
    outcomes_inserted: int = 0
    outcomes_skipped: int = 0
    questions_inserted: int = 0
    questions_skipped: int = 0
    blobs_replaced: list[str] = field(default_factory=list)
    blobs_inserted: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "chapter_id": self.chapter_id,
            "chapter_text_replaced": self.chapter_text_replaced,
            "topics": {"inserted": self.topics_inserted, "skipped": self.topics_skipped},
            "outcomes": {"inserted": self.outcomes_inserted, "skipped": self.outcomes_skipped},
            "questions": {"inserted": self.questions_inserted, "skipped": self.questions_skipped},
            "content_blobs": {
                "replaced": self.blobs_replaced,
                "inserted": self.blobs_inserted,
            },
        }


def ingest_bundle(
    db: Session,
    bundle: ContentBundle,
    *,
    created_by_id: int,
) -> IngestReport:
    """Ingest a validated `ContentBundle` into the database.

    Caller is responsible for `db.commit()` on success.
    """
    chapter = _resolve_chapter(db, bundle)
    report = IngestReport(chapter_id=chapter.id)

    # 1. chapter_text (optional REPLACE)
    if bundle.chapter_text is not None:
        chapter.full_text = bundle.chapter_text
        chapter.content_hash = hashlib.sha256(
            bundle.chapter_text.encode("utf-8")
        ).hexdigest()
        chapter.imported_at = datetime.now(timezone.utc)
        db.flush()
        report.chapter_text_replaced = True

    # 2. topics (idempotent INSERT, build name -> id map for outcome wiring)
    topic_id_by_name = _insert_topics(db, chapter=chapter, bundle=bundle, report=report)

    # 3. learning outcomes (idempotent INSERT by code)
    _insert_outcomes(
        db,
        chapter=chapter,
        bundle=bundle,
        topic_id_by_name=topic_id_by_name,
        report=report,
    )

    # 4. content blobs (REPLACE existing row of each type)
    _ingest_content_blobs(db, chapter=chapter, bundle=bundle, created_by_id=created_by_id, report=report)

    # 5. questions (idempotent INSERT by text)
    _insert_questions(db, chapter=chapter, bundle=bundle, created_by_id=created_by_id, report=report)

    return report


# ---------- chapter lookup ---------------------------------------------------


def _resolve_chapter(db: Session, bundle: ContentBundle) -> Chapter:
    """Resolve a Chapter from whatever curriculum coordinates are provided.

    Only `subject` and `chapter_title` are required. Everything else
    (board, class_level, chapter_number, book_title) is a filter applied
    when supplied. We return the unique matching chapter, or raise a
    `ContentBundleError` that lists all candidates so the author can
    add a disambiguator.
    """
    coords = bundle.curriculum

    # 1. Build the candidate Subject set. Filters are applied only when
    #    the author supplied them.
    subject_q = select(Subject).where(
        Subject.name.ilike(coords.subject),
        Subject.language == coords.language,
    )
    if coords.board is not None:
        subject_q = subject_q.where(Subject.board == coords.board)
    if coords.class_level is not None:
        school_class = db.scalar(
            select(SchoolClass).where(SchoolClass.level == coords.class_level)
        )
        if school_class is None:
            raise ContentBundleError(
                f"No SchoolClass row for class_level={coords.class_level}. "
                "Either omit class_level (we'll search every class) or "
                "scaffold that class first."
            )
        subject_q = subject_q.where(Subject.class_id == school_class.id)

    subjects = db.scalars(subject_q).all()
    if not subjects:
        raise ContentBundleError(
            f"No subject named {coords.subject!r} found"
            + (f" for board={coords.board!r}" if coords.board else "")
            + (f", class {coords.class_level}" if coords.class_level else "")
            + f", language={coords.language!r}. Has the curriculum been scaffolded?"
        )

    # 2. For each candidate subject, find chapters matching the title /
    #    number. Collect every match across all candidate subjects.
    matches: list[tuple[Subject, Book, Chapter]] = []
    for subject in subjects:
        book_q = select(Book).where(Book.subject_id == subject.id)
        if coords.book_title is not None:
            book_q = book_q.where(Book.title == coords.book_title)
        for book in db.scalars(book_q).all():
            chapter_q = select(Chapter).where(Chapter.book_id == book.id)
            if coords.chapter_number is not None:
                chapter_q = chapter_q.where(Chapter.chapter_number == coords.chapter_number)
            else:
                chapter_q = chapter_q.where(Chapter.title.ilike(coords.chapter_title))
            for chapter in db.scalars(chapter_q).all():
                matches.append((subject, book, chapter))

    if not matches:
        raise ContentBundleError(
            f"No chapter matched: subject={coords.subject!r}, chapter_title={coords.chapter_title!r}"
            + (f", chapter_number={coords.chapter_number}" if coords.chapter_number else "")
            + (f", board={coords.board!r}" if coords.board else "")
            + (f", class={coords.class_level}" if coords.class_level else "")
            + ". Check the spelling, or scaffold the chapter first."
        )

    # 3. If the author gave `chapter_number`, sanity-check the title and
    #    refuse a mismatch (catches wrong-chapter uploads).
    if coords.chapter_number is not None:
        matches = [
            m for m in matches
            if m[2].title.strip().lower() == coords.chapter_title.strip().lower()
        ]
        if not matches:
            raise ContentBundleError(
                f"chapter_title mismatch: bundle says chapter "
                f"{coords.chapter_number} is {coords.chapter_title!r}, "
                "but no chapter with that number has that title in the "
                "candidate subjects. Fix one of them."
            )

    # 4. Otherwise (no chapter_number) require an exact title match for
    #    each candidate to be considered.
    else:
        matches = [
            m for m in matches
            if m[2].title.strip().lower() == coords.chapter_title.strip().lower()
        ]
        if not matches:
            raise ContentBundleError(
                f"No chapter titled {coords.chapter_title!r} found under "
                f"subject {coords.subject!r}. Check the spelling."
            )

    # 5. Single match: ship it.
    if len(matches) == 1:
        return matches[0][2]

    # 6. Multiple matches: list them so the author can add a disambiguator.
    def _label(subject: Subject, book: Book, chapter: Chapter) -> str:
        return (
            f"board={subject.board}, class={subject.school_class.level}, "
            f"subject={subject.name!r}, book={book.title!r}, "
            f"chapter_number={chapter.chapter_number}"
        )

    candidates = "\n  - " + "\n  - ".join(_label(s, b, c) for s, b, c in matches)
    raise ContentBundleError(
        f"Ambiguous: {len(matches)} chapters match your coordinates. "
        f"Add `board`, `class_level`, or `chapter_number` to your bundle's "
        f"`curriculum` block to pick one. Candidates:{candidates}"
    )


# ---------- topics + outcomes -----------------------------------------------


def _insert_topics(
    db: Session,
    *,
    chapter: Chapter,
    bundle: ContentBundle,
    report: IngestReport,
) -> dict[str, int]:
    existing = {
        t.name: t.id
        for t in db.scalars(select(Topic).where(Topic.chapter_id == chapter.id)).all()
    }
    name_to_id: dict[str, int] = dict(existing)
    for spec in bundle.topics:
        if spec.name in existing:
            report.topics_skipped += 1
            continue
        topic = Topic(
            chapter_id=chapter.id,
            name=spec.name,
            description=spec.description,
            full_text=spec.full_text,
        )
        db.add(topic)
        db.flush()
        name_to_id[spec.name] = topic.id
        report.topics_inserted += 1
    return name_to_id


def _insert_outcomes(
    db: Session,
    *,
    chapter: Chapter,
    bundle: ContentBundle,
    topic_id_by_name: dict[str, int],
    report: IngestReport,
) -> None:
    existing_codes = {
        r.code
        for r in db.scalars(
            select(LearningOutcome).where(LearningOutcome.chapter_id == chapter.id)
        ).all()
    }
    for o in bundle.learning_outcomes:
        if o.code in existing_codes:
            report.outcomes_skipped += 1
            continue
        topic_id = topic_id_by_name.get(o.topic_name) if o.topic_name else None
        db.add(
            LearningOutcome(
                chapter_id=chapter.id,
                topic_id=topic_id,
                code=o.code,
                description=o.description,
                bloom_level=o.bloom,
            )
        )
        report.outcomes_inserted += 1


# ---------- questions --------------------------------------------------------


def _insert_questions(
    db: Session,
    *,
    chapter: Chapter,
    bundle: ContentBundle,
    created_by_id: int,
    report: IngestReport,
) -> None:
    outcome_map = {
        r.code: r.id
        for r in db.scalars(
            select(LearningOutcome).where(LearningOutcome.chapter_id == chapter.id)
        ).all()
    }
    existing_texts = {
        r.text
        for r in db.scalars(
            select(Question).where(Question.chapter_id == chapter.id)
        ).all()
    }
    for q in bundle.questions:
        if q.question in existing_texts:
            report.questions_skipped += 1
            continue
        outcome_id = outcome_map.get(q.outcome_code) if q.outcome_code else None
        options_payload = {"choices": list(q.options)} if q.options else None
        db.add(
            Question(
                chapter_id=chapter.id,
                topic_id=None,
                outcome_id=outcome_id,
                outcome_code=q.outcome_code,
                type=q.type,
                difficulty=q.difficulty,
                status=QuestionStatus.APPROVED,
                cognitive_level=q.cognitive_level,
                text=q.question,
                options=options_payload,
                correct_answer=q.answer,
                explanation=q.explanation,
                marks=q.marks,
                created_by_id=created_by_id,
            )
        )
        report.questions_inserted += 1


# ---------- content blobs (summary / lesson plan / worksheet / ppt / etc.) --


_BLOB_SPECS: list[tuple[str, GeneratedContentType, type, object, str | None]] = [
    # (bundle field, content_type, schema, renderer, extension)
    # renderer is either a callable or one of: 'worksheet', None.
    ("chapter_summary", GeneratedContentType.CHAPTER_SUMMARY, ChapterSummaryOutput, None, None),
    ("lesson_plan", GeneratedContentType.LESSON_PLAN, LessonPlanOutput, render_lesson_plan_docx, "docx"),
    ("worksheet", GeneratedContentType.WORKSHEET, WorksheetOutput, "worksheet", "pdf"),
    ("ppt", GeneratedContentType.PPT, PPTOutlineOutput, render_ppt_outline, "pptx"),
    ("diagram", GeneratedContentType.DIAGRAM, DiagramOutput, render_concept_map_svg, "svg"),
    ("simulation", GeneratedContentType.SIMULATION, SimulationOutput, render_simulation_html, "html"),
]


def _ingest_content_blobs(
    db: Session,
    *,
    chapter: Chapter,
    bundle: ContentBundle,
    created_by_id: int,
    report: IngestReport,
) -> None:
    subject = chapter.book.subject
    school_class = subject.school_class
    subject_name = subject.name
    store = get_artifact_store()
    now = datetime.now(timezone.utc)

    llm_provider = bundle.meta.source if bundle.meta and bundle.meta.source else "content-bundle-upload"
    llm_model = bundle.meta.author if bundle.meta and bundle.meta.author else "bundle-v1.0"

    for field_name, content_type, schema, renderer, extension in _BLOB_SPECS:
        payload = getattr(bundle, field_name)
        if payload is None:
            continue
        # Re-validate against the LLM-output schema (defensive — the bundle
        # already validated, but the typed payload is an instance, not raw
        # JSON, so we just re-dump).
        validated = payload
        output_json = validated.model_dump(mode="json")

        # Drop any existing row of this type.
        existing = db.scalars(
            select(GeneratedContent)
            .where(GeneratedContent.chapter_id == chapter.id)
            .where(GeneratedContent.content_type == content_type)
        ).all()
        replaced = bool(existing)
        for old in existing:
            db.delete(old)
        if existing:
            db.flush()  # Ensure DELETE hits DB before the INSERT below.

        cache_key = build_generation_cache_key(
            content_type=content_type.value,
            academic_year=bundle.curriculum.academic_year,
            class_level=school_class.level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=None,
            prompt=None,
            options=None,
        )
        row = GeneratedContent(
            content_type=content_type,
            status=GeneratedContentStatus.APPROVED,
            cache_key=cache_key,
            academic_year=bundle.curriculum.academic_year,
            class_level=school_class.level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=None,
            title=(
                f"{content_type.value.replace('_', ' ').title()} - "
                f"Class {school_class.level} - {subject_name} - "
                f"Chapter {chapter.chapter_number}: {chapter.title}"
            ),
            source_context=(chapter.full_text or "")[:4000],
            output_json=output_json,
            request_options=None,
            llm_provider=llm_provider,
            llm_model=llm_model,
            created_by_id=created_by_id,
            published_at=now,
            published_by_id=created_by_id,
        )
        db.add(row)
        db.flush()

        # Render any artefact file.
        if renderer is None:
            pass
        elif renderer == "worksheet":
            pdf_bytes = render_worksheet_pdf(
                validated,
                class_level=school_class.level,
                subject=subject_name,
                chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
                include_answer_key=True,
            )
            row.artifact_url = store.save(content_id=row.id, extension="pdf", data=pdf_bytes)
        else:
            data = renderer(validated)
            row.artifact_url = store.save(content_id=row.id, extension=extension, data=data)

        if replaced:
            report.blobs_replaced.append(content_type.value)
        else:
            report.blobs_inserted.append(content_type.value)
