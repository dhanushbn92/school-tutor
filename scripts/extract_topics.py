"""LLM-extract topics for one or more chapters and upsert into the Topic table.

Topics are conceptual sub-headings within a chapter (e.g. "Magnetic Poles",
"Properties of a Magnet"). They power the student-facing chapter browse and
let teachers scope generation jobs to a single topic.

Usage:
    .venv/Scripts/python.exe -m scripts.extract_topics --chapter-id 58
    .venv/Scripts/python.exe -m scripts.extract_topics --class-level 6 --subject Science
    .venv/Scripts/python.exe -m scripts.extract_topics --class-level 6 --subject Science --dry-run
"""
import argparse
import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.llm import LLMError, get_llm_provider
from app.llm.prompts.topic_extraction import (
    TOPIC_EXTRACTION_SYSTEM_PROMPT,
    build_topic_extraction_user_prompt,
)
from app.llm.schemas.topic_extraction import TopicExtractionOutput
from app.models.curriculum import Book, Chapter, SchoolClass, Subject, Topic


log = logging.getLogger(__name__)


# Cap chapter text to keep us under provider TPM limits (matches generation worker).
_MAX_CHAPTER_TEXT_CHARS = 25_000


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, default=None,
                        help="Extract topics for one chapter. Overrides --class-level/--subject.")
    parser.add_argument("--class-level", type=int, default=None)
    parser.add_argument("--subject", default=None,
                        help="Subject name, e.g. 'Science'. Required with --class-level.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Call the LLM but don't write Topic rows.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Delete existing topics for each chapter first.")
    args = parser.parse_args()

    with SessionLocal() as db:
        chapters = _resolve_chapters(db, args)
        if not chapters:
            print("No chapters match the filter.")
            return
        print(f"Will extract topics for {len(chapters)} chapter(s).")

    provider = get_llm_provider()
    total_new = 0
    for ch in chapters:
        with SessionLocal() as db:
            chapter = db.get(Chapter, ch.id)
            if chapter is None:
                continue
            text = chapter.full_text or ""
            if not text.strip():
                log.warning("ch %s has no full_text; skipping", chapter.id)
                continue
            if len(text) > _MAX_CHAPTER_TEXT_CHARS:
                text = text[:_MAX_CHAPTER_TEXT_CHARS] + "\n…[truncated for token budget]"

            existing_count = db.scalar(
                select(Topic).where(Topic.chapter_id == chapter.id).limit(1)
            )
            if existing_count is not None and not args.overwrite:
                log.info(
                    "ch %s already has topics; skipping (use --overwrite to replace)",
                    chapter.id,
                )
                continue

            log.info("ch %s: calling LLM for topic extraction…", chapter.id)
            t0 = time.time()
            try:
                result = provider.generate_structured(
                    system=TOPIC_EXTRACTION_SYSTEM_PROMPT,
                    user=build_topic_extraction_user_prompt(
                        class_level=ch.class_level,
                        subject_name=ch.subject_name,
                        chapter_number=chapter.chapter_number,
                        chapter_title=chapter.title,
                        chapter_text=text,
                    ),
                    response_model=TopicExtractionOutput,
                    temperature=0.2,
                )
            except LLMError as exc:
                log.error("ch %s: LLM error: %s", chapter.id, exc)
                continue

            elapsed = time.time() - t0
            log.info(
                "ch %s: %s topics extracted in %.1fs",
                chapter.id, len(result.topics), elapsed,
            )

            if args.dry_run:
                for t in result.topics:
                    print(f"  - {t.name}: {t.description}")
                continue

            kept = _persist_topics(db, chapter, result, overwrite=args.overwrite)
            db.commit()
            total_new += kept
            print(f"  ch {chapter.chapter_number} {chapter.title!r}: +{kept} topics")

    if not args.dry_run:
        print()
        print("=" * 60)
        print(f"Done. Added {total_new} topics across {len(chapters)} chapter(s).")


class _ChapterRef:
    def __init__(self, *, id: int, class_level: int, subject_name: str):
        self.id = id
        self.class_level = class_level
        self.subject_name = subject_name


def _resolve_chapters(db: Session, args) -> list[_ChapterRef]:
    if args.chapter_id is not None:
        chapter = db.get(Chapter, args.chapter_id)
        if chapter is None:
            raise SystemExit(f"Chapter {args.chapter_id} not found.")
        return [_chapter_ref(db, chapter)]

    if args.class_level is None or args.subject is None:
        raise SystemExit("Provide --chapter-id OR (--class-level AND --subject).")

    rows = db.execute(
        select(Chapter, SchoolClass.level, Subject.name)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .join(SchoolClass, Subject.class_id == SchoolClass.id)
        .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
        .order_by(Chapter.chapter_number)
    ).all()
    return [
        _ChapterRef(id=ch.id, class_level=lvl, subject_name=sub)
        for ch, lvl, sub in rows
    ]


def _chapter_ref(db: Session, chapter: Chapter) -> _ChapterRef:
    book = db.get(Book, chapter.book_id)
    subject = db.get(Subject, book.subject_id) if book else None
    klass = db.get(SchoolClass, subject.class_id) if subject else None
    if klass is None or subject is None:
        raise SystemExit(f"Chapter {chapter.id} not mapped to a class+subject.")
    return _ChapterRef(id=chapter.id, class_level=klass.level, subject_name=subject.name)


def _persist_topics(
    db: Session, chapter: Chapter, result: TopicExtractionOutput, *, overwrite: bool
) -> int:
    if overwrite:
        existing = list(db.scalars(select(Topic).where(Topic.chapter_id == chapter.id)))
        for t in existing:
            db.delete(t)
        db.flush()

    existing_names = {
        t.name.strip().lower()
        for t in db.scalars(select(Topic).where(Topic.chapter_id == chapter.id))
    }
    kept = 0
    for t in result.topics:
        norm = t.name.strip().lower()
        if norm in existing_names:
            continue
        db.add(Topic(chapter_id=chapter.id, name=t.name.strip(), description=t.description.strip()))
        existing_names.add(norm)
        kept += 1
    return kept


if __name__ == "__main__":
    main()
