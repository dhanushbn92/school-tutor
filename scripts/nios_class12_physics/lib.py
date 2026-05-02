"""Shared loader helpers for NIOS Class 12 Physics chapters.

Per-chapter scripts (02_load_ch73.py, 03_load_ch74.py, ...) call into
this module to:
  - update chapter.full_text
  - insert topics + verbatim-style slices
  - insert learning outcomes
  - insert the question bank
  - insert + render the six content blobs

All inserts are idempotent (skip on existing key / unique constraint
match). Status for both questions and generated content is APPROVED
+ published_at set, so the content is visible to students/teachers
immediately rather than requiring a separate publish step.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import (
    BloomLevel,
    Chapter,
    LearningOutcome,
    Topic,
)
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
)
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key


# ----- constants -----------------------------------------------------------

SUBJECT_ID = 14  # NIOS Senior Secondary Physics
CLASS_LEVEL = 12
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14  # platform.team@anaadi.org

DATA_DIR = Path(__file__).parent / "data"


# ----- chapter / topics / outcomes ----------------------------------------


def update_chapter_full_text(db: Session, chapter_id: int, full_text: str) -> Chapter:
    """Replace chapter.full_text and its content_hash. Required before
    bootstrapping content (the worker errors on empty full_text)."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise SystemExit(f"Chapter {chapter_id} not found")
    chapter.full_text = full_text
    chapter.content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    chapter.imported_at = datetime.now(timezone.utc)
    db.flush()
    return chapter


def insert_topics(
    db: Session,
    *,
    chapter_id: int,
    full_text: str,
    topic_specs: list[dict],
) -> dict[str, int]:
    """Insert topics with verbatim-style full_text slices.

    Each topic_spec has:
        name, description, section_header, next_section_header

    Returns a name -> topic_id map.
    """
    existing = {
        t.name: t.id
        for t in db.scalars(
            select(Topic).where(Topic.chapter_id == chapter_id)
        ).all()
    }
    name_to_id: dict[str, int] = dict(existing)
    inserted = 0
    for spec in topic_specs:
        if spec["name"] in existing:
            continue
        slice_text = _slice(full_text, spec["section_header"], spec["next_section_header"])
        t = Topic(
            chapter_id=chapter_id,
            name=spec["name"],
            description=spec["description"],
            full_text=slice_text,
        )
        db.add(t)
        db.flush()
        name_to_id[spec["name"]] = t.id
        inserted += 1
    print(f"[ok] topics: inserted {inserted}, skipped {len(existing)} pre-existing")
    return name_to_id


def insert_outcomes(
    db: Session,
    *,
    chapter_id: int,
    outcome_specs: list[dict],
    topic_id_by_name: dict[str, int],
) -> None:
    """Insert learning outcomes. Each spec has:
        code, topic_name, bloom (BloomLevel enum), description.
    """
    existing = {
        r.code
        for r in db.scalars(
            select(LearningOutcome).where(LearningOutcome.chapter_id == chapter_id)
        ).all()
    }
    inserted = 0
    for o in outcome_specs:
        if o["code"] in existing:
            continue
        db.add(
            LearningOutcome(
                chapter_id=chapter_id,
                topic_id=topic_id_by_name.get(o["topic_name"]),
                code=o["code"],
                description=o["description"],
                bloom_level=o["bloom"],
            )
        )
        inserted += 1
    print(f"[ok] outcomes: inserted {inserted}, skipped {len(existing)} pre-existing")


# ----- questions ----------------------------------------------------------


def load_questions_from_file(
    db: Session,
    *,
    chapter_id: int,
    filename: str,
) -> None:
    """Insert questions from a JSON file. Idempotent on `text`."""
    data = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    questions = data["questions"]

    outcome_map = {
        r.code: r.id
        for r in db.scalars(
            select(LearningOutcome).where(LearningOutcome.chapter_id == chapter_id)
        ).all()
    }
    existing_texts = {
        r.text
        for r in db.scalars(
            select(Question).where(Question.chapter_id == chapter_id)
        ).all()
    }
    inserted = 0
    skipped = 0
    unresolved: set[str] = set()
    for q in questions:
        if q["question"] in existing_texts:
            skipped += 1
            continue
        outcome_code = q.get("outcome_code")
        outcome_id = outcome_map.get(outcome_code) if outcome_code else None
        if outcome_code and outcome_id is None:
            unresolved.add(outcome_code)

        options_payload = (
            {"choices": list(q["options"])} if q.get("options") else None
        )
        db.add(
            Question(
                chapter_id=chapter_id,
                topic_id=q.get("topic_id"),
                outcome_id=outcome_id,
                outcome_code=outcome_code,
                type=QuestionType(q["type"]),
                difficulty=QuestionDifficulty(q["difficulty"]),
                status=QuestionStatus.APPROVED,
                cognitive_level=BloomLevel(q["cognitive_level"].lower()),
                text=q["question"],
                options=options_payload,
                correct_answer=q["answer"],
                explanation=q.get("explanation"),
                marks=int(q.get("marks", 1)),
                created_by_id=CREATED_BY_ID,
            )
        )
        inserted += 1
    print(f"[ok] questions: inserted {inserted}, skipped {skipped} pre-existing")
    if unresolved:
        print(f"  WARNING: unresolved outcome_codes: {sorted(unresolved)}")


