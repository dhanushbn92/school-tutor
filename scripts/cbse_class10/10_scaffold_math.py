"""Scaffold CBSE Class 10 Mathematics: subject + book + 14 chapter rows.

Run:
    PYTHONPATH=. PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/cbse_class10/10_scaffold_math.py
"""

from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"
PLACEHOLDER = "Pending content authoring. Scaffold row."

CHAPTERS = [
    "Real Numbers",
    "Polynomials",
    "Pair of Linear Equations in Two Variables",
    "Quadratic Equations",
    "Arithmetic Progressions",
    "Triangles",
    "Coordinate Geometry",
    "Introduction to Trigonometry",
    "Some Applications of Trigonometry",
    "Circles",
    "Areas Related to Circles",
    "Surface Areas and Volumes",
    "Statistics",
    "Probability",
]


def main() -> None:
    db = SessionLocal()
    try:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")

        subj = db.scalar(select(Subject).where(
            Subject.class_id == cls.id, Subject.board == BOARD, Subject.name == "Mathematics"))
        if subj is None:
            subj = Subject(class_id=cls.id, name="Mathematics", language="en", board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: Mathematics")
        else:
            print(f"  [skip] subject_id={subj.id}: Mathematics exists")

        book = db.scalar(select(Book).where(Book.subject_id == subj.id, Book.title == "Mathematics"))
        if book is None:
            book = Book(subject_id=subj.id, title="Mathematics", ncert_code="jemh1dd",
                academic_year=ACADEMIC_YEAR, source_url=None)
            db.add(book); db.flush()
            print(f"  [new]  book_id={book.id}: Mathematics (jemh1dd)")
        else:
            print(f"  [skip] book_id={book.id}: Mathematics exists")

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
            WHERE sc.level = 10 AND s.board = 'CBSE' AND s.name = 'Mathematics'
            ORDER BY c.chapter_number
        """)).fetchall()
        print()
        print("=== CBSE Class 10 Mathematics chapters ===")
        for r in rows: print(f"  ch_id={r[0]:3d}  ch{r[1]:2d}  {r[2]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
