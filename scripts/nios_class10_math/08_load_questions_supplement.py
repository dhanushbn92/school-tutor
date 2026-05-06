"""Append a supplemental question batch onto an existing chapter's
question bank. Idempotent — questions whose `text` already exists in
the chapter are skipped.

Usage:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/08_load_questions_supplement.py <chapter_id> <supplement_filename>

Examples:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/08_load_questions_supplement.py 101 ch101_questions_supplement.json
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/08_load_questions_supplement.py 102 ch102_questions_supplement.json

Same JSON shape as the main per-chapter `chXXX_questions.json` file:
    {"_meta": {...}, "questions": [{...}, ...]}
"""

import json
import sys
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


CREATED_BY_ID = 14  # platform.team@anaadi.org

DATA_DIR = Path(__file__).parent / "data"


def _options_payload(q: dict) -> dict | None:
    if q.get("options"):
        return {"choices": list(q["options"])}
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    chapter_id = int(sys.argv[1])
    filename = sys.argv[2]

    payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    questions_data = payload["questions"]

    db = SessionLocal()
    try:
        outcome_map = {
            r.code: r.id
            for r in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == chapter_id)
            ).all()
        }
        existing_texts = {
            r.text
            for r in db.scalars(
                select(Question).where(Question.chapter_id == chapter_id)
            ).all()
        }
        added = 0
        skipped = 0
        for q in questions_data:
            if q["question"] in existing_texts:
                skipped += 1
                continue
            outcome_code = q.get("outcome_code")
            outcome_id = outcome_map.get(outcome_code) if outcome_code else None
            db.add(
                Question(
                    chapter_id=chapter_id,
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
            added += 1
        db.commit()
        print(f"[ok] chapter {chapter_id}: added {added} questions, skipped {skipped} duplicates")

        # Final count by type/Bloom for sanity.
        from collections import Counter
        rows = db.scalars(select(Question).where(Question.chapter_id == chapter_id)).all()
        types = Counter(r.type.value for r in rows)
        blooms = Counter(r.cognitive_level.value for r in rows)
        print(f"     total now: {len(rows)} (objective: {sum(types.get(t, 0) for t in ('MCQ','TRUE_FALSE','FILL_BLANK'))}, subjective: {sum(types.get(t, 0) for t in ('SHORT_ANSWER','LONG_ANSWER'))})")
        print(f"     by type:   {dict(types)}")
        print(f"     by Bloom:  {dict(blooms)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
