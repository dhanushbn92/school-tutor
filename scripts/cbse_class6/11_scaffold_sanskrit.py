"""Scaffold CBSE Class 6 Sanskrit subject + Deepakam book + chapter placeholders.

Adds the Sanskrit subject (a third-language option in CBSE Class 6) with the
NEP-2020 NCERT textbook *Deepakam* (दीपकम्). Idempotent — re-running won't
double-insert anything.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/cbse_class6/11_scaffold_sanskrit.py
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 6
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"

PLACEHOLDER_FULL_TEXT = (
    "Pending content authoring. This chapter row was created by the "
    "scaffolding script; topics, outcomes, questions and content blobs "
    "will be added in a follow-up authoring pass."
)

# Subject + Book + Chapter list for CBSE Class 6 Sanskrit (Deepakam).
SUBJECT_NAME = "Sanskrit"
SUBJECT_LANGUAGE = "sa"
BOOK_TITLE = "Deepakam"
BOOK_NCERT_CODE = "fesa1"

# Pedagogically-aligned introductory Sanskrit chapter list for Class 6.
CHAPTER_TITLES = [
    "वर्णपरिचयः",                      # 1. Introduction to varṇas (alphabet)
    "मम परिचयः",                       # 2. Self-introduction (basic pronouns/verbs)
    "अस्माकं परिवारः",                # 3. Our family
    "अस्माकं विद्यालयः",              # 4. Our school
    "वयं क्रीडामः",                   # 5. We play
    "ऋतवः",                            # 6. Seasons
    "वृक्षाः सन्ति मित्राणि",         # 7. Trees are friends
    "पञ्चतन्त्रकथा",                  # 8. A Panchatantra story
    "देशभक्तिगीतम्",                  # 9. Patriotic verse
    "योगः जीवनशैली",                  # 10. Yoga as a way of life
    "सुभाषितानि",                      # 11. Subhāṣitas (wisdom verses)
    "गणितक्रीडा",                      # 12. Number play in Sanskrit
    "जलं जीवनम्",                      # 13. Water is life
    "त्योहाराः",                       # 14. Festivals
    "अहम् अपि करिष्यामि",             # 15. I too will do it
]


def main() -> None:
    db = SessionLocal()
    try:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")
        print(f"[ok] resolved Class 6 → school_class id={cls.id}")

        # Subject upsert
        subj = db.scalar(select(Subject).where(
            Subject.class_id == cls.id, Subject.board == BOARD, Subject.name == SUBJECT_NAME))
        if subj is None:
            subj = Subject(class_id=cls.id, name=SUBJECT_NAME, language=SUBJECT_LANGUAGE, board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: {SUBJECT_NAME}")
        else:
            print(f"  [skip] subject_id={subj.id}: {SUBJECT_NAME} (already exists)")

        # Book upsert
        book = db.scalar(select(Book).where(
            Book.subject_id == subj.id, Book.title == BOOK_TITLE))
        if book is None:
            book = Book(subject_id=subj.id, title=BOOK_TITLE, ncert_code=BOOK_NCERT_CODE,
                academic_year=ACADEMIC_YEAR, source_url=None)
            db.add(book); db.flush()
            print(f"  [new]  book_id={book.id}: {BOOK_TITLE} ({BOOK_NCERT_CODE})")
        else:
            print(f"  [skip] book_id={book.id}: {BOOK_TITLE} (already exists)")

        # Chapter rows
        existing_numbers = {
            c.chapter_number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()
        }
        added = 0
        for idx, title in enumerate(CHAPTER_TITLES, start=1):
            if idx in existing_numbers: continue
            db.add(Chapter(book_id=book.id, chapter_number=idx, title=title,
                full_text=PLACEHOLDER_FULL_TEXT, imported_at=datetime.now(timezone.utc)))
            added += 1
        db.commit()
        print(f"  chapters: created {added}, skipped {len(CHAPTER_TITLES) - added}")

        # Summary
        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT c.id, c.chapter_number, c.title FROM chapters c
            JOIN books b ON c.book_id = b.id
            JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            WHERE sc.level = 6 AND s.board = 'CBSE' AND s.name = 'Sanskrit'
            ORDER BY c.chapter_number
        """)).fetchall()
        print()
        print("=== CBSE Class 6 Sanskrit chapters ===")
        for r in rows: print(f"  ch_id={r[0]:3d}  ch{r[1]:2d}  {r[2]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
