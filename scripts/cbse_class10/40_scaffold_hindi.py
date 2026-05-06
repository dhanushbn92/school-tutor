"""Scaffold CBSE Class 10 Hindi (Course A): subject + 2 books + chapter rows.

Course A uses two NCERT textbooks:
  - Kshitij (क्षितिज) — main reader (poetry + prose)
  - Kritika (कृतिका) — supplementary reader

Idempotent — re-running won't double-insert anything.
"""

from datetime import datetime, timezone
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject

CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
BOARD = "CBSE"
SUBJECT_NAME = "Hindi"
PLACEHOLDER = "Pending content authoring. Scaffold row."

BOOKS = [
    {
        "title": "Kshitij Bhag 2",
        "ncert_code": "jhkh1dd",
        "chapters": [
            "सूरदास के पद",
            "राम-लक्ष्मण-परशुराम संवाद",
            "आत्मकथ्य",
            "उत्साह और अट नहीं रही है",
            "यह दंतुरित मुस्कान और फसल",
            "छाया मत छूना",
            "कन्यादान",
            "संगतकार",
            "नेताजी का चश्मा",
            "बालगोबिन भगत",
            "लखनवी अंदाज़",
            "एक कहानी यह भी",
            "नौबतखाने में इबादत",
            "संस्कृति",
        ],
    },
    {
        "title": "Kritika Bhag 2",
        "ncert_code": "jhkr1dd",
        "chapters": [
            "माता का अँचल",
            "जॉर्ज पंचम की नाक",
            "साना-साना हाथ जोड़ि",
            "एही ठैयाँ झुलनी हेरानी हो रामा",
            "मैं क्यों लिखता हूँ",
        ],
    },
]


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
            subj = Subject(class_id=cls.id, name=SUBJECT_NAME, language="hi", board=BOARD)
            db.add(subj); db.flush()
            print(f"  [new]  subject_id={subj.id}: {SUBJECT_NAME}")
        else:
            print(f"  [skip] subject_id={subj.id}: {SUBJECT_NAME}")

        for spec in BOOKS:
            print()
            print(f"--- {spec['title']} ---")
            book = db.scalar(select(Book).where(
                Book.subject_id == subj.id, Book.title == spec["title"]))
            if book is None:
                book = Book(subject_id=subj.id, title=spec["title"], ncert_code=spec["ncert_code"],
                    academic_year=ACADEMIC_YEAR, source_url=None)
                db.add(book); db.flush()
                print(f"  [new]  book_id={book.id}: {spec['title']} ({spec['ncert_code']})")
            else:
                print(f"  [skip] book_id={book.id}: {spec['title']}")

            existing = {c.chapter_number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()}
            added = 0
            for idx, title in enumerate(spec["chapters"], start=1):
                if idx in existing: continue
                db.add(Chapter(book_id=book.id, chapter_number=idx, title=title,
                    full_text=PLACEHOLDER, imported_at=datetime.now(timezone.utc)))
                added += 1
            db.flush()
            print(f"  chapters: created {added}, skipped {len(spec['chapters']) - added}")
        db.commit()

        print()
        print("=== CBSE Class 10 Hindi chapters ===")
        rows = db.execute(text("""
            SELECT b.title, c.id, c.chapter_number, c.title FROM chapters c
            JOIN books b ON c.book_id = b.id JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            WHERE sc.level = 10 AND s.board = 'CBSE' AND s.name = 'Hindi'
            ORDER BY b.id, c.chapter_number
        """)).fetchall()
        last = None
        for r in rows:
            if r[0] != last:
                print(f"\n  {r[0]}")
                last = r[0]
            print(f"    ch_id={r[1]:3d}  ch{r[2]:2d}  {r[3]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
