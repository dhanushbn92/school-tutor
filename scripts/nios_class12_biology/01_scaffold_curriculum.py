"""Scaffold NIOS Class 12 (Senior Secondary) Biology (314): create the
Subject, Book, and all 31 Chapter rows (titles only).

Idempotent: re-running skips rows that already exist by natural key.
Once the chapter scaffold is in place, content for any chapter can be
loaded via the content-bundle ingester:

    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle \\
        scripts/nios_class12_biology/data/bundle_ch1_origin_evolution.json

Source: NIOS Senior Secondary Biology (314) syllabus (5 modules, 31 lessons).

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_biology.01_scaffold_curriculum
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


BOARD = "NIOS"
CLASS_LEVEL = 12
SUBJECT_NAME = "Biology"
SUBJECT_LANGUAGE = "en"
BOOK_TITLE = "NIOS Senior Secondary Biology"
BOOK_NCERT_CODE = "nios-sr-biology"
BOOK_ACADEMIC_YEAR = "2026-27"
BOOK_SOURCE_URL = (
    "https://www.nios.ac.in/online-course-material/sr-secondary-courses/"
    "biology-(314).aspx"
)

# 31 lessons of NIOS Senior Secondary Biology (314) across 5 modules.
CHAPTERS: list[tuple[int, str]] = [
    # --- Module 1: Diversity and Evolution of Life ---
    (1, "Origin and Evolution of Life and Introduction to Classification"),
    (2, "The Kingdoms Monera, Protoctista and Fungi"),
    (3, "Kingdoms Plantae and Animalia"),
    (4, "Cell - Structure and Function"),
    (5, "Tissues and other Levels of Organization"),
    # --- Module 2: Plant and Animal Types and Functions ---
    (6, "Root System"),
    (7, "Shoot System"),
    (8, "Absorption, Transport and Water Loss in Plants"),
    (9, "Nutrition in Plants - Mineral Nutrition"),
    (10, "Nitrogen Metabolism"),
    (11, "Photosynthesis"),
    (12, "Respiration in Plants"),
    (13, "Nutrition and Digestion"),
    (14, "Respiration and Elimination of Nitrogenous Wastes"),
    (15, "Circulation of Body Fluids"),
    (16, "Locomotion and Movement"),
    (17, "Coordination and Control - The Nervous and Endocrine Systems"),
    (18, "Homeostasis: The Steady State"),
    # --- Module 3: Reproduction and Genetics ---
    (19, "Reproduction in Plants"),
    (20, "Growth and Development in Plants"),
    (21, "Reproduction and Population Control"),
    (22, "Principles of Genetics"),
    (23, "Molecular Inheritance and Gene Expression"),
    (24, "Genetics and Society"),
    # --- Module 4: Environment and Health ---
    (25, "Principles of Ecology"),
    (26, "Conservation and Use of Natural Resources"),
    (27, "Pollution"),
    (28, "Nutrition and Health"),
    (29, "Some Common Human Diseases"),
    # --- Module 5: Emerging Fields of Biology ---
    (30, "Biotechnology"),
    (31, "Immunobiology: An Introduction"),
]


def main() -> None:
    db = SessionLocal()
    try:
        klass = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if klass is None:
            raise SystemExit(f"No SchoolClass row for level={CLASS_LEVEL}.")

        subject = db.scalar(
            select(Subject)
            .where(Subject.class_id == klass.id)
            .where(Subject.name == SUBJECT_NAME)
            .where(Subject.language == SUBJECT_LANGUAGE)
            .where(Subject.board == BOARD)
        )
        if subject is None:
            subject = Subject(
                class_id=klass.id, name=SUBJECT_NAME,
                language=SUBJECT_LANGUAGE, board=BOARD,
            )
            db.add(subject); db.flush()
            print(f"[created] Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")
        else:
            print(f"[exists]  Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")

        book = db.scalar(
            select(Book)
            .where(Book.subject_id == subject.id)
            .where(Book.ncert_code == BOOK_NCERT_CODE)
            .where(Book.academic_year == BOOK_ACADEMIC_YEAR)
        )
        if book is None:
            book = Book(
                subject_id=subject.id, title=BOOK_TITLE,
                ncert_code=BOOK_NCERT_CODE, academic_year=BOOK_ACADEMIC_YEAR,
                source_url=BOOK_SOURCE_URL,
            )
            db.add(book); db.flush()
            print(f"[created] Book id={book.id}: {BOOK_TITLE}")
        else:
            print(f"[exists]  Book id={book.id}: {BOOK_TITLE}")

        existing = {
            c.chapter_number
            for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()
        }
        inserted = 0
        for num, title in CHAPTERS:
            if num in existing:
                continue
            db.add(Chapter(book_id=book.id, chapter_number=num, title=title))
            inserted += 1
        db.commit()
        print(f"[ok] chapters: inserted {inserted}, skipped {len(existing)} pre-existing (total {len(CHAPTERS)})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
