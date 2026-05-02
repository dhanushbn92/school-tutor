import argparse
import io
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
import zipfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.ingestion.ncert_http import download_binary, download_pdf, extract_chapter_title_from_pdf, extract_pdf_text
from app.models.curriculum import AcademicYear, Book, Chapter, ChapterSection, SchoolClass, Subject, Topic


def main() -> None:
    parser = argparse.ArgumentParser(description="Import NCERT chapter PDFs or book zip archives into the database.")
    parser.add_argument("--manifest", required=True, help="Path to the NCERT manifest JSON file.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max chapter count for a small test run.")
    parser.add_argument(
        "--classes",
        default=None,
        help="Optional comma-separated class levels to import, for example 6 or 6,7,8.",
    )
    parser.add_argument(
        "--subjects",
        default=None,
        help="Optional comma-separated subject names to import, for example Mathematics,Science.",
    )
    parser.add_argument(
        "--book-codes",
        default=None,
        help="Optional comma-separated NCERT book codes to import, for example fecu1.",
    )
    parser.add_argument("--workers", type=int, default=1, help="Parallel chapter download workers.")
    parser.add_argument("--commit-every", type=int, default=25, help="Commit every N successful chapter imports.")
    args = parser.parse_args()

    if get_settings().auto_create_tables:
        Base.metadata.create_all(bind=engine)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    with SessionLocal() as db:
        result = import_manifest(
            db,
            manifest,
            limit=args.limit,
            class_levels=_parse_class_levels(args.classes),
            subject_names=_parse_subject_names(args.subjects),
            book_codes=_parse_book_codes(args.book_codes),
            workers=args.workers,
            commit_every=args.commit_every,
        )
    print(json.dumps(result, indent=2))


def import_manifest(
    db: Session,
    manifest: dict,
    limit: int | None = None,
    class_levels: set[int] | None = None,
    subject_names: set[str] | None = None,
    book_codes: set[str] | None = None,
    workers: int = 1,
    commit_every: int = 25,
) -> dict:
    imported = 0
    skipped = 0
    failed: list[dict] = []

    academic_year = manifest["academic_year"]
    year = _upsert_academic_year(db, academic_year, is_current=manifest.get("is_current", False))
    base_url = manifest.get("base_url") or get_settings().ncert_base_url
    existing_keys = _existing_chapter_keys(db, academic_year)
    jobs = list(
        _iter_book_jobs(
            manifest,
            limit=limit,
            class_levels=class_levels,
            subject_names=subject_names,
            book_codes=book_codes,
            base_url=base_url,
            academic_year=academic_year,
            existing_keys=existing_keys,
        )
    )

    if workers <= 1:
        for job in jobs:
            try:
                result = _process_book_job(job)
                imported += _upsert_book_job(db, result, year=year)
                if imported % commit_every == 0:
                    db.commit()
            except (ValueError, OSError) as exc:
                failed.append(_job_failure(job, str(exc)))
                skipped += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_process_book_job, job): job for job in jobs}
            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    result = future.result()
                    imported += _upsert_book_job(db, result, year=year)
                    if imported % commit_every == 0:
                        db.commit()
                except (ValueError, OSError) as exc:
                    failed.append(_job_failure(job, str(exc)))
                    skipped += 1

    if imported % commit_every != 0:
        db.commit()
    return {"imported": imported, "skipped": skipped, "failed": failed}


def _iter_book_jobs(
    manifest: dict,
    *,
    limit: int | None,
    class_levels: set[int] | None,
    subject_names: set[str] | None,
    book_codes: set[str] | None,
    base_url: str,
    academic_year: str,
    existing_keys: set[tuple[str, int]],
):
    for class_item in manifest.get("classes", []):
        class_level = int(class_item["level"])
        if class_levels is not None and class_level not in class_levels:
            continue
        for subject_item in class_item.get("subjects", []):
            subject_name = subject_item["name"]
            if subject_names is not None and subject_name not in subject_names:
                continue
            subject_language = subject_item.get("language", "en")
            for book_item in subject_item.get("books", []):
                if book_codes is not None and book_item["ncert_code"] not in book_codes:
                    continue
                chapters = [
                    chapter_item
                    for chapter_item in book_item.get("chapters", [])
                    if (book_item["ncert_code"], int(chapter_item["number"])) not in existing_keys
                ]
                if not chapters:
                    continue
                if limit is not None:
                    if limit <= 0:
                        return
                    chapters = chapters[:limit]
                    limit -= len(chapters)
                yield {
                    "academic_year": academic_year,
                    "base_url": base_url,
                    "class_level": class_level,
                    "subject_name": subject_name,
                    "subject_language": subject_language,
                    "book": book_item,
                    "chapters": chapters,
                }


