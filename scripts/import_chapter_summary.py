"""Import a hand-authored chapter summary JSON into GeneratedContent.

Pydantic-validates against ChapterSummaryOutput, then writes a GeneratedContent
row in APPROVED status so it appears immediately in the student Learn flow.
Used as a fallback path when the LLM provider is rate-limited and a Claude /
human author writes the JSON directly.

Usage:
    .venv/Scripts/python.exe -m scripts.import_chapter_summary \\
        --chapter-id 59 --json-path tmp/ch02_summary.json
"""
import argparse
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.models.curriculum import Book, Chapter, SchoolClass, Subject
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.school import User, UserRole


log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, required=True)
    parser.add_argument("--json-path", required=True)
    parser.add_argument("--platform-admin-email", default="platform.team@anaadi.org")
    parser.add_argument("--academic-year", default="2026-27")
    parser.add_argument("--replace", action="store_true",
                        help="If a READY/APPROVED summary exists, delete it first.")
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        raw = json.load(f)
    summary = ChapterSummaryOutput.model_validate(raw)

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

        existing = list(
            db.scalars(
                select(GeneratedContent).where(
                    GeneratedContent.content_type == GeneratedContentType.CHAPTER_SUMMARY,
                    GeneratedContent.chapter_id == chapter.id,
                    GeneratedContent.status.in_(
                        [GeneratedContentStatus.READY, GeneratedContentStatus.APPROVED]
                    ),
                )
            )
        )
        if existing and not args.replace:
            print(
                f"Chapter {chapter.id} already has {len(existing)} summary row(s); "
                f"pass --replace to overwrite."
            )
            return
        for r in existing:
            db.delete(r)
        db.flush()

        cache_key = f"chapter_summary:hand:{chapter.id}:{datetime.now(timezone.utc).timestamp():.0f}"
        row = GeneratedContent(
            content_type=GeneratedContentType.CHAPTER_SUMMARY,
            status=GeneratedContentStatus.APPROVED,
            cache_key=cache_key,
            academic_year=args.academic_year,
            class_level=klass.level,
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=None,
            title=f"Ch {chapter.chapter_number} summary · {chapter.title}",
            output_json=summary.model_dump(mode="json"),
            llm_provider="claude-author",
            llm_model="claude-opus-4.7-1m",
            request_options={},
            created_by_id=admin.id,
            published_at=datetime.now(timezone.utc),
            published_by_id=admin.id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        print(f"Imported chapter summary #{row.id} for ch {chapter.chapter_number}: {chapter.title!r}")


if __name__ == "__main__":
    main()
