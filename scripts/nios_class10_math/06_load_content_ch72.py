"""Load all six bootstrap content blobs for NIOS Class 10 Math, Chapter 2
(Exponents and Radicals, chapter_id=72) from data/ch72_*.json.

Identical structure to 03_load_content_ch71.py — see that file for
full commentary. We duplicate rather than parameterise to keep each
chapter's loader script self-contained and grep-able.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/06_load_content_ch72.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import Chapter
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key


CHAPTER_ID = 72
SUBJECT_ID = 12
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14  # platform.team@anaadi.org

DATA_DIR = Path(__file__).parent / "data"


# (file, content_type, schema, options, renderer, extension).
# renderer == "worksheet" is special-cased below because the PDF
# renderer needs extra kwargs that aren't on the validated model.
BLOBS: list[tuple[str, GeneratedContentType, type, dict[str, Any], object | None, str | None]] = [
    ("ch72_chapter_summary.json", GeneratedContentType.CHAPTER_SUMMARY, ChapterSummaryOutput, {}, None, None),
    ("ch72_lesson_plan.json", GeneratedContentType.LESSON_PLAN, LessonPlanOutput, {}, render_lesson_plan_docx, "docx"),
    ("ch72_worksheet.json", GeneratedContentType.WORKSHEET, WorksheetOutput, {}, "worksheet", "pdf"),
    ("ch72_ppt.json", GeneratedContentType.PPT, PPTOutlineOutput, {}, render_ppt_outline, "pptx"),
    ("ch72_diagram.json", GeneratedContentType.DIAGRAM, DiagramOutput, {}, render_concept_map_svg, "svg"),
    ("ch72_simulation.json", GeneratedContentType.SIMULATION, SimulationOutput, {"template": "match_pairs"}, render_simulation_html, "html"),
]


def _title(content_type: GeneratedContentType, chapter: Chapter, subject_name: str) -> str:
    return (
        f"{content_type.value.replace('_', ' ').title()} - "
        f"Class {CLASS_LEVEL} - {subject_name} - "
        f"Chapter {chapter.chapter_number}: {chapter.title}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        chapter = db.get(Chapter, CHAPTER_ID)
        if chapter is None:
            raise SystemExit(f"Chapter {CHAPTER_ID} not found")
        subject_name = chapter.book.subject.name

        store = get_artifact_store()

        loaded = 0
        skipped = 0
        for filename, content_type, schema, options, renderer, extension in BLOBS:
            path = DATA_DIR / filename
            payload = json.loads(path.read_text(encoding="utf-8"))

            validated = schema.model_validate(payload)
            output_json = validated.model_dump(mode="json")

            cache_key = build_generation_cache_key(
                content_type=content_type.value,
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=CHAPTER_ID,
                topic_id=None,
                prompt=None,
                options=options or None,
            )

            existing = db.scalar(
                select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
            )
            if existing is not None:
                skipped += 1
                print(f"[skip] {content_type.value}: row {existing.id} already exists.")
                continue

            now = datetime.now(timezone.utc)
            row = GeneratedContent(
                content_type=content_type,
                status=GeneratedContentStatus.APPROVED,
                cache_key=cache_key,
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=CHAPTER_ID,
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
            print(f"[ok]   {content_type.value}: row {row.id} artifact={row.artifact_url or '(json-only)'}")

        print(f"\nDone. Loaded {loaded} blobs, skipped {skipped} pre-existing.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