# ----- content blobs ------------------------------------------------------


def _content_blobs_for(prefix: str) -> list[tuple[str, GeneratedContentType, type, dict, Any, str | None]]:
    """Return the (filename, content_type, schema, options, renderer, ext)
    tuple list for a given chapter prefix (e.g. 'ch73').
    """
    return [
        (f"{prefix}_chapter_summary.json", GeneratedContentType.CHAPTER_SUMMARY, ChapterSummaryOutput, {}, None, None),
        (f"{prefix}_lesson_plan.json", GeneratedContentType.LESSON_PLAN, LessonPlanOutput, {}, render_lesson_plan_docx, "docx"),
        (f"{prefix}_worksheet.json", GeneratedContentType.WORKSHEET, WorksheetOutput, {}, "worksheet", "pdf"),
        (f"{prefix}_ppt.json", GeneratedContentType.PPT, PPTOutlineOutput, {}, render_ppt_outline, "pptx"),
        (f"{prefix}_diagram.json", GeneratedContentType.DIAGRAM, DiagramOutput, {}, render_concept_map_svg, "svg"),
        # Simulation template is read from the JSON itself; we don't pass
        # it in `options` so the cache_key stays stable across template
        # choices.
        (f"{prefix}_simulation.json", GeneratedContentType.SIMULATION, SimulationOutput, {}, render_simulation_html, "html"),
    ]


def _title(content_type: GeneratedContentType, chapter: Chapter, subject_name: str) -> str:
    return (
        f"{content_type.value.replace('_', ' ').title()} - "
        f"Class {CLASS_LEVEL} - {subject_name} - "
        f"Chapter {chapter.chapter_number}: {chapter.title}"
    )


def load_content_blobs(
    db: Session,
    *,
    chapter_id: int,
    prefix: str,
) -> None:
    """Validate each blob's JSON, insert as a GeneratedContent row at
    status=APPROVED with published_at set, and run the matching
    renderer to produce the artifact file."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise SystemExit(f"Chapter {chapter_id} not found")
    subject_name = chapter.book.subject.name
    store = get_artifact_store()

    loaded = 0
    skipped = 0
    for filename, content_type, schema, options, renderer, extension in _content_blobs_for(prefix):
        path = DATA_DIR / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        validated = schema.model_validate(payload)
        output_json = validated.model_dump(mode="json")

        cache_key = build_generation_cache_key(
            content_type=content_type.value,
            academic_year=ACADEMIC_YEAR,
            class_level=CLASS_LEVEL,
            subject_id=SUBJECT_ID,
            chapter_id=chapter_id,
            topic_id=None,
            prompt=None,
            options=options or None,
        )
        existing = db.scalar(
            select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
        )
        if existing is not None:
            skipped += 1
            print(f"  [skip] {content_type.value}: row {existing.id} already exists.")
            continue

        now = datetime.now(timezone.utc)
        row = GeneratedContent(
            content_type=content_type,
            status=GeneratedContentStatus.APPROVED,
            cache_key=cache_key,
            academic_year=ACADEMIC_YEAR,
            class_level=CLASS_LEVEL,
            subject_id=SUBJECT_ID,
            chapter_id=chapter_id,
            topic_id=None,
            title=_title(content_type, chapter, subject_name),
            source_context=(chapter.full_text or "")[:4000],
            output_json=output_json,
            request_options=options or None,
            llm_provider="hand-authored",
            llm_model="curated-claude-agent",
            created_by_id=CREATED_BY_ID,
            published_at=now,
            published_by_id=CREATED_BY_ID,
        )
        db.add(row)
        db.flush()

        if renderer is None:
            pass
        elif renderer == "worksheet":
            pdf_bytes = render_worksheet_pdf(
                validated,
                class_level=CLASS_LEVEL,
                subject=subject_name,
                chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
                include_answer_key=True,
            )
            row.artifact_url = store.save(content_id=row.id, extension="pdf", data=pdf_bytes)
        else:
            data = renderer(validated)
            row.artifact_url = store.save(content_id=row.id, extension=extension, data=data)

        db.commit()
        loaded += 1
        print(f"  [ok]   {content_type.value}: row {row.id} artifact={row.artifact_url or '(json-only)'}")

    print(f"[ok] content blobs: loaded {loaded}, skipped {skipped} pre-existing")


# ----- internals -----------------------------------------------------------


def _slice(full_text: str, start_header: str, end_header: str) -> str:
    i = full_text.index(start_header)
    j = full_text.index(end_header, i + 1)
    return full_text[i:j].strip()
