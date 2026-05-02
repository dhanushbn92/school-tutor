"""Import a hand-authored chapter-specific simulation.

Skips the rigid template-based SimulationOutput schema entirely. Each
simulation here is a self-contained HTML file (with inline JS / CSS) that
loads in an iframe via the artifact_url. This is the right shape for chapter
content that doesn't fit a template — e.g. a 3D balanced-plate builder, a
classification jungle, or a scientific-method lab.

Usage:
    .venv/Scripts/python.exe -m scripts.import_simulation_html \\
        --chapter-id 58 --html-path tmp/simulations/ch01_lab.html \\
        --title "Scientific Method Lab" --kind interactive \\
        --description "Drag the steps into the right order to investigate why ice floats."
"""
import argparse
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.school import User, UserRole
from app.services.artifact_store import get_artifact_store


log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, required=True)
    parser.add_argument("--html-path", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--kind",
        default="interactive",
        help="Short label, e.g. '3d', 'game', 'interactive'.",
    )
    parser.add_argument("--description", default="")
    parser.add_argument("--platform-admin-email", default="platform.team@anaadi.org")
    parser.add_argument("--academic-year", default="2026-27")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete existing READY/APPROVED simulations for the chapter first.",
    )
    args = parser.parse_args()

    with open(args.html_path, "rb") as f:
        html_bytes = f.read()

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
                        GeneratedContent.content_type == GeneratedContentType.SIMULATION,
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
            f"simulation:hand:{chapter.id}:"
            f"{datetime.now(timezone.utc).timestamp():.0f}"
        )
        row = GeneratedContent(
            content_type=GeneratedContentType.SIMULATION,
            status=GeneratedContentStatus.APPROVED,
            cache_key=cache_key,
            academic_year=args.academic_year,
            class_level=klass.level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=None,
            title=args.title,
            output_json={
                "kind": args.kind,
                "title": args.title,
                "description": args.description,
                "template": "custom",  # marker so the frontend knows this is hand-authored
            },
            llm_provider="claude-author",
            llm_model="claude-opus-4.7-1m",
            request_options={},
            created_by_id=admin.id,
            published_at=datetime.now(timezone.utc),
            published_by_id=admin.id,
        )
        db.add(row)
        db.flush()
        row.artifact_url = get_artifact_store().save(
            content_id=row.id, extension="html", data=html_bytes
        )
        db.commit()
        db.refresh(row)
        print(
            f"Imported custom simulation #{row.id} for ch {chapter.chapter_number}: "
            f"{chapter.title!r} ({len(html_bytes)} bytes)"
        )


if __name__ == "__main__":
    main()
