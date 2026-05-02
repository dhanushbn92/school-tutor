"""Create Chapter 7 (Arithmetic Progressions) for NIOS Class 10
Mathematics (chapter_id=105), populate its full_text from the local data
file, then insert 6 topics with verbatim-style topic_text slices and 8
learning outcomes.

Idempotent: if the chapter already exists we skip creation and only top
up missing topics / outcomes. Mirrors `04_create_chapter2.py` and
`07_create_chapter6.py`; we duplicate rather than parameterise so each
chapter loader stays self-contained and grep-able.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/11_create_chapter7.py
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
CHAPTER_NUMBER = 7
CHAPTER_TITLE = "ARITHMETIC PROGRESSIONS"

DATA_DIR = Path(__file__).parent / "data"
FULL_TEXT_PATH = DATA_DIR / "ch7_full_text.txt"


# Topic name → (description, slice section header in full_text). The slices
# below are pulled verbatim from the corresponding section of the chapter
# so AI-tutor topic-scoped chats stay grounded in the chapter's prose.
TOPICS: list[dict] = [
    {
        "name": "Sequences And Series",
        "description": (
            "Definition of a sequence (an ordered list of numbers a_1, a_2, "
            "a_3, …) and a series (the sum of a sequence). Notation S_n for "
            "the partial sum of the first n terms; examples of finite, "
            "infinite, alternating, and recursively defined sequences."
        ),
        "section_header": "7.1 SEQUENCES AND SERIES",
        "next_section_header": "7.2 ARITHMETIC PROGRESSION — DEFINITION",
    },
    {
        "name": "Arithmetic Progression Definition",
        "description": (
            "An arithmetic progression (AP) is a sequence whose successive "
            "terms differ by a constant d, the common difference. First term "
            "a; the AP is a, a + d, a + 2 d, … . How to test whether a given "
            "sequence is an AP."
        ),
        "section_header": "7.2 ARITHMETIC PROGRESSION — DEFINITION",
        "next_section_header": "7.3 N-TH TERM OF AN AP",
    },
    {
        "name": "Nth Term Of An Ap",
        "description": (
            "Derivation and use of the n-th-term formula a_n = a + (n − 1) d. "
            "Standard problems: find a specific term, find the AP given two "
            "terms, find which term equals a given value, count three-digit "
            "multiples of a number."
        ),
        "section_header": "7.3 N-TH TERM OF AN AP",
        "next_section_header": "7.4 SUM OF THE FIRST N TERMS OF AN AP",
    },
    {
        "name": "Sum Of An Ap",
        "description": (
            "Derivation (Gauss-style pairing) and use of S_n = (n/2)(2 a + "
            "(n − 1) d) = (n/2)(a + l). Standard particular sums: 1 + 2 + … "
            "+ n = n(n + 1)/2; 1 + 3 + … + (2 n − 1) = n^2. Recovering a_n "
            "from S_n via a_n = S_n − S_(n − 1)."
        ),
        "section_header": "7.4 SUM OF THE FIRST N TERMS OF AN AP",
        "next_section_header": "7.5 ARITHMETIC MEAN",
    },
    {
        "name": "Arithmetic Mean",
        "description": (
            "Definition of the arithmetic mean of two numbers, AM = (a + b)/2. "
            "Three numbers in AP iff the middle is the AM of the outer two. "
            "Inserting n arithmetic means between a and b: common difference "
            "d = (b − a)/(n + 1)."
        ),
        "section_header": "7.5 ARITHMETIC MEAN",
        "next_section_header": "7.6 WORD PROBLEMS ON ARITHMETIC PROGRESSIONS",
    },
    {
        "name": "Ap Word Problems",
        "description": (
            "Translating short word problems (savings, ladder rungs, theatre "
            "seating, instalment-loan repayments) into AP set-ups; choosing "
            "between the n-th-term and sum formulae; rejecting non-natural-"
            "number values of n."
        ),
        "section_header": "7.6 WORD PROBLEMS ON ARITHMETIC PROGRESSIONS",
        "next_section_header": "SUMMARY",
    },
]


# Outcome code prefix uses chapter abbreviation "AP" (Arithmetic Progressions).
OUTCOMES: list[dict] = [
    {
        "code": "10-NIOS-MATH-AP-01",
        "topic_name": "Sequences And Series",
        "bloom": BloomLevel.REMEMBER,
        "description": (
            "Define a sequence and a series; identify the first few terms "
            "given a rule for a_n, and the partial sum S_n given a sequence."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-02",
        "topic_name": "Arithmetic Progression Definition",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "State the definition of an arithmetic progression and its common "
            "difference; test whether a given sequence is an AP by computing "
            "successive differences."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-03",
        "topic_name": "Nth Term Of An Ap",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Apply a_n = a + (n − 1) d to find a specified term of an AP, the "
            "first term or common difference given two terms, or the position "
            "of a known term."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-04",
        "topic_name": "Nth Term Of An Ap",
        "bloom": BloomLevel.ANALYZE,
        "description": (
            "Determine how many terms of a given AP lie in a specified range, "
            "e.g. how many three-digit numbers are divisible by a given "
            "integer, by setting up and solving a_n = a + (n − 1) d."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-05",
        "topic_name": "Sum Of An Ap",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Apply S_n = (n/2)(2 a + (n − 1) d) and S_n = (n/2)(a + l) to "
            "compute the sum of the first n terms of an AP, choosing the "
            "appropriate form for the data given."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-06",
        "topic_name": "Sum Of An Ap",
        "bloom": BloomLevel.EVALUATE,
        "description": (
            "Recover the n-th term of an AP from a given S_n via a_n = S_n − "
            "S_(n−1), and verify the result against the AP formula a + "
            "(n − 1) d."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-07",
        "topic_name": "Arithmetic Mean",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Compute the arithmetic mean of two numbers; insert n arithmetic "
            "means between two given numbers using d = (b − a)/(n + 1)."
        ),
    },
    {
        "code": "10-NIOS-MATH-AP-08",
        "topic_name": "Ap Word Problems",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Model a short word problem (savings, ladder rungs, seating, loan "
            "instalments) as an AP, decide whether to apply the n-th-term or "
            "the sum formula, solve, and reject any non-natural-number value "
            "of n."
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
