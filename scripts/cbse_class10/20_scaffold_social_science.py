"""Scaffold CBSE Class 10 Social Science: subject + 4 books + chapter rows.

Class 10 Social Science is split into FOUR separate NCERT books:
  - History       — India and the Contemporary World – II
  - Geography     — Contemporary India – II
  - Civics        — Democratic Politics – II
  - Economics     — Understanding Economic Development

Idempotent — re-running won't double-insert anything.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/cbse_class10/20_scaffold_social_science.py
"""

from datetime import datetime, timezone
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"
SUBJECT_NAME = "Social Science"
PLACEHOLDER = "Pending content authoring. Scaffold row."

BOOKS = [
    {
        "title": "India and the Contemporary World - II",
        "ncert_code": "jess3dd",
        "strand": "History",
        "chapters": [
            "The Rise of Nationalism in Europe",
            "Nationalism in India",
            "The Making of a Global World",
            "The Age of Industrialisation",
            "Print Culture and the Modern World",
        ],
    },
    {
        "title": "Contemporary India - II",
        "ncert_code": "jess2dd",
        "strand": "Geography",
        "chapters": [
            "Resources and Development",
            "Forest and Wildlife Resources",
            "Water Resources",
            "Agriculture",
            "Minerals and Energy Resources",
            "Manufacturing Industries",
            "Lifelines of National Economy",
        ],
    },
    {
        "title": "Democratic Politics - II",
        "ncert_code": "jess4dd",
        "strand": "Civics",
        "chapters": [
            "Power-sharing",
            "Federalism",
            "Gender, Religion and Caste",
            "Political Parties",
            "Outcomes of Democracy",
        ],
    },
    {
        "title": "Understanding Economic Development",
        "ncert_code": "jess1dd",
        "strand": "Economics",
        "chapters": [
            "Development",
            "Sectors of the Indian Economy",
            "Money and Credit",
            "Globalisation and the Indian Economy",
            "Consumer Rights",
        ],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")
        print(f"[ok] resolved Class 10 → school_class id={cls.id}")

        # Subject upsert
        subj = db.scalar(select(Subject).where(
            Subject.class_id == cls.id, Subject.board == BOARD, Subject.name == SUBJECT_NAME))
        if subj is None:
            subj = Subject(class_id=cls.id, name=SUBJECT_NAME, language="en", board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: {SUBJECT_NAME}")
        else:
            print(f"  [skip] subject_id={subj.id}: {SUBJECT_NAME} (already exists)")

        for spec in BOOKS:
            print()
            print(f"--- {spec['strand']}: {spec['title']} ---")
            book = db.scalar(select(Book).where(
                Book.subject_id == subj.id, Book.title == spec["title"]))
            if book is None:
                book = Book(subject_id=subj.id, title=spec["title"], ncert_code=spec["ncert_code"],
                    academic_year=ACADEMIC_YEAR, source_url=None)
                db.add(book); db.flush()
                print(f"  [new]  book_id={book.id}: {spec['title']} ({spec['ncert_code']})")
            else:
                print(f"  [skip] book_id={book.id}: {spec['title']} (already exists)")

            existing_numbers = {
                c.chapter_number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()
            }
            added = 0
            for idx, title in enumerate(spec["chapters"], start=1):
                if idx in existing_numbers: continue
                db.add(Chapter(book_id=book.id, chapter_number=idx, title=title,
                    full_text=PLACEHOLDER, imported_at=datetime.now(timezone.utc)))
                added += 1
            db.flush()
            print(f"  chapters: created {added}, skipped {len(spec['chapters']) - added}")
        db.commit()

        # Summary
        print()
        print("=== CBSE Class 10 Social Science chapters ===")
        rows = db.execute(text("""
            SELECT b.title, c.id, c.chapter_number, c.title FROM chapters c
            JOIN books b ON c.book_id = b.id JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            WHERE sc.level = 10 AND s.board = 'CBSE' AND s.name = 'Social Science'
            ORDER BY b.id, c.chapter_number
        """)).fetchall()
        last_book = None
        for r in rows:
            if r[0] != last_book:
                print(f"\n  {r[0]}")
                last_book = r[0]
            print(f"    ch_id={r[1]:3d}  ch{r[2]:2d}  {r[3]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
