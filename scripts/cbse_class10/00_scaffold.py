"""Scaffold CBSE Class 10 Science: subject + book + 13 chapter rows.
Idempotent.

Run:
    PYTHONPATH=. PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/cbse_class10/00_scaffold.py
"""

from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"
PLACEHOLDER = "Pending content authoring. Scaffold row; will be populated in a follow-up pass."

CHAPTERS = [
    "Chemical Reactions and Equations",
    "Acids, Bases and Salts",
    "Metals and Non-metals",
    "Carbon and its Compounds",
    "Life Processes",
    "Control and Coordination",
    "How do Organisms Reproduce?",
    "Heredity",
    "Light - Reflection and Refraction",
    "The Human Eye and the Colourful World",
    "Electricity",
    "Magnetic Effects of Electric Current",
    "Our Environment",
]


def main() -> None:
    db = SessionLocal()
    try:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")
        print(f"[ok] resolved Class 10 -> id={cls.id}")

        # Subject
        subj = db.scalar(select(Subject).where(
            Subject.class_id == cls.id, Subject.board == BOARD, Subject.name == "Science"))
        if subj is None:
            subj = Subject(class_id=cls.id, name="Science", language="en", board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: Science")
        else:
            print(f"  [skip] subject_id={subj.id}: Science exists")

        # Book
        book = db.scalar(select(Book).where(
            Book.subject_id == subj.id, Book.title == "Science"))
        if book is None:
            book = Book(subject_id=subj.id, title="Science", ncert_code="jesc1dd",
                academic_year=ACADEMIC_YEAR, source_url=None)
            db.add(book); db.flush()
            print(f"  [new]  book_id={book.id}: Science (jesc1dd)")
        else:
            print(f"  [skip] book_id={book.id}: Science exists")

        # Chapters
        existing = {c.chapter_number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()}
        added = 0
        for idx, title in enumerate(CHAPTERS, start=1):
            if idx in existing: continue
            db.add(Chapter(book_id=book.id, chapter_number=idx, title=title,
                full_text=PLACEHOLDER, imported_at=datetime.now(timezone.utc)))
            added += 1
        db.commit()
        print(f"  chapters: created {added}, skipped {len(CHAPTERS) - added}")

        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT c.id, c.chapter_number, c.title FROM chapters c
            JOIN books b ON c.book_id = b.id
            JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            WHERE sc.level = 10 AND s.board = 'CBSE' AND s.name = 'Science'
            ORDER BY c.chapter_number
        """)).fetchall()
        print()
        print("=== CBSE Class 10 Science chapters ===")
        for r in rows: print(f"  ch_id={r[0]:3d}  ch{r[1]:2d}  {r[2]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
