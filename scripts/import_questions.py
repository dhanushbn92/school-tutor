"""Bulk-import hand-authored questions into the global question bank.

Validates each question against a strict Pydantic schema mirroring the
existing LLM `WorksheetQuestion`, then writes APPROVED Question rows.
Optionally maps `outcome_code` -> `outcome_id` automatically.

JSON file shape:
{
  "chapter_id": 58,
  "questions": [
    {
      "type": "MCQ",
      "difficulty": "EASY",
      "cognitive_level": "remember",
      "text": "...",
      "options": ["A","B","C","D"],
      "answer": "B",
      "explanation": "...",
      "marks": 1,
      "outcome_code": "6-SCI-WOS-01"
    },
    ...
  ]
}

Usage:
    .venv/Scripts/python.exe -m scripts.import_questions \\
        --json-path tmp/ch01_questions.json
    .venv/Scripts/python.exe -m scripts.import_questions \\
        --json-path tmp/ch01_questions.json --replace-approved
"""
import argparse
import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
)
from app.models.school import User, UserRole


log = logging.getLogger(__name__)


class _ImportedQuestion(BaseModel):
    type: QuestionType
    difficulty: QuestionDifficulty
    cognitive_level: BloomLevel
    text: str = Field(min_length=5, max_length=2000)
    options: list[str] | None = None
    answer: str = Field(min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=2000)
    explanation_rich: dict | None = Field(
        default=None,
        description=(
            "Optional structured rich explanation. Shape: "
            "{'blocks': [{'type':'text'|'list'|'mind_map'|'flow_diagram', ...}, ...]}."
        ),
    )
    auto_grade: dict | None = Field(
        default=None,
        description=(
            "Optional keyword rubric for auto-grading subjective answers. Shape: "
            "{'method':'keywords','min_words':int,'groups':[{'label','any_of':[...],'marks':float}]}."
        ),
    )
    marks: int = Field(ge=1, le=10)
    outcome_code: str | None = None

    @model_validator(mode="after")
    def _check_options(self) -> "_ImportedQuestion":
        if self.type == QuestionType.MCQ:
            if not self.options or len(self.options) != 4:
                raise ValueError("MCQ questions must have exactly 4 options.")
            if self.answer not in self.options:
                raise ValueError(f"MCQ answer {self.answer!r} must be one of the options.")
        elif self.type == QuestionType.TRUE_FALSE:
            if not self.options or {opt.lower() for opt in self.options} != {"true", "false"}:
                raise ValueError("TRUE_FALSE options must be ['True', 'False'].")
        return self


class _ImportFile(BaseModel):
    chapter_id: int
    questions: list[_ImportedQuestion] = Field(min_length=1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-path", required=True)
    parser.add_argument("--platform-admin-email", default="platform.team@anaadi.org")
    parser.add_argument(
        "--replace-approved",
        action="store_true",
        help="Delete all existing APPROVED questions for this chapter before import.",
    )
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        raw = json.load(f)
    file = _ImportFile.model_validate(raw)

    with SessionLocal() as db:
        admin = db.scalar(
            select(User).where(
                User.email == args.platform_admin_email,
                User.role == UserRole.PLATFORM_ADMIN,
            )
        )
        if admin is None:
            raise SystemExit(f"Platform admin {args.platform_admin_email} not found.")

        outcome_map: dict[str, int] = {
            row.code: row.id
            for row in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == file.chapter_id)
            )
        }

        if args.replace_approved:
            # Retire (not delete) so existing assessment_questions FKs stay valid.
            n = db.execute(
                update(Question)
                .where(
                    Question.chapter_id == file.chapter_id,
                    Question.status == QuestionStatus.APPROVED,
                )
                .values(status=QuestionStatus.RETIRED)
            ).rowcount
            log.info("retired %s existing APPROVED questions for ch %s", n, file.chapter_id)

        existing_norms = {
            _norm(q.text)
            for q in db.scalars(
                select(Question).where(
                    Question.chapter_id == file.chapter_id,
                    Question.status == QuestionStatus.APPROVED,
                )
            )
        }

        kept = 0
        skipped = 0
        for q in file.questions:
            norm = _norm(q.text)
            if norm in existing_norms:
                log.info("dedup: skipping %r", q.text[:50])
                skipped += 1
                continue
            existing_norms.add(norm)
            outcome_id = outcome_map.get(q.outcome_code) if q.outcome_code else None
            options_payload = {"choices": list(q.options)} if q.options else None
            row = Question(
                chapter_id=file.chapter_id,
                topic_id=None,
                outcome_id=outcome_id,
                outcome_code=q.outcome_code,
                type=q.type,
                difficulty=q.difficulty,
                cognitive_level=q.cognitive_level,
                status=QuestionStatus.APPROVED,
                text=q.text,
                options=options_payload,
                correct_answer=q.answer,
                explanation=q.explanation,
                explanation_rich=q.explanation_rich,
                auto_grade=q.auto_grade,
                marks=q.marks,
                created_by_id=admin.id,
                reviewed_by_id=admin.id,
            )
            db.add(row)
            kept += 1
        db.commit()

    print(f"Chapter {file.chapter_id}: imported {kept} new questions ({skipped} duplicates skipped).")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


if __name__ == "__main__":
    main()
