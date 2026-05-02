"""Import a hand-authored structured-content JSON into GeneratedContent.

Accepts any content type whose schema lives in app/llm/schemas/. Validates
the JSON against the appropriate Pydantic model, then writes a
GeneratedContent row in APPROVED status (so it appears in the catalog
immediately, like the chapter-summary import path).

Skipping artifact rendering on purpose — these on-screen-only content types
are read straight out of `output_json` by the frontend.

Usage:
    .venv/Scripts/python.exe -m scripts.import_structured_content \\
        --content-type lesson_plan --chapter-id 58 \\
        --json-path tmp/lesson_plans/ch01.json
"""
import argparse
import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.classroom_activity import ClassroomActivitySetOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.flow_diagram import FlowDiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.resource_list import ResourceListOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import Book, Chapter, SchoolClass, Subject
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.school import User, UserRole
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store


log = logging.getLogger(__name__)

_TYPE_TO_SCHEMA: dict[GeneratedContentType, type[BaseModel]] = {
    GeneratedContentType.CHAPTER_SUMMARY: ChapterSummaryOutput,
    GeneratedContentType.LESSON_PLAN: LessonPlanOutput,
    GeneratedContentType.DIAGRAM: DiagramOutput,
    GeneratedContentType.SIMULATION: SimulationOutput,
    GeneratedContentType.CLASSROOM_ACTIVITY: ClassroomActivitySetOutput,
    GeneratedContentType.RESOURCE_LIST: ResourceListOutput,
    GeneratedContentType.WORKSHEET: WorksheetOutput,
    GeneratedContentType.FLOW_DIAGRAM: FlowDiagramOutput,
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-type", required=True,
                        help="One of: " + ", ".join(t.value for t in _TYPE_TO_SCHEMA))
    parser.add_argument("--chapter-id", type=int, required=True)
    parser.add_argument("--json-path", required=True)
    parser.add_argument("--title", default=None,
                        help="Optional title; defaults from the JSON or chapter info.")
    parser.add_argument("--platform-admin-email", default="platform.team@anaadi.org")
    parser.add_argument("--academic-year", default="2026-27")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete existing READY/APPROVED rows of this type for the chapter first.",
    )
    args = parser.parse_args()

    try:
        ctype = GeneratedContentType(args.content_type)
    except ValueError:
        raise SystemExit(
            f"--content-type must be one of: {', '.join(t.value for t in _TYPE_TO_SCHEMA)}"
        )
    schema = _TYPE_TO_SCHEMA.get(ctype)
    if schema is None:
        raise SystemExit(f"No schema registered for content type {args.content_type!r}")

    with open(args.json_path, encoding="utf-8") as f:
        raw = json.load(f)
    payload = schema.model_validate(raw)

    with SessionLocal() as db:
        admin = db.scalar(
            select(User).where(
                User.email == args.platform_admin_email,
                User.role == UserRole.PLATFORM_ADMIN,
            )
        )
        if admin is None:
            raise SystemExit(f"Platform admin {args.platform_admin_email} not found.")

        chapter = db.get(Chapter, args.chapter_id)
        if chapter is None:
            raise SystemExit(f"Chapter {args.chapter_id} not found.")
        book = db.get(Book, chapter.book_id)
        subject = db.get(Subject, book.subject_id) if book else None
        klass = db.get(SchoolClass, subject.class_id) if subject else None
        if not (book and subject and klass):
            raise SystemExit(f"Chapter {chapter.id} not mapped to class+subject.")

        if args.replace_existing:
            existing = list(
                db.scalars(
                    select(GeneratedContent).where(
                        GeneratedContent.content_type == ctype,
                        GeneratedContent.chapter_id == chapter.id,
                        GeneratedContent.status.in_(
                            [GeneratedContentStatus.READY, GeneratedContentStatus.APPROVED]
                        ),
                    )
                )
            )
            for r in existing:
                db.delete(r)
            db.flush()

        cache_key = (
            f"{ctype.value}:hand:{chapter.id}:"
            f"{datetime.now(timezone.utc).timestamp():.0f}"
        )
        title = args.title or _default_title(payload, chapter, ctype)
        # Resource lists go through admin approval (READY); everything else is
        # vetted by the author so it lands as APPROVED.
        initial_status = (
            GeneratedContentStatus.READY
            if ctype == GeneratedContentType.RESOURCE_LIST
            else GeneratedContentStatus.APPROVED
        )
        published_at = (
            datetime.now(timezone.utc)
            if initial_status == GeneratedContentStatus.APPROVED
            else None
        )
        published_by = admin.id if initial_status == GeneratedContentStatus.APPROVED else None

        row = GeneratedContent(
            content_type=ctype,
            status=initial_status,
            cache_key=cache_key,
            academic_year=args.academic_year,
            class_level=klass.level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=None,
            title=title,
            output_json=payload.model_dump(mode="json"),
            llm_provider="claude-author",
            llm_model="claude-opus-4.7-1m",
            request_options={},
            created_by_id=admin.id,
            published_at=published_at,
            published_by_id=published_by,
        )
        db.add(row)
        db.flush()
        # Simulations need an interactive HTML artifact.
        if ctype == GeneratedContentType.SIMULATION:
            html_bytes = render_simulation_html(payload)  # type: ignore[arg-type]
            row.artifact_url = get_artifact_store().save(
                content_id=row.id, extension="html", data=html_bytes
            )
        # Worksheets render to a PDF that students download / open.
        elif ctype == GeneratedContentType.WORKSHEET:
            pdf_bytes = render_worksheet_pdf(
                payload,  # type: ignore[arg-type]
                class_level=klass.level,
                subject=subject.name,
                chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
                include_answer_key=True,
            )
            row.artifact_url = get_artifact_store().save(
                content_id=row.id, extension="pdf", data=pdf_bytes
            )
        db.commit()
        db.refresh(row)
        print(
            f"Imported {ctype.value} #{row.id} for ch {chapter.chapter_number}: {chapter.title!r}"
        )


def _default_title(
    payload: BaseModel, chapter: Chapter, ctype: GeneratedContentType
) -> str:
    payload_title = getattr(payload, "title", None)
    if payload_title:
        return str(payload_title)[:300]
    return f"Ch {chapter.chapter_number} {ctype.value} · {chapter.title}"[:300]


if __name__ == "__main__":
    main()