def _existing_chapter_keys(db: Session, academic_year: str) -> set[tuple[str, int]]:
    rows = db.execute(
        select(Book.ncert_code, Chapter.chapter_number)
        .join(Chapter, Chapter.book_id == Book.id)
        .where(Book.academic_year == academic_year)
    )
    return {(row[0], row[1]) for row in rows}


def _process_book_job(job: dict) -> dict:
    book_item = job["book"]
    zip_url = build_book_zip_url(base_url=job["base_url"], ncert_code=book_item["ncert_code"])
    zip_bytes = download_binary(zip_url, timeout=120, retries=3)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        chapter_results = []
        for chapter_item in job["chapters"]:
            chapter_number = int(chapter_item["number"])
            chapter_pdf_name = f"{book_item['ncert_code']}{chapter_number:02d}.pdf"
            pdf_bytes = _read_zip_member(archive, chapter_pdf_name)
            if pdf_bytes is None and chapter_item.get("pdf_url"):
                pdf_bytes = download_pdf(chapter_item["pdf_url"])
            if pdf_bytes is None:
                raise ValueError(f"Missing chapter PDF in zip: {chapter_pdf_name}")
            text, page_count, page_texts = extract_pdf_text(pdf_bytes)
            chapter_title = chapter_item.get("title") or extract_chapter_title_from_pdf(pdf_bytes, chapter_number)
            chapter_results.append(
                {
                    "chapter_number": chapter_number,
                    "chapter_title": chapter_title,
                    "pdf_url": chapter_item.get("pdf_url") or build_chapter_pdf_url(
                        base_url=job["base_url"],
                        ncert_code=book_item["ncert_code"],
                        chapter_number=chapter_number,
                    ),
                    "full_text": text,
                    "page_count": page_count,
                    "page_texts": page_texts,
                    "section_titles": chapter_item.get("sections", []),
                    "topic_names": chapter_item.get("topics", []),
                }
            )
    return {
        "academic_year": job["academic_year"],
        "class_level": job["class_level"],
        "subject_name": job["subject_name"],
        "subject_language": job["subject_language"],
        "book": book_item,
        "chapters": chapter_results,
    }


def _upsert_book_job(db: Session, result: dict, *, year: AcademicYear) -> int:
    school_class = _upsert_class(db, int(result["class_level"]))
    subject = _upsert_subject(
        db,
        school_class=school_class,
        name=result["subject_name"],
        language=result["subject_language"],
    )
    book_item = result["book"]
    book = _upsert_book(
        db,
        subject=subject,
        title=book_item["title"],
        ncert_code=book_item["ncert_code"],
        academic_year=year.name,
        source_url=book_item.get("source_url"),
    )
    imported = 0
    for chapter in result["chapters"]:
        _upsert_chapter(
            db,
            book=book,
            chapter_number=int(chapter["chapter_number"]),
            title=chapter["chapter_title"],
            full_text=chapter["full_text"],
            source_url=chapter["pdf_url"],
            page_count=int(chapter["page_count"]),
            section_titles=list(chapter["section_titles"]),
            topic_names=list(chapter["topic_names"]),
            page_texts=list(chapter["page_texts"]),
        )
        imported += 1
    return imported


def _job_failure(job: dict, error: str) -> dict:
    return {
        "book": job["book"]["ncert_code"],
        "chapter": job["chapters"][0].get("number") if job.get("chapters") else None,
        "title": job["chapters"][0].get("title") if job.get("chapters") else None,
        "error": error,
    }


def build_book_zip_url(*, base_url: str, ncert_code: str) -> str:
    return f"{base_url.rstrip('/')}/{ncert_code}dd.zip"


def build_chapter_pdf_url(*, base_url: str, ncert_code: str, chapter_number: int) -> str:
    return f"{base_url.rstrip('/')}/{ncert_code}{chapter_number:02d}.pdf"


