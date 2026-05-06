"""Scaffold CBSE Class 10 Sanskrit: subject + Shemushi book + chapter rows."""

from datetime import datetime, timezone
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"
SUBJECT_NAME = "Sanskrit"
PLACEHOLDER = "Pending content authoring."

BOOK = {
    "title": "Shemushi Bhag 2",
    "ncert_code": "jhss1dd",
    "chapters": [
        "शुचिपर्यावरणम्",
        "बुद्धिर्बलवती सदा",
        "व्यायामः सर्वदा पथ्यः",
        "शिशुलालनम्",
        "जननी तुल्यवत्सला",
        "सुभाषितानि",
        "सौहार्दं प्रकृतेः शोभा",
        "विचित्रः साक्षी",
        "सूक्तयः",
        "भूकंपविभीषिका",
    ],
}


def main() -> None:
    db = SessionLocal()
    try:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")
        print(f"[ok] resolved Class 10 -> school_class id={cls.id}")

        subj = db.scalar(select(Subject).where(
            Subject.class_id == cls.id, Subject.board == BOARD, Subject.name == SUBJECT_NAME))
        if subj is None:
            subj = Subject(class_id=cls.id, name=SUBJECT_NAME, language="sa", board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: {SUBJECT_NAME}")
        else:
            print(f"  [skip] subject_id={subj.id}: {SUBJECT_NAME}")

        book = db.scalar(select(Book).where(
            Book.subject_id == subj.id, Book.title == BOOK["title"]))
        if book is None:
            book = Book(subject_id=subj.id, title=BOOK["title"], ncert_code=BOOK["ncert_code"],
                academic_year=ACADEMIC_YEAR, source_url=None)
            db.add(book); db.flush()
            print(f"  [new]  book_id={book.id}: {BOOK['title']} ({BOOK['ncert_code']})")
        else:
            print(f"  [skip] book_id={book.id}: {BOOK['title']}")

        existing = {c.chapter_number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()}
        added = 0
        for idx, title in enumerate(BOOK["chapters"], start=1):
            if idx in existing: continue
            db.add(Chapter(book_id=book.id, chapter_number=idx, title=title,
                full_text=PLACEHOLDER, imported_at=datetime.now(timezone.utc)))
            added += 1
        db.commit()
        print(f"  chapters: created {added}, skipped {len(BOOK['chapters']) - added}")

        print()
        print("=== CBSE Class 10 Sanskrit chapters ===")
        rows = db.execute(text("""
            SELECT c.id, c.chapter_number, c.title FROM chapters c
            JOIN books b ON c.book_id = b.id JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            WHERE sc.level = 10 AND s.board = 'CBSE' AND s.name = 'Sanskrit'
            ORDER BY c.chapter_number
        """)).fetchall()
        for r in rows:
            print(f"  ch_id={r[0]:3d}  ch{r[1]:2d}  {r[2]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
