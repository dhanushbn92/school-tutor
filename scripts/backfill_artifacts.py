"""Re-render rendered files for `GeneratedContent` rows that are missing them.

Some rows landed in the catalog as APPROVED (`output_json` populated) but
without ever rendering their downloadable artefact — typically because they
were imported via `import_structured_content.py` rather than going through
the worker pipeline. The Content library's "Open" button then falls back to
the inline viewer; this script repairs those rows so the file path is also
available.

Scope (only types that have a backend renderer):

    lesson_plan  ->  DOCX
    diagram      ->  SVG (mind map / concept map)
    worksheet    ->  PDF
    ppt          ->  PPTX
    simulation   ->  HTML

Inline-only types (`chapter_summary`, `classroom_activity`, `resource_list`,
`flow_diagram`, `quiz`) are skipped — they intentionally have no artefact;
the SPA renders them from `output_json`.

Usage::

    # Local backfill (writes to data/artifacts/, useful for dev):
    .venv/Scripts/python.exe scripts/backfill_artifacts.py

    # Backfill against the prod GCS bucket (needs ADC + the env vars
    # below set; mirrors what Cloud Run would do):
    DATABASE_URL='postgresql://...' \
    ARTIFACT_BACKEND=gcs \
    GCS_BUCKET=school-tuter-artifacts-prod \
    .venv/Scripts/python.exe scripts/backfill_artifacts.py

The script is idempotent: it only touches rows whose `artifact_url` is
NULL/empty. Re-running after a successful pass is a no-op.
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.generation import GeneratedContent, GeneratedContentStatus, GeneratedContentType
from app.models.curriculum import Chapter, Subject
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store


log = logging.getLogger("backfill_artifacts")


# Each entry: (extension, output schema, render fn taking schema -> bytes,
# extra-kwargs builder for the renderer if any).
RENDERERS: dict[GeneratedContentType, tuple[str, type, Callable]] = {
    GeneratedContentType.LESSON_PLAN: ("docx", LessonPlanOutput, render_lesson_plan_docx),
    GeneratedContentType.DIAGRAM:     ("svg",  DiagramOutput,    render_concept_map_svg),
    GeneratedContentType.PPT:         ("pptx", PPTOutlineOutput, render_ppt_outline),
    GeneratedContentType.SIMULATION:  ("html", SimulationOutput, render_simulation_html),
    # Worksheet needs class_level / subject / chapter_title context — handled
    # specially below because its signature doesn't match the simple
    # `model -> bytes` shape.
}


def _render_worksheet(db: Session, row: GeneratedContent) -> bytes:
    chapter = db.get(Chapter, row.chapter_id) if row.chapter_id else None
    subject = None
    if chapter is not None and chapter.book_id is not None:
        from app.models.curriculum import Book
        book = db.get(Book, chapter.book_id)
        if book is not None:
            subject = db.get(Subject, book.subject_id)
    payload = WorksheetOutput.model_validate(row.output_json)
    return render_worksheet_pdf(
        payload,
        class_level=row.class_level or 0,
        subject=subject.name if subject else "Unknown",
        chapter_title=chapter.title if chapter else "Unknown chapter",
        include_answer_key=True,
    )


def _backfill_row(db: Session, row: GeneratedContent, store) -> bool:
    """Render and save one row's artefact. Returns True on success."""
    if row.output_json is None:
        log.warning("  #%s  %s  output_json is null, skipping", row.id, row.content_type.value)
        return False

    try:
        if row.content_type == GeneratedContentType.WORKSHEET:
            blob = _render_worksheet(db, row)
            ext = "pdf"
        else:
            entry = RENDERERS.get(row.content_type)
            if entry is None:
                log.info("  #%s  %s  no renderer for this type, skipping", row.id, row.content_type.value)
                return False
            ext, schema, render_fn = entry
            payload = schema.model_validate(row.output_json)
            blob = render_fn(payload)

        path = store.save(content_id=row.id, extension=ext, data=blob)
        row.artifact_url = path
        db.commit()
        log.info("  #%s  %-12s  -> %s  (%d bytes)", row.id, row.content_type.value, path, len(blob))
        return True
    except Exception as exc:
        db.rollback()
        log.error("  #%s  %s  FAILED: %s", row.id, row.content_type.value, exc)
        log.debug("%s", traceback.format_exc())
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be re-rendered without writing anything.",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        type=int,
        help="Only backfill these specific GeneratedContent ids (otherwise all "
             "missing-artefact rows in renderable types).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    renderable = list(RENDERERS.keys()) + [GeneratedContentType.WORKSHEET]

    with SessionLocal() as db:
        stmt = select(GeneratedContent).where(
            (GeneratedContent.artifact_url.is_(None))
            | (GeneratedContent.artifact_url == ""),
            GeneratedContent.content_type.in_(renderable),
            GeneratedContent.status.in_(
                [GeneratedContentStatus.READY, GeneratedContentStatus.APPROVED]
            ),
            GeneratedContent.output_json.isnot(None),
        ).order_by(GeneratedContent.id)
        if args.ids:
            stmt = stmt.where(GeneratedContent.id.in_(args.ids))
        rows = list(db.scalars(stmt))

        log.info("Found %d row(s) needing backfill:", len(rows))
        for r in rows:
            log.info("  #%s  type=%-12s  status=%s  title=%r",
                     r.id, r.content_type.value, r.status.value, (r.title or "")[:60])

        if args.dry_run:
            log.info("\nDry run — no changes made.")
            return
        if not rows:
            log.info("Nothing to do.")
            return

        log.info("\nRendering...")
        store = get_artifact_store()
        ok = fail = 0
        for row in rows:
            if _backfill_row(db, row, store):
                ok += 1
            else:
                fail += 1

        log.info("\nDone. ok=%d  failed=%d", ok, fail)
        if fail:
            sys.exit(1)


if __name__ == "__main__":
    main()