def _upsert_academic_year(db: Session, name: str, is_current: bool) -> AcademicYear:
    item = db.scalar(select(AcademicYear).where(AcademicYear.name == name))
    if item is None:
        item = AcademicYear(name=name, is_current=is_current)
        db.add(item)
        db.flush()
    elif is_current and not item.is_current:
        item.is_current = True
    return item


def _upsert_class(db: Session, level: int) -> SchoolClass:
    item = db.scalar(select(SchoolClass).where(SchoolClass.level == level))
    if item is None:
        item = SchoolClass(level=level, display_name=f"Class {level}")
        db.add(item)
        db.flush()
    return item


def _upsert_subject(db: Session, *, school_class: SchoolClass, name: str, language: str) -> Subject:
    item = db.scalar(
        select(Subject).where(
            Subject.class_id == school_class.id,
            Subject.name == name,
            Subject.language == language,
        )
    )
    if item is None:
        item = Subject(class_id=school_class.id, name=name, language=language)
        db.add(item)
        db.flush()
    return item


def _upsert_book(
    db: Session,
    *,
    subject: Subject,
    title: str,
    ncert_code: str,
    academic_year: str,
    source_url: str | None,
) -> Book:
    item = db.scalar(
        select(Book).where(
            Book.subject_id == subject.id,
            Book.ncert_code == ncert_code,
            Book.academic_year == academic_year,
        )
    )
    if item is None:
        item = Book(
            subject_id=subject.id,
            title=title,
            ncert_code=ncert_code,
            academic_year=academic_year,
            source_url=source_url,
        )
        db.add(item)
        db.flush()
    else:
        item.title = title
        item.source_url = source_url
    return item


def _upsert_chapter(
    db: Session,
    *,
    book: Book,
    chapter_number: int,
    title: str,
    full_text: str,
    source_url: str,
    page_count: int,
    section_titles: list[str],
    topic_names: list[str],
    page_texts: list[str],
) -> Chapter:
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    item = db.scalar(select(Chapter).where(Chapter.book_id == book.id, Chapter.chapter_number == chapter_number))
    if item is None:
        item = Chapter(book_id=book.id, chapter_number=chapter_number, title=title)
        db.add(item)
        db.flush()

    item.title = title
    item.full_text = full_text
    item.source_url = source_url
    item.content_hash = content_hash
    item.page_count = page_count
    item.imported_at = datetime.now(UTC)

    _replace_sections(db, item, section_titles=section_titles, page_texts=page_texts)
    _replace_topics(db, item, topic_names=topic_names)
    return item


def _replace_sections(db: Session, chapter: Chapter, *, section_titles: list[str], page_texts: list[str]) -> None:
    for section in list(chapter.sections):
        db.delete(section)
    db.flush()

    if section_titles:
        for index, title in enumerate(section_titles, start=1):
            db.add(
                ChapterSection(
                    chapter_id=chapter.id,
                    section_number=str(index),
                    title=title,
                    section_text=_extract_section_text(chapter.full_text, title),
                )
            )
        return

    for index, page_text in enumerate(page_texts, start=1):
        if page_text.strip():
            db.add(
                ChapterSection(
                    chapter_id=chapter.id,
                    section_number=f"page-{index}",
                    title=f"Page {index}",
                    section_text=page_text,
                    page_start=index,
                    page_end=index,
                )
            )


def _replace_topics(db: Session, chapter: Chapter, *, topic_names: list[str]) -> None:
    for topic in list(chapter.topics):
        db.delete(topic)
    db.flush()

    for name in topic_names:
        db.add(Topic(chapter_id=chapter.id, name=name))


def _extract_section_text(full_text: str, section_title: str) -> str:
    marker = section_title.lower()
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    matched = [line for line in lines if marker in line.lower()]
    return "\n".join(matched)


def _read_zip_member(archive: zipfile.ZipFile, member_name: str) -> bytes | None:
    candidates = [member_name, member_name.lower(), member_name.upper()]
    for candidate in candidates:
        try:
            return archive.read(candidate)
        except KeyError:
            continue
    return None


def _parse_class_levels(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    return {int(part.strip()) for part in raw.split(",") if part.strip()}


def _parse_subject_names(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}


def _parse_book_codes(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}


if __name__ == "__main__":
    main()
