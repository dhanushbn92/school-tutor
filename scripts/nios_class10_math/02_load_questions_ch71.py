"""Load NIOS Class 10 Math, Chapter 1 (Number Systems) question bank
from scripts/nios_class10_math/data/ch71_questions.json into the
`questions` table.

Resolves outcome_code → outcome_id by looking up LearningOutcome rows
on the chapter. Sets created_by_id to the platform admin (id=14),
status=APPROVED so they're immediately bank-worthy. Idempotent: only
inserts questions whose `text` is not already present for the chapter.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/02_load_questions_ch71.py
"""

import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
)


CHAPTER_ID = 71
CREATED_BY_ID = 14  # platform.team@anaadi.org

DATA_PATH = Path(__file__).parent / "data" / "ch71_questions.json"


def _options_payload(q: dict) -> dict | None:
    """Match the shape used by the worker: {"choices": [...]}."""
    if q.get("options"):
        return {"choices": list(q["options"])}
    return None


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    questions_data = payload["questions"]

    db = SessionLocal()
    try:
        outcome_map = {
            r.code: r.id
            for r in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)
            ).all()
        }
        existing_texts = {
            r.text
            for r in db.scalars(
                select(Question).where(Question.chapter_id == CHAPTER_ID)
            ).all()
        }

        inserted = 0
        skipped = 0
        unresolved: set[str] = set()

        for q in questions_data:
            if q["question"] in existing_texts:
                skipped += 1
                continue

            outcome_code = q.get("outcome_code")
            outcome_id = outcome_map.get(outcome_code) if outcome_code else None
            if outcome_code and outcome_id is None:
                unresolved.add(outcome_code)

            db.add(
                Question(
                    chapter_id=CHAPTER_ID,
                    topic_id=q.get("topic_id"),
                    outcome_id=outcome_id,
                    outcome_code=outcome_code,
                    type=QuestionType(q["type"]),
                    difficulty=QuestionDifficulty(q["difficulty"]),
                    status=QuestionStatus.APPROVED,
                    cognitive_level=BloomLevel(q["cognitive_level"].lower()),
                    text=q["question"],
                    options=_options_payload(q),
                    correct_answer=q["answer"],
                    explanation=q.get("explanation"),
                    marks=int(q.get("marks", 1)),
                    created_by_id=CREATED_BY_ID,
                )
            )
            inserted += 1

        db.commit()
        print(f"Inserted {inserted} questions (skipped {skipped} dupes).")
        if unresolved:
            print(f"WARNING: unresolved outcome_codes: {sorted(unresolved)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
