"""Scaffold the remaining NIOS Class 10 Mathematics chapters (3-26)
in book id=14, grouped by syllabus module. Idempotent: existing
chapters are skipped, never overwritten.

Current state assumed at start: chapters 1 (Number Systems) and 2
(Exponents and Radicals) already onboarded in full earlier in the
session. This script creates the 24 remaining chapter rows so the
full curriculum becomes visible in the SPA. Each new chapter gets a
placeholder full_text so the bootstrap-content worker doesn't error
on empty text — when the actual chapter is authored, that placeholder
is replaced.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/06_scaffold_remaining_chapters.py
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Chapter


BOOK_ID = 14

PLACEHOLDER_FULL_TEXT = (
    "Pending content authoring. This chapter row was created by the "
    "scaffolding script; topics, outcomes, questions and content "
    "blobs will be added in a follow-up authoring pass."
)


# Standard NIOS Senior Secondary Mathematics syllabus, grouped by module.
# Order is consecutive — chapter_number is assigned in sequence.
CHAPTERS_BY_MODULE: list[tuple[str, list[str]]] = [
    ("Module 1 — Algebra", [
        "Number Systems",                         # ch1 - DONE
        "Exponents and Radicals",                 # ch2 - DONE
        "Algebraic Expressions and Polynomials",  # ch3
        "Special Products and Factorisation",     # ch4
        "Linear Equations",                       # ch5
        "Quadratic Equations",                    # ch6
        "Arithmetic Progressions",                # ch7
    ]),
    ("Module 2 — Commercial Mathematics", [
        "Percentage and Its Applications",        # ch8
        "Instalment Buying",                      # ch9
    ]),
    ("Module 3 — Geometry", [
        "Lines and Angles",                       # ch10
        "Congruence of Triangles",                # ch11
        "Concurrent Lines",                       # ch12
        "Quadrilaterals",                         # ch13
        "Similarity of Triangles",                # ch14
        "Circles",                                # ch15
        "Angles in a Circle",                     # ch16
        "Secants, Tangents and Their Properties", # ch17
        "Constructions",                          # ch18
    ]),
    ("Module 4 — Mensuration", [
        "Perimeters and Areas of Plane Figures",  # ch19
        "Surface Areas and Volumes of Solid Figures",  # ch20
    ]),
    ("Module 5 — Trigonometry", [
        "Trigonometric Ratios of an Acute Angle", # ch21
        "Trigonometric Ratios of Some Special Angles",  # ch22
        "Some Applications of Trigonometry",      # ch23
    ]),
    ("Module 6 — Statistics and Probability", [
        "Data and Their Representations",         # ch24
        "Measures of Central Tendency",           # ch25
        "Probability",                            # ch26
    ]),
]


def main() -> None:
    db = SessionLocal()
    try:
        existing = {
            c.chapter_number
            for c in db.scalars(
                select(Chapter).where(Chapter.book_id == BOOK_ID)
            ).all()
        }

        chapter_number = 0
        created = 0
        for module_label, titles in CHAPTERS_BY_MODULE:
            for title in titles:
                chapter_number += 1
                if chapter_number in existing:
                    continue
                db.add(
                    Chapter(
                        book_id=BOOK_ID,
                        chapter_number=chapter_number,
                        title=title,
                        full_text=PLACEHOLDER_FULL_TEXT,
                        imported_at=datetime.now(timezone.utc),
                    )
                )
                created += 1
        db.commit()
        print(f"[ok] created {created} new chapters (skipped {chapter_number - created} pre-existing)")

        # Final report.
        chapters = db.scalars(
            select(Chapter).where(Chapter.book_id == BOOK_ID).order_by(Chapter.chapter_number)
        ).all()
        idx = 0
        print()
        print("=== NIOS Class 10 Mathematics — full curriculum ===")
        for module_label, titles in CHAPTERS_BY_MODULE:
            print(f"\n{module_label}")
            for _ in titles:
                ch = chapters[idx]
                done_marker = "[*]" if (ch.full_text or "").strip() != PLACEHOLDER_FULL_TEXT else "[ ]"
                print(f"  {done_marker} {ch.chapter_number:2d}. {ch.title}  (id={ch.id})")
                idx += 1
        print()
        print("[*] = chapter has real content (not placeholder)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
