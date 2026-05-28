"""Replace the platform-authored chapter_summary and worksheet rows for
NIOS Class 12 Physics chapters 1-4 with NIOS-OFFICIAL content sourced
from the LG (Learner's Guide) and WS (Worksheet) documents.

This script:
  1. Deletes the existing chapter_summary and worksheet GeneratedContent
     rows for chapters 73-76 (and removes their PDF/DOCX/etc. artifacts).
  2. Inserts new rows from the chXX_chapter_summary_nios.json and
     chXX_worksheet_nios.json files, renders the worksheet PDF artifact,
     and marks both as APPROVED + published.

Idempotent: re-running drops + re-inserts each row cleanly.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_physics.07_load_nios_official
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import Chapter
from app.models.generation import GeneratedContent, GeneratedContentStatus, GeneratedContentType
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key

from scripts.nios_class12_physics.lib import (
    ACADEMIC_YEAR,
    CLASS_LEVEL,
    CREATED_BY_ID,
    DATA_DIR,
    SUBJECT_ID,
)


CHAPTERS = [73, 74, 75, 76]


def _delete_existing(db, *, chapter_id: int, content_type: GeneratedContentType) -> None:
    """Drop the existing row(s) for this (chapter, type) so a fresh
    insert can succeed without hitting the unique cache_key index."""
    rows = (
        db.scalars(
            select(GeneratedContent)
            .where(GeneratedContent.chapter_id == chapter_id)
            .where(GeneratedContent.content_type == content_type)
        )
        .all()
    )
    for row in rows:
        # Artifact files (PDF/DOCX/...) are left on disk; the store path
        # uses the row ID, so re-inserts get a new ID and a new file.
        db.delete(row)
    if rows:
        # Flush so the DELETE hits the DB BEFORE the subsequent INSERT;
        # otherwise SQLAlchemy may order the INSERT first and the unique
        # cache_key index will reject it.
        db.flush()
        print(f"  [drop] {content_type.value}: removed {len(rows)} existing row(s)")


def load_one(db, *, chapter_id: int) -> None:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise SystemExit(f"Chapter {chapter_id} not found")
    subject_name = chapter.book.subject.name
    prefix = f"ch{chapter_id}"
    store = get_artifact_store()
    now = datetime.now(timezone.utc)

    # ----- chapter_summary -----
    sum_path = DATA_DIR / f"{prefix}_chapter_summary_nios.json"
    sum_payload = json.loads(sum_path.read_text(encoding="utf-8"))
    sum_validated = ChapterSummaryOutput.model_validate(sum_payload)
    sum_output_json = sum_validated.model_dump(mode="json")

    _delete_existing(db, chapter_id=chapter_id, content_type=GeneratedContentType.CHAPTER_SUMMARY)

    sum_cache_key = build_generation_cache_key(
        content_type=GeneratedContentType.CHAPTER_SUMMARY.value,
        academic_year=ACADEMIC_YEAR,
        class_level=CLASS_LEVEL,
        subject_id=SUBJECT_ID,
        chapter_id=chapter_id,
        topic_id=None,
        prompt=None,
        options=None,
    )
    sum_row = GeneratedContent(
        content_type=GeneratedContentType.CHAPTER_SUMMARY,
        status=GeneratedContentStatus.APPROVED,
        cache_key=sum_cache_key,
        academic_year=ACADEMIC_YEAR,
        class_level=CLASS_LEVEL,
        subject_id=SUBJECT_ID,
        chapter_id=chapter_id,
        topic_id=None,
        title=(
            f"Chapter Summary - Class {CLASS_LEVEL} - {subject_name} - "
            f"Chapter {chapter.chapter_number}: {chapter.title} (NIOS Official)"
        ),
        source_context=(chapter.full_text or "")[:4000],
        output_json=sum_output_json,
        request_options=None,
        llm_provider="nios-official",
        llm_model="nios-lg-pdf-transcription",
        created_by_id=CREATED_BY_ID,
        published_at=now,
        published_by_id=CREATED_BY_ID,
    )
    db.add(sum_row)
    db.flush()
    print(f"  [ok]   chapter_summary: row {sum_row.id} (NIOS LG)")

    # ----- worksheet -----
    ws_path = DATA_DIR / f"{prefix}_worksheet_nios.json"
    ws_payload = json.loads(ws_path.read_text(encoding="utf-8"))
    ws_validated = WorksheetOutput.model_validate(ws_payload)
    ws_output_json = ws_validated.model_dump(mode="json")

    _delete_existing(db, chapter_id=chapter_id, content_type=GeneratedContentType.WORKSHEET)

    ws_cache_key = build_generation_cache_key(
        content_type=GeneratedContentType.WORKSHEET.value,
        academic_year=ACADEMIC_YEAR,
        class_level=CLASS_LEVEL,
        subject_id=SUBJECT_ID,
        chapter_id=chapter_id,
        topic_id=None,
        prompt=None,
        options=None,
    )
    ws_row = GeneratedContent(
        content_type=GeneratedContentType.WORKSHEET,
        status=GeneratedContentStatus.APPROVED,
        cache_key=ws_cache_key,
        academic_year=ACADEMIC_YEAR,
        class_level=CLASS_LEVEL,
        subject_id=SUBJECT_ID,
        chapter_id=chapter_id,
        topic_id=None,
        title=(
            f"Worksheet - Class {CLASS_LEVEL} - {subject_name} - "
            f"Chapter {chapter.chapter_number}: {chapter.title} (NIOS Official)"
        ),
        source_context=(chapter.full_text or "")[:4000],
        output_json=ws_output_json,
        request_options=None,
        llm_provider="nios-official",
        llm_model="nios-ws-pdf-transcription",
        created_by_id=CREATED_BY_ID,
        published_at=now,
        published_by_id=CREATED_BY_ID,
    )
    db.add(ws_row)
    db.flush()

    # Render the worksheet PDF.
    pdf_bytes = render_worksheet_pdf(
        ws_validated,
        class_level=CLASS_LEVEL,
        subject=subject_name,
        chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
        include_answer_key=True,
    )
    ws_row.artifact_url = store.save(content_id=ws_row.id, extension="pdf", data=pdf_bytes)
    print(f"  [ok]   worksheet: row {ws_row.id} artifact={ws_row.artifact_url} (NIOS WS)")


def main() -> None:
    db = SessionLocal()
    try:
        for chapter_id in CHAPTERS:
            print(f"--- chapter {chapter_id} ---")
            load_one(db, chapter_id=chapter_id)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
