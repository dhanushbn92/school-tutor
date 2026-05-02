"""Insert 8 learning outcomes for NIOS Class 10 Math, Chapter 1 (Number
Systems, chapter_id=71). Idempotent — checks UniqueConstraint on
(chapter_id, code) and skips dupes.

Run:
    .venv/Scripts/python.exe scripts/nios_class10_math/01_load_outcomes_ch71.py
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, LearningOutcome


CHAPTER_ID = 71

# Topic IDs (from the inspection done earlier)
T_NATURAL = 91
T_WHOLE = 92
T_INTEGERS = 93
T_RATIONAL = 94
T_OPS_RATIONAL = 95
T_DECIMAL = 96


OUTCOMES: list[dict] = [
    {
        "code": "10-NIOS-MATH-NS-01",
        "topic_id": T_NATURAL,
        "bloom": BloomLevel.REMEMBER,
        "description": (
            "Identify natural numbers, recall that they begin from 1 and are "
            "denoted by N, and place them on the number line."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-02",
        "topic_id": T_WHOLE,
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Distinguish whole numbers (W = N ∪ {0}) from natural numbers and "
            "explain the role of zero on the number line."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-03",
        "topic_id": T_INTEGERS,
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Represent integers (positive, negative, and zero) on the number "
            "line and order them using <, >, ≤, ≥ relations."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-04",
        "topic_id": T_RATIONAL,
        "bloom": BloomLevel.UNDERSTAND,
        "description": (
            "Express a number in p/q form where p and q are integers and q ≠ 0, "
            "and recognise equivalent rational numbers."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-05",
        "topic_id": T_RATIONAL,
        "bloom": BloomLevel.APPLY,
        "description": (
            "Compare and order rational numbers and locate them on the number "
            "line, including fractions with unlike denominators."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-06",
        "topic_id": T_OPS_RATIONAL,
        "bloom": BloomLevel.APPLY,
        "description": (
            "Perform addition, subtraction, multiplication and division on "
            "rational numbers and apply closure, commutative and associative "
            "properties to simplify expressions."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-07",
        "topic_id": T_DECIMAL,
        "bloom": BloomLevel.ANALYZE,
        "description": (
            "Convert a rational number to its terminating or non-terminating "
            "recurring decimal form and convert recurring decimals back into "
            "p/q form."
        ),
    },
    {
        "code": "10-NIOS-MATH-NS-08",
        "topic_id": T_DECIMAL,
        "bloom": BloomLevel.EVALUATE,
        "description": (
            "Justify why every rational number has either a terminating or a "
            "non-terminating recurring decimal expansion by analysing the "
            "prime factorisation of its denominator."
        ),
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        existing = {
            row.code
            for row in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)
            ).all()
        }
        inserted = 0
        skipped = 0
        for o in OUTCOMES:
            if o["code"] in existing:
                skipped += 1
                continue
            db.add(
                LearningOutcome(
                    chapter_id=CHAPTER_ID,
                    topic_id=o["topic_id"],
                    code=o["code"],
                    description=o["description"],
                    bloom_level=o["bloom"],
                )
            )
            inserted += 1
        db.commit()
        print(f"Inserted {inserted} learning outcomes (skipped {skipped} dupes).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
