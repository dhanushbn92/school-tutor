"""Scaffold NIOS Class 10 Social Science (213): create the Subject,
Book, and all 27 Chapter rows.

The 27 lessons span four branches:
  History           (L1-L8)   — Ancient/Medieval/Modern world + colonial India
  Geography         (L9-L14)  — Physiography, climate, biodiversity, agriculture
  Civics/Political  (L15-L22) — Constitution, fundamental rights, governance
  Contemporary India (L23-L27) — Democracy, integration, environment, peace

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class10_socsci.01_scaffold_curriculum
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


BOARD = "NIOS"
CLASS_LEVEL = 10
SUBJECT_NAME = "Social Science"
SUBJECT_LANGUAGE = "en"
BOOK_TITLE = "NIOS Social Science (213)"
BOOK_NCERT_CODE = "NIOS-213"
BOOK_ACADEMIC_YEAR = "2026-27"
BOOK_SOURCE_URL = (
    "https://www.nios.ac.in/online-course-material/secondary-courses/"
    "Social-Science-(213)-Syllabus.aspx"
)

# 27 chapters of NIOS Social Science (213) in syllabus order.
CHAPTERS: list[tuple[int, str]] = [
    # --- History (L1-L8) ---
    (1, "Ancient World"),
    (2, "Medieval World"),
    (3, "Modern World - I"),
    (4, "Modern World - II"),
    (5, "Impact of British Rule on India: Economic, Social and Cultural (1757-1857)"),
    (6, "Religious and Social Awakening in Colonial India"),
    (7, "Popular Resistance to the British Rule"),
    (8, "Indian National Movement"),
    # --- Geography (L9-L14) ---
    (9, "Physiography of India"),
    (10, "Climate"),
    (11, "Bio-diversity"),
    (12, "Agriculture in India"),
    (13, "Transport and Communication"),
    (14, "Population: Our Greatest Resource"),
    # --- Civics / Political Science (L15-L22) ---
    (15, "Constitutional Values and Political System in India"),
    (16, "Fundamental Rights and Fundamental Duties"),
    (17, "India - A Welfare State"),
    (18, "Local Governments and Field Administration"),
    (19, "Governance at the State Level"),
    (20, "Governance at the Union Level"),
    (21, "Political Parties and Pressure Groups"),
    (22, "People's Participation in the Democratic Process"),
    # --- Contemporary India (L23-L27) ---
    (23, "Challenges to Indian Democracy"),
    (24, "National Integration and Secularism"),
    (25, "Socio-Economic Development and Empowerment of Disadvantaged Groups"),
    (26, "Environmental Degradation and Disaster Management"),
    (27, "Peace and Security"),
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
