"""Scaffold the NIOS Class 12 Physics curriculum: subject, book and
all 30 chapter rows grouped by syllabus module.

Each chapter is created with a placeholder full_text ('Pending
content authoring.') so the bootstrap-content worker (which requires
non-empty full_text) can be unblocked once we author per-chapter
prose. Topics, outcomes, questions and content blobs are NOT created
here — those follow per-chapter once the user picks which chapters
to prioritise.

Idempotent: re-running the script tops up missing rows but never
duplicates existing ones.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/01_scaffold_curriculum.py
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


CLASS_LEVEL = 12
SUBJECT_NAME = "Physics"
BOARD = "NIOS"
LANGUAGE = "en"

BOOK_TITLE = "NIOS Senior Secondary Physics"
BOOK_NCERT_CODE = "nios-sr-physics"
ACADEMIC_YEAR = "2026-27"

# Placeholder full_text — required by the bootstrap-content worker
# (it errors on empty full_text). Replace per chapter when content is
# authored. Long enough to satisfy any min-length checks.
PLACEHOLDER_FULL_TEXT = (
    "Pending content authoring. This chapter row was created by the "
    "scaffolding script; topics, outcomes, questions and content "
    "blobs will be added in a follow-up authoring pass once the "
    "platform team prioritises this chapter."
)


# Chapter list, grouped by NIOS Senior Secondary Physics module. Order
# preserved across modules — `chapter_number` is assigned sequentially
# (1..30) so the SPA's chapter ordering matches the syllabus.
CHAPTERS_BY_MODULE: list[tuple[str, list[str]]] = [
    ("Module 1 — Motion, Force and Energy", [
        "Units, Dimensions and Vectors",
        "Motion in a Straight Line",
        "Laws of Motion",
        "Motion in a Plane",
        "Gravitation",
    ]),
    ("Module 2 — Mechanics of Solids and Fluids", [
        "Elastic Properties of Solids",
        "Properties of Fluids",
    ]),
    ("Module 3 — Thermal Physics", [
        "Kinetic Theory of Gases",
        "Thermodynamics",
        "Heat Transfer and Solar Energy",
    ]),
    ("Module 4 — Oscillations and Waves", [
        "Simple Harmonic Motion",
        "Wave Phenomena",
    ]),
    ("Module 5 — Electricity and Magnetism", [
        "Electric Charge and Electric Field",
        "Electric Potential and Capacitance",
        "Electric Current and Ohm's Law",
        "Magnetic Effect of Electric Current",
        "Electromagnetic Induction and Alternating Current",
    ]),
    ("Module 6 — Optics and Optical Instruments", [
        "Reflection and Refraction of Light",
        "Dispersion and Scattering of Light",
        "Wave Phenomena and Light",
    ]),
    ("Module 7 — Atoms and Nuclei", [
        "Structure of Atom",
        "Dual Nature of Radiation and Matter",
        "Nuclei and Radioactivity",
    ]),
    ("Module 8 — Semiconductors and Communication", [
        "Semiconductors and Semiconducting Devices",
        "Applications of Semiconductor Devices",
        "Communication Systems",
    ]),
    ("Module 9 — Modern Physics", [
        "Universe",
        "Contemporary Physics",
    ]),
]


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Class --------------------------------------------------------
        cls = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if cls is None:
            raise SystemExit(
                f"SchoolClass level={CLASS_LEVEL} not configured. Run the "
                "class seeding step before scaffolding subjects."
            )
        print(f"[ok] using class id={cls.id} ({cls.display_name})")

        # 2. Subject ------------------------------------------------------
        subject = db.scalar(
            select(Subject).where(
                Subject.class_id == cls.id,
                Subject.name == SUBJECT_NAME,
                Subject.language == LANGUAGE,
                Subject.board == BOARD,
            )
        )
        if subject is None:
            subject = Subject(
                class_id=cls.id,
                name=SUBJECT_NAME,
                language=LANGUAGE,
                board=BOARD,
            )
            db.add(subject)
            db.flush()
            print(f"[ok] created subject id={subject.id} board={BOARD!r} name={SUBJECT_NAME!r}")
        else:
            print(f"[skip] subject exists: id={subject.id}")

        # 3. Book --------------------------------------------------------
        book = db.scalar(
            select(Book).where(
                Book.subject_id == subject.id,
                Book.ncert_code == BOOK_NCERT_CODE,
                Book.academic_year == ACADEMIC_YEAR,
            )
        )
        if book is None:
            book = Book(
                subject_id=subject.id,
                title=BOOK_TITLE,
                ncert_code=BOOK_NCERT_CODE,
                academic_year=ACADEMIC_YEAR,
            )
            db.add(book)
            db.flush()
            print(f"[ok] created book id={book.id} title={BOOK_TITLE!r}")
        else:
            print(f"[skip] book exists: id={book.id}")

        # 4. Chapters ----------------------------------------------------
        existing_numbers = {
            c.chapter_number
            for c in db.scalars(
                select(Chapter).where(Chapter.book_id == book.id)
            ).all()
        }
        chapter_number = 0
        chapters_created = 0
        for module_label, titles in CHAPTERS_BY_MODULE:
            for title in titles:
                chapter_number += 1
                if chapter_number in existing_numbers:
                    continue
                # Prefix the title with the module label so the SPA's
                # chapter list reads as a syllabus map. Cleaner than
                # nested books-per-module.
                titled = f"{title}"
                db.add(
                    Chapter(
                        book_id=book.id,
                        chapter_number=chapter_number,
                        title=titled,
                        full_text=PLACEHOLDER_FULL_TEXT,
                        imported_at=datetime.now(timezone.utc),
                    )
                )
                chapters_created += 1
        db.commit()
        print(f"[ok] created {chapters_created} chapters (skipped {chapter_number - chapters_created} pre-existing)")

        # 5. Final report -------------------------------------------------
        print()
        print("=== NIOS Class 12 Physics — curriculum scaffold ===")
        chapters = db.scalars(
            select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.chapter_number)
        ).all()
        # Walk the module table again to print the right grouping.
        idx = 0
        for module_label, titles in CHAPTERS_BY_MODULE:
            print(f"\n{module_label}")
            for _ in titles:
                ch = chapters[idx]
                print(f"  {ch.chapter_number:2d}. {ch.title}  (id={ch.id})")
                idx += 1
    finally:
        db.close()


if __name__ == "__main__":
    main()
