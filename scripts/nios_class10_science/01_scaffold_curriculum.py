"""Scaffold NIOS Class 10 Science & Technology (212): create the
Subject, Book, and all 32 Chapter rows (titles only).

Idempotent: re-running skips rows that already exist by natural key.
Once the chapter scaffold is in place, content for any chapter can be
loaded via the content-bundle ingester:

    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle \\
        scripts/nios_class10_science/data/bundle_ch1_measurement.json

Source: NIOS Science and Technology (212) syllabus —
https://www.nios.ac.in/online-course-material/secondary-courses/Science-and-Technology-(212)-Syllabus.aspx

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class10_science.01_scaffold_curriculum
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


# Curriculum coordinates
BOARD = "NIOS"
CLASS_LEVEL = 10
SUBJECT_NAME = "Science"
SUBJECT_LANGUAGE = "en"
BOOK_TITLE = "NIOS Science and Technology (212)"
BOOK_NCERT_CODE = "NIOS-212"
BOOK_ACADEMIC_YEAR = "2026-27"
BOOK_SOURCE_URL = (
    "https://www.nios.ac.in/online-course-material/secondary-courses/"
    "Science-and-Technology-(212)-Syllabus.aspx"
)

# 32 chapters of NIOS Class 10 Science & Technology (212), in syllabus order.
CHAPTERS: list[tuple[int, str]] = [
    (1,  "Measurement in Science and Technology"),
    (2,  "Matter in Our Surroundings"),
    (3,  "Atom and Molecules"),
    (4,  "Chemical Reaction and Equations"),
    (5,  "Atomic Structure"),
    (6,  "Periodic Classification of Elements"),
    (7,  "Chemical Bonding"),
    (8,  "Acids, Bases and Salts"),
    (9,  "Motion and its Description"),
    (10, "Force and Motion"),
    (11, "Gravitation"),
    (12, "Sources of Energy"),
    (13, "Work and Energy"),
    (14, "Thermal Energy"),
    (15, "Light Energy"),
    (16, "Electrical Energy"),
    (17, "Magnetic Effect of Electric Current"),
    (18, "Sound and Communication"),
    (19, "Classification of Living Organisms"),
    (20, "History of Life on Earth"),
    (21, "Building Blocks of Life - Cell and Tissues"),
    (22, "Life Processes - 1: Nutrition, Transportation, Respiration and Excretion"),
    (23, "Life Processes - 2: Control and Coordination"),
    (24, "Life Processes - 3: Reproduction"),
    (25, "Heredity"),
    (26, "Air and Water"),
    (27, "Metals and Non-metals"),
    (28, "Carbon and Its Compounds"),
    (29, "Natural Environment"),
    (30, "Human Impact on Environment"),
    (31, "Food Production"),
    (32, "Health and Hygiene"),
]


def main() -> None:
    db = SessionLocal()
    try:
        # 1. SchoolClass
        klass = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if klass is None:
            raise SystemExit(
                f"No SchoolClass row for level={CLASS_LEVEL}. Scaffold the class first."
            )

        # 2. Subject
        subject = db.scalar(
            select(Subject)
            .where(Subject.class_id == klass.id)
            .where(Subject.name == SUBJECT_NAME)
            .where(Subject.language == SUBJECT_LANGUAGE)
            .where(Subject.board == BOARD)
        )
        if subject is None:
            subject = Subject(
                class_id=klass.id,
                name=SUBJECT_NAME,
                language=SUBJECT_LANGUAGE,
                board=BOARD,
            )
            db.add(subject)
            db.flush()
            print(f"[created] Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")
        else:
            print(f"[exists]  Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")

        # 3. Book (unique by subject_id + ncert_code + academic_year)
        book = db.scalar(
            select(Book)
            .where(Book.subject_id == subject.id)
            .where(Book.ncert_code == BOOK_NCERT_CODE)
            .where(Book.academic_year == BOOK_ACADEMIC_YEAR)
        )
        if book is None:
            book = Book(
                subject_id=subject.id,
                title=BOOK_TITLE,
                ncert_code=BOOK_NCERT_CODE,
                academic_year=BOOK_ACADEMIC_YEAR,
                source_url=BOOK_SOURCE_URL,
            )
            db.add(book)
            db.flush()
            print(f"[created] Book id={book.id}: {BOOK_TITLE} ({BOOK_NCERT_CODE})")
        else:
            print(f"[exists]  Book id={book.id}: {BOOK_TITLE} ({BOOK_NCERT_CODE})")

        # 4. Chapters (idempotent on chapter_number within the book)
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
        print(
            f"[ok] chapters: inserted {inserted}, skipped {len(existing)} pre-existing "
            f"(total scaffolded: {len(CHAPTERS)})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
