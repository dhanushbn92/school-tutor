"""Scaffold CBSE Class 6 subjects, books and chapter rows for Mathematics,
Social Science and English (NCF 2024 books). Hindi (Malhar) and Science
(Curiosity) already exist; this script will not touch them.

Idempotent — re-running won't double-insert anything.

After Phase 0 the SPA will show all Class 6 CBSE subjects with their full
chapter lists. Chapters carry placeholder full_text; chapters 1 and 2 will
get real content in subsequent per-subject sessions.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/cbse_class6/00_scaffold_subjects_books.py
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


# (subject_name, language, book_title, ncert_code, chapter_titles)
SCAFFOLD: list[tuple[str, str, str, str, list[str]]] = [
    (
        "Mathematics", "en", "Ganita Prakash", "fegp1",
        [
            "Patterns in Mathematics",
            "Lines and Angles",
            "Number Play",
            "Data Handling and Presentation",
            "Prime Time",
            "Perimeter and Area",
            "Fractions",
            "Playing with Constructions",
            "Symmetry",
            "The Other Side of Zero",
        ],
    ),
    (
        "Social Science", "en", "Exploring Society: India and Beyond", "fees1",
        [
            "Locating Places on the Earth",
            "Oceans and Continents",
            "Landforms and Life",
            "Timeline and Sources of History",
            "India, That Is Bharat",
            "The Beginnings of Indian Civilisation",
            "India's Cultural Roots",
            "Unity in Diversity, or 'Many in the One'",
            "Family and Community",
            "Grassroots Democracy — Part 1: Governance",
            "Grassroots Democracy — Part 2: Local Government in Rural Areas",
            "Grassroots Democracy — Part 3: Local Government in Urban Areas",
        ],
    ),
    (
        "English", "en", "Poorvi", "fepv1",
        [
            "A Bottle of Dew",
            "The Raven and the Fox",
            "The Unlikely Best Friends",
            "A Friend's Prayer",
            "Rama to the Rescue",
            "The Chair",
            "The Winner",
            "Yoga: A Way of Life",
        ],
    ),
]


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Resolve Class 6 SchoolClass row.
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(f"school_classes row for level={CLASS_LEVEL} not found")
        print(f"[ok] resolved Class 6 → school_class id={cls.id}")

        for subject_name, language, book_title, ncert_code, chapter_titles in SCAFFOLD:
            print()
            print(f"--- {subject_name} ({book_title}) ---")

            # 2. Subject upsert.
            subj = db.scalar(
                select(Subject).where(
                    Subject.class_id == cls.id,
                    Subject.board == BOARD,
                    Subject.name == subject_name,
                )
            )
            if subj is None:
                subj = Subject(
                    class_id=cls.id,
                    name=subject_name,
                    language=language,
                    board=BOARD,
                )
                db.add(subj)
                db.flush()
                print(f"  [new]  subject_id={subj.id}: {subject_name}")
            else:
                print(f"  [skip] subject_id={subj.id}: {subject_name} (already exists)")

            # 3. Book upsert (one book per subject for the moment).
            book = db.scalar(
                select(Book).where(
                    Book.subject_id == subj.id,
                    Book.title == book_title,
                )
            )
            if book is None:
                book = Book(
                    subject_id=subj.id,
                    title=book_title,
                    ncert_code=ncert_code,
                    academic_year=ACADEMIC_YEAR,
                    source_url=None,
                )
                db.add(book)
                db.flush()
                print(f"  [new]  book_id={book.id}: {book_title} ({ncert_code})")
            else:
                print(f"  [skip] book_id={book.id}: {book_title} (already exists)")

            # 4. Chapter rows — keyed by chapter_number.
            existing_numbers = {
                c.chapter_number
                for c in db.scalars(
                    select(Chapter).where(Chapter.book_id == book.id)
                ).all()
            }
            added = 0
            for idx, title in enumerate(chapter_titles, start=1):
                if idx in existing_numbers:
                    continue
                db.add(
                    Chapter(
                        book_id=book.id,
                        chapter_number=idx,
                        title=title,
                        full_text=PLACEHOLDER_FULL_TEXT,
                        imported_at=datetime.now(timezone.utc),
                    )
                )
                added += 1
            db.flush()
            print(
                f"  chapters: created {added}, skipped {len(chapter_titles) - added} "
                f"(book has {len(chapter_titles)} chapters total)"
            )

        db.commit()

        # 5. Summary report.
        print()
        print("=== CBSE Class 6 curriculum after scaffold ===")
        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT s.name, b.title, b.id, COUNT(c.id) AS chapters
            FROM subjects s
            JOIN school_classes sc ON s.class_id = sc.id
            JOIN books b ON b.subject_id = s.id
            LEFT JOIN chapters c ON c.book_id = b.id
            WHERE sc.level = 6 AND s.board = 'CBSE'
            GROUP BY s.name, b.title, b.id
            ORDER BY s.name, b.title
        """)).fetchall()
        for r in rows:
            print(f"  {r[0]:>22}  {r[1]:>40}  book_id={r[2]:3d}  chapters={r[3]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
