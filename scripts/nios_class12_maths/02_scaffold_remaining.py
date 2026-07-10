"""Scaffold the remaining chapters (3-38) of NIOS Senior Secondary
Mathematics (311). Chapters 1 (Sets) and 2 (Relations and Functions-I)
already exist. Idempotent: skips chapter_numbers already present.

Chapter list from the official NIOS 311 course material (38 lessons).

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_maths.02_scaffold_remaining
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, Subject

SUBJECT_ID = 25  # NIOS class 12 Mathematics
BOOK_NCERT_CODE = "311"

# Full 38-lesson list; scaffold inserts any that are missing (3-38).
CHAPTERS: list[tuple[int, str]] = [
    (1, "Sets"),
    (2, "Relations and Functions-I"),
    (3, "Trigonometric Functions-I"),
    (4, "Trigonometric Functions-II"),
    (5, "Relation between Sides and Angles of a Triangle"),
    (6, "Sequences and Series"),
    (7, "Some Special Sequences"),
    (8, "Complex Numbers"),
    (9, "Quadratic Equations and Linear Inequalities"),
    (10, "Principle of Mathematical Induction"),
    (11, "Permutations and Combinations"),
    (12, "Binomial Theorem"),
    (13, "Cartesian System of Rectangular Co-ordinates"),
    (14, "Straight Lines"),
    (15, "Circles"),
    (16, "Conic Sections"),
    (17, "Measures of Dispersion"),
    (18, "Random Experiments and Events"),
    (19, "Probability"),
    (20, "Matrices"),
    (21, "Determinants"),
    (22, "Inverse of a Matrix and its Applications"),
    (23, "Relation and Functions-II"),
    (24, "Inverse Trigonometric Functions"),
    (25, "Limits and Continuity"),
    (26, "Differentiation"),
    (27, "Differentiation of Trigonometric Functions"),
    (28, "Differentiation of Exponential and Logarithmic Functions"),
    (29, "Application of Derivatives"),
    (30, "Integration"),
    (31, "Definite Integrals"),
    (32, "Differential Equations"),
    (33, "Introduction to 3-D"),
    (34, "Vectors"),
    (35, "Plane"),
    (36, "Straight Line"),
    (37, "Linear Programming"),
    (38, "Mathematical Reasoning"),
]


def main() -> None:
    db = SessionLocal()
    try:
        subject = db.get(Subject, SUBJECT_ID)
        if subject is None:
            raise SystemExit(f"No Subject id={SUBJECT_ID}")
        book = db.scalar(
            select(Book).where(Book.subject_id == SUBJECT_ID).where(Book.ncert_code == BOOK_NCERT_CODE)
        )
        if book is None:
            raise SystemExit(f"No Book with code {BOOK_NCERT_CODE} for subject {SUBJECT_ID}")
        print(f"Subject id={subject.id} {subject.name}; Book id={book.id} {book.title!r}")

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
            f"(total defined {len(CHAPTERS)})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
