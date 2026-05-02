"""Generate one CHAPTER_SUMMARY per chapter for a class+subject scope.

Each summary is auto-approved + published so it shows up in the student-facing
Learn flow without further moderation. Re-runs are no-ops by default — pass
`--regenerate` to force a fresh job per chapter.

Usage:
    .venv/Scripts/python.exe -m scripts.bulk_generate_chapter_summaries \\
        --class-level 6 --subject Science
    .venv/Scripts/python.exe -m scripts.bulk_generate_chapter_summaries \\
        --chapter-id 58 --regenerate
"""
import argparse
import logging
import time
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
from app.schemas.generation import GenerateContentRequest
from app.services.generation_service import create_or_reuse_generated_content
from app.workers.generate import run_generation_job


log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--class-level", type=int, default=None)
    parser.add_argument("--subject", default=None)
    parser.add_argument("--regenerate", action="store_true",
                        help="Force a fresh summary even if one already exists.")
    parser.add_argument("--platform-admin-email", default="platform.team@anaadi.org")
    args = parser.parse_args()

    with SessionLocal() as db:
        admin = db.scalar(
            select(User).where(
                User.email == args.platform_admin_email,
                User.role == UserRole.PLATFORM_ADMIN,
            )
        )
        if admin is None:
            raise SystemExit(f"Platform admin {args.platform_admin_email} not found.")
        chapters = _resolve_chapters(db, args)
        if not chapters:
            print("No chapters match the filter.")
            return
        print(f"Will generate summaries for {len(chapters)} chapter(s).")

    success = 0
    skipped = 0
    failed = 0

    for ch in chapters:
        with SessionLocal() as db:
            chapter = db.get(Chapter, ch["id"])
            if chapter is None:
                continue
            existing = db.scalar(
                select(GeneratedContent).where(
                    GeneratedContent.content_type == GeneratedContentType.CHAPTER_SUMMARY,
                    GeneratedContent.chapter_id == chapter.id,
                    GeneratedContent.status.in_(
                        [GeneratedContentStatus.READY, GeneratedContentStatus.APPROVED]
                    ),
                ).limit(1)
            )
            if existing is not None and not args.regenerate:
                log.info("ch %s already has a summary (#%s); skipping",
                         chapter.id, existing.id)
                skipped += 1
                continue

            req = GenerateContentRequest(
                content_type=GeneratedContentType.CHAPTER_SUMMARY,
                academic_year="2026-27",
                class_level=ch["class_level"],
                subject_id=ch["subject_id"],
                chapter_id=chapter.id,
                title=f"Ch {chapter.chapter_number} summary · {chapter.title}",
                force_regenerate=args.regenerate,
                options={},
            )
            row = create_or_reuse_generated_content(db, req, creator_user_id=admin.id)
            cid = row.id

        t0 = time.time()
        run_generation_job(cid)
        with SessionLocal() as db:
            row = db.get(GeneratedContent, cid)
            elapsed = time.time() - t0
            if row.status == GeneratedContentStatus.FAILED:
                log.warning("ch %s summary FAILED: %s", row.chapter_id, row.error_message)
                failed += 1
                continue
            if row.status == GeneratedContentStatus.READY:
                row.status = GeneratedContentStatus.APPROVED
                row.published_at = datetime.now(timezone.utc)
                row.published_by_id = admin.id
                db.commit()
            success += 1
            log.info("ch %s summary #%s ready in %.1fs", row.chapter_id, row.id, elapsed)

    print()
    print("=" * 60)
    print(f"Summaries: {success} generated, {skipped} skipped, {failed} failed.")


def _resolve_chapters(db, args) -> list[dict]:
    if args.chapter_id is not None:
        ch = db.get(Chapter, args.chapter_id)
        if ch is None:
            raise SystemExit(f"Chapter {args.chapter_id} not found.")
        bk = db.get(Book, ch.book_id)
        sub = db.get(Subject, bk.subject_id) if bk else None
        klass = db.get(SchoolClass, sub.class_id) if sub else None
        if not (bk and sub and klass):
            raise SystemExit(f"Chapter {ch.id} has no class/subject mapping.")
        return [{"id": ch.id, "class_level": klass.level, "subject_id": sub.id}]

    if args.class_level is None or args.subject is None:
        raise SystemExit("Provide --chapter-id OR (--class-level AND --subject).")

    rows = db.execute(
        select(Chapter.id, SchoolClass.level, Subject.id)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .join(SchoolClass, Subject.class_id == SchoolClass.id)
        .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
        .order_by(Chapter.chapter_number)
    ).all()
    return [{"id": cid, "class_level": lvl, "subject_id": sid} for cid, lvl, sid in rows]


if __name__ == "__main__":
    main()
