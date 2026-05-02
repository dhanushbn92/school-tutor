"""Create Chapter 2 (Exponents and Radicals) for NIOS Class 10
Mathematics, populate its full_text from the local data file, then
insert 6 topics with verbatim-style topic_text slices and 8 learning
outcomes.

Idempotent: if the chapter already exists we skip creation and only
top up missing topics / outcomes.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/04_create_chapter2.py
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
CHAPTER_NUMBER = 2
CHAPTER_TITLE = "EXPONENTS AND RADICALS"

DATA_DIR = Path(__file__).parent / "data"
FULL_TEXT_PATH = DATA_DIR / "ch2_full_text.txt"


# Topic name → (description, slice section header in full_text). The slices
# below are pulled verbatim from the corresponding section of the
# chapter so that AI-tutor topic-scoped chats stay grounded in the
# chapter's prose. The slicer in production calls an LLM to do this;
# here we slice by hand, using the section headings as boundaries.
TOPICS: list[dict] = [
    {
        "name": "Positive Integral Exponents",
        "description": (
            "Definition of a^n for a positive integer n, the base–exponent "
            "vocabulary, and the five basic laws of exponents (product, "
            "quotient, power-of-power, power-of-product, power-of-quotient)."
        ),
        "section_header": "2.1 POSITIVE INTEGRAL EXPONENTS",
        "next_section_header": "2.2 ZERO AND NEGATIVE INTEGRAL EXPONENTS",
    },
    {
        "name": "Zero And Negative Integral Exponents",
        "description": (
            "Extending exponents to 0 and negative integers so the laws of "
            "exponents continue to hold: a^0 = 1, a^(−n) = 1/a^n."
        ),
        "section_header": "2.2 ZERO AND NEGATIVE INTEGRAL EXPONENTS",
        "next_section_header": "2.3 RATIONAL EXPONENTS",
    },
    {
        "name": "Rational Exponents",
        "description": (
            "Extension to rational exponents via n-th roots: a^(m/n) = n√(a^m). "
            "The five laws extend to rational exponents for positive bases."
        ),
        "section_header": "2.3 RATIONAL EXPONENTS",
        "next_section_header": "2.4 RADICALS AND SURDS",
    },
    {
        "name": "Radicals And Surds",
        "description": (
            "The radical sign and n-th roots, vocabulary of surds (order, "
            "pure vs mixed, like vs unlike), and the laws of radicals."
        ),
        "section_header": "2.4 RADICALS AND SURDS",
        "next_section_header": "2.5 SIMPLIFICATION OF RADICALS",
    },
    {
        "name": "Simplification Of Radicals",
        "description": (
            "When a radical is in simplified form, addition / subtraction of "
            "like surds, multiplication and division of surds (same index "
            "and via common index)."
        ),
        "section_header": "2.5 SIMPLIFICATION OF RADICALS",
        "next_section_header": "2.6 RATIONALISATION OF DENOMINATORS",
    },
    {
        "name": "Rationalisation Of Denominators",
        "description": (
            "Removing radicals from a denominator: multiplying by √a for a "
            "single-term surd denominator, and by the conjugate for a "
            "binomial surd denominator."
        ),
        "section_header": "2.6 RATIONALISATION OF DENOMINATORS",
        "next_section_header": "SUMMARY",
    },
]


# Outcome code prefix uses chapter abbreviation "ER" (Exponents & Radicals).
# Each outcome maps to a topic by name (resolved at runtime).
OUTCOMES: list[dict] = [
    {
        "code": "10-NIOS-MATH-ER-01",
        "topic_name": "Positive Integral Exponents",
        "bloom": BloomLevel.REMEMBER,
        "description": (
            "Recall the meaning of a^n for a positive integer n and identify "
            "the base, exponent and value of a given expression."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-02",
        "topic_name": "Positive Integral Exponents",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "State and apply the five laws of exponents (product, quotient, "
            "power of a power, power of a product, power of a quotient) for "
            "positive integral exponents."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-03",
        "topic_name": "Zero And Negative Integral Exponents",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Justify why a^0 = 1 and a^(−n) = 1/a^n using the product law "
            "of exponents, and evaluate expressions with zero or negative "
            "integral exponents."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-04",
        "topic_name": "Rational Exponents",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Convert between rational-exponent form a^(m/n) and radical "
            "form n√(a^m), and evaluate simple rational-exponent "
            "expressions for positive bases."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-05",
        "topic_name": "Radicals And Surds",
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Identify the order, radicand, and rational coefficient of a "
            "given radical; classify a radical as a surd / not a surd, and "
            "as pure / mixed, like / unlike."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-06",
        "topic_name": "Simplification Of Radicals",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Simplify a given radical expression by removing perfect-power "
            "factors from the radicand, combine like surds, and apply the "
            "common-index technique to surds with different indices."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-07",
        "topic_name": "Rationalisation Of Denominators",
        "bloom": BloomLevel.APPLY,
        "description": (
            "Rationalise denominators of the form √a or a ± b√c by "
            "multiplying by an appropriate rationalising factor (the surd "
            "itself or the conjugate) and reduce to standard form."
        ),
    },
    {
        "code": "10-NIOS-MATH-ER-08",
        "topic_name": "Rationalisation Of Denominators",
        "bloom": BloomLevel.EVALUATE,
        "description": (
            "Justify the choice of conjugate as the rationalising factor "
            "for a binomial surd denominator using the difference-of-squares "
            "identity (a + b)(a − b) = a² − b²."
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
            # Refresh full_text in case the data file was edited.
            if chapter.content_hash != content_hash:
                chapter.full_text = full_text
                chapter.content_hash = content_hash
                print(f"[ok]   updated chapter full_text (hash changed)")

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
