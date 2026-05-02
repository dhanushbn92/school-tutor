"""Create Chapter 6 (Quadratic Equations) for NIOS Class 10 Mathematics
(chapter_id=104), populate its full_text from the local data file, then
insert 6 topics with verbatim-style topic_text slices and 8 learning
outcomes.

Idempotent: if the chapter already exists we skip creation and only top
up missing topics / outcomes. Mirrors `04_create_chapter2.py`; we
duplicate rather than parameterise so each chapter loader stays
self-contained and grep-able.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/07_create_chapter6.py
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import (
    BloomLevel,
    Book,
    Chapter,
    LearningOutcome,
    Topic,
)


BOOK_ID = 14  # NIOS Mathematics (Default), subject_id=12
CHAPTER_NUMBER = 6
CHAPTER_TITLE = "QUADRATIC EQUATIONS"

DATA_DIR = Path(__file__).parent / "data"
FULL_TEXT_PATH = DATA_DIR / "ch6_full_text.txt"


# Topic name → (description, slice section header in full_text). The slices
# below are pulled verbatim from the corresponding section of the chapter
# so AI-tutor topic-scoped chats stay grounded in the chapter's prose.
TOPICS: list[dict] = [
    {
        "name": "Introduction To Quadratic Equations",
        "description": (
            "Definition of a quadratic equation a x^2 + b x + c = 0 with a ≠ 0, "
            "the meaning of leading coefficient and constant term, examples "
            "and non-examples, and the idea of a root as an x-value that "
            "makes the polynomial zero."
        ),
        "section_header": "6.1 INTRODUCTION TO QUADRATIC EQUATIONS",
        "next_section_header": "6.2 SOLUTION BY FACTORISATION",
    },
    {
        "name": "Solution By Factorisation",
        "description": (
            "Solving a x^2 + b x + c = 0 by writing the polynomial as a "
            "product of two linear factors via the split-the-middle-term "
            "method, then applying the zero-product property."
        ),
        "section_header": "6.2 SOLUTION BY FACTORISATION",
        "next_section_header": "6.3 SOLUTION BY COMPLETING THE SQUARE",
    },
    {
        "name": "Completing The Square",
        "description": (
            "Solving a quadratic equation by rewriting a x^2 + b x + c as a "
            "perfect square plus a constant; the six-step algorithm and the "
            "identity x^2 + 2 p x = (x + p)^2 − p^2."
        ),
        "section_header": "6.3 SOLUTION BY COMPLETING THE SQUARE",
        "next_section_header": "6.4 QUADRATIC FORMULA (SRIDHARACHARYA FORMULA)",
    },
    {
        "name": "Quadratic Formula",
        "description": (
            "Derivation and use of the Sridharacharya / quadratic formula "
            "x = (−b ± √(b^2 − 4 a c)) / (2 a). Sum and product of the "
            "roots: α + β = −b/a, αβ = c/a; building a quadratic from "
            "given roots."
        ),
        "section_header": "6.4 QUADRATIC FORMULA (SRIDHARACHARYA FORMULA)",
        "next_section_header": "6.5 NATURE OF ROOTS — THE DISCRIMINANT",
    },
    {
        "name": "Nature Of Roots",
        "description": (
            "Using the discriminant D = b^2 − 4 a c to classify the roots: "
            "two distinct real (D > 0), one repeated real (D = 0), no real "
            "(D < 0). Also rational vs irrational and finding a missing "
            "parameter so the equation has equal roots."
        ),
        "section_header": "6.5 NATURE OF ROOTS — THE DISCRIMINANT",
        "next_section_header": "6.6 WORD PROBLEMS ON QUADRATIC EQUATIONS",
    },
    {
        "name": "Word Problems",
        "description": (
            "Translating short word problems (number relations, geometry, "
            "speed–time, ages) into quadratic equations and solving them; "
            "discipline of rejecting roots that contradict the physical "
            "situation."
        ),
        "section_header": "6.6 WORD PROBLEMS ON QUADRATIC EQUATIONS",
        "next_section_header": "SUMMARY",
    },
]


# Outcome code prefix uses chapter abbreviation "QE" (Quadratic Equations).
OUTCOMES: list[dict] = [
    {
        "code": "10-NIOS-MATH-QE-01",
        "topic_name": "Introduction To Quadratic Equations",
        "bloom": BloomLevel.REMEMBER,
        "description": (
            "Identify a quadratic equation in one variable; state the standard "
            "form a x^2 + b x + c = 0 with a ≠ 0 and pick out a, b, c from a "
            "given equation."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-02",
        "topic_name": "Introduction To Quadratic Equations",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Bring an equation to the standard form a x^2 + b x + c = 0 by "
            "expanding products, clearing fractions or rationalising, and "
            "verify whether a candidate value is a root."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-03",
        "topic_name": "Solution By Factorisation",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Solve a quadratic equation by factorisation, splitting the middle "
            "term using two numbers whose product is a × c and whose sum is b, "
            "then applying the zero-product property."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-04",
        "topic_name": "Completing The Square",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Solve a quadratic equation by completing the square, applying the "
            "identity x^2 + 2 p x = (x + p)^2 − p^2 and the six-step algorithm."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-05",
        "topic_name": "Quadratic Formula",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Solve a quadratic equation using the quadratic (Sridharacharya) "
            "formula x = (−b ± √(b^2 − 4 a c)) / (2 a) and report both roots "
            "in simplest form."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-06",
        "topic_name": "Nature Of Roots",
        "bloom": BloomLevel.ANALYZE,
        "description": (
            "Compute the discriminant D = b^2 − 4 a c and use it to classify "
            "the roots as real-and-distinct, real-and-equal, or non-real; "
            "distinguish rational from irrational real roots."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-07",
        "topic_name": "Quadratic Formula",
        "bloom": BloomLevel.EVALUATE,
        "description": (
            "Use the relations α + β = −b/a and α β = c/a to verify a pair of "
            "computed roots and to construct a quadratic equation given its "
            "roots, or to find a missing coefficient given the nature of the "
            "roots."
        ),
    },
    {
        "code": "10-NIOS-MATH-QE-08",
        "topic_name": "Word Problems",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Model a short word problem (number relations, geometry, speed–"
            "time, ages) as a quadratic equation, solve it, and reject any "
            "root that contradicts the physical situation."
        ),
    },
]


def _slice(full_text: str, start_header: str, end_header: str) -> str:
    """Return text between start_header (inclusive) and end_header (exclusive),
    trimmed. Used to build per-topic full_text slices."""
    i = full_text.index(start_header)
    j = full_text.index(end_header, i + 1)
    return full_text[i:j].strip()


def main() -> None:
    full_text = FULL_TEXT_PATH.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

    db = SessionLocal()
    try:
        # 1. Chapter --------------------------------------------------------
        chapter = db.scalar(
            select(Chapter).where(
                Chapter.book_id == BOOK_ID,
                Chapter.chapter_number == CHAPTER_NUMBER,
            )
        )
        if chapter is None:
            chapter = Chapter(
                book_id=BOOK_ID,
                chapter_number=CHAPTER_NUMBER,
                title=CHAPTER_TITLE,
                full_text=full_text,
                content_hash=content_hash,
                imported_at=datetime.now(timezone.utc),
            )
            db.add(chapter)
            db.flush()
            print(f"[ok] created chapter id={chapter.id} title={CHAPTER_TITLE!r}")
        else:
            print(f"[skip] chapter exists: id={chapter.id}")
            if chapter.content_hash != content_hash:
                chapter.full_text = full_text
                chapter.content_hash = content_hash
                print("[ok]   updated chapter full_text (hash changed)")

        # 2. Topics + verbatim slices --------------------------------------
        existing_topic_names = {
            t.name
            for t in db.scalars(
                select(Topic).where(Topic.chapter_id == chapter.id)
            ).all()
        }
        topics_added = 0
        for spec in TOPICS:
            if spec["name"] in existing_topic_names:
                continue
            slice_text = _slice(
                full_text, spec["section_header"], spec["next_section_header"]
            )
            db.add(
                Topic(
                    chapter_id=chapter.id,
                    name=spec["name"],
                    description=spec["description"],
                    full_text=slice_text,
                )
            )
            topics_added += 1
        db.flush()
        print(f"[ok] inserted {topics_added} topics (skipped {len(TOPICS) - topics_added} dupes)")

        # 3. Learning outcomes ---------------------------------------------
        topic_id_by_name = {
            t.name: t.id
            for t in db.scalars(select(Topic).where(Topic.chapter_id == chapter.id)).all()
        }
        existing_codes = {
            r.code
            for r in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == chapter.id)
            ).all()
        }
        outcomes_added = 0
        for o in OUTCOMES:
            if o["code"] in existing_codes:
                continue
            db.add(
                LearningOutcome(
                    chapter_id=chapter.id,
                    topic_id=topic_id_by_name.get(o["topic_name"]),
                    code=o["code"],
                    description=o["description"],
                    bloom_level=o["bloom"],
                )
            )
            outcomes_added += 1
        db.commit()
        print(f"[ok] inserted {outcomes_added} learning outcomes (skipped {len(OUTCOMES) - outcomes_added} dupes)")

        # 4. Final report ---------------------------------------------------
        topics = db.scalars(select(Topic).where(Topic.chapter_id == chapter.id).order_by(Topic.id)).all()
        print()
        print("Topics now on chapter:")
        for t in topics:
            print(f"  id={t.id} name={t.name!r} slice_len={len(t.full_text or '')}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
