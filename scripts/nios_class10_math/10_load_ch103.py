"""Load NIOS Class 10 Math, Chapter 5 (Linear Equations, chapter_id=103).

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/10_load_ch103.py
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import BloomLevel, Chapter, LearningOutcome, Topic
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
)
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key


CHAPTER_ID = 103
SUBJECT_ID = 12
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14

DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch103"


TOPICS = [
    {"name": "Linear Equation In One Variable",
     "description": "Standard form ax + b = 0 (a ≠ 0); the unique solution x = −b/a.",
     "section_header": "5.1 LINEAR EQUATION IN ONE VARIABLE",
     "next_section_header": "5.2 SOLVING LINEAR EQUATIONS IN ONE VARIABLE"},
    {"name": "Solving One-Variable Linear Equations",
     "description": "Equality properties; clearing denominators; isolating the variable.",
     "section_header": "5.2 SOLVING LINEAR EQUATIONS IN ONE VARIABLE",
     "next_section_header": "5.3 WORD PROBLEMS — ONE VARIABLE"},
    {"name": "Word Problems One Variable",
     "description": "Translating verbal problems (number, age, money) into a single linear equation.",
     "section_header": "5.3 WORD PROBLEMS — ONE VARIABLE",
     "next_section_header": "5.4 LINEAR EQUATIONS IN TWO VARIABLES"},
    {"name": "Linear Equation In Two Variables",
     "description": "Standard form ax + by + c = 0; ordered-pair solutions; graphing as a straight line.",
     "section_header": "5.4 LINEAR EQUATIONS IN TWO VARIABLES",
     "next_section_header": "5.5 SYSTEMS OF LINEAR EQUATIONS IN TWO VARIABLES"},
    {"name": "Systems Of Linear Equations",
     "description": "Three cases: unique, no, infinitely many solutions; the ratio test.",
     "section_header": "5.5 SYSTEMS OF LINEAR EQUATIONS IN TWO VARIABLES",
     "next_section_header": "5.6 METHODS OF SOLVING SIMULTANEOUS LINEAR EQUATIONS"},
    {"name": "Methods Of Solving Systems",
     "description": "Substitution, elimination and cross-multiplication.",
     "section_header": "5.6 METHODS OF SOLVING SIMULTANEOUS LINEAR EQUATIONS",
     "next_section_header": "5.7 WORD PROBLEMS — TWO VARIABLES"},
    {"name": "Word Problems Two Variables",
     "description": "Translating two-unknown verbal problems (money, speed-and-current) into systems.",
     "section_header": "5.7 WORD PROBLEMS — TWO VARIABLES",
     "next_section_header": "SUMMARY"},
]


OUTCOMES = [
    {"code": "10-NIOS-MATH-LE-01", "topic_name": "Linear Equation In One Variable", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify a linear equation in one variable and write it in standard form ax + b = 0."},
    {"code": "10-NIOS-MATH-LE-02", "topic_name": "Solving One-Variable Linear Equations", "bloom": BloomLevel.APPLY,
     "description": "Solve a linear equation in one variable using the equality properties (clearing denominators, distributing, isolating x)."},
    {"code": "10-NIOS-MATH-LE-03", "topic_name": "Word Problems One Variable", "bloom": BloomLevel.APPLY,
     "description": "Translate a one-variable word problem (number / age / money) into a linear equation, solve it and interpret the answer."},
    {"code": "10-NIOS-MATH-LE-04", "topic_name": "Linear Equation In Two Variables", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify a linear equation in two variables and represent it geometrically as a straight line by plotting solutions."},
    {"code": "10-NIOS-MATH-LE-05", "topic_name": "Systems Of Linear Equations", "bloom": BloomLevel.ANALYZE,
     "description": "Use the coefficient-ratio test to classify a 2×2 linear system as having a unique, no or infinitely many solutions."},
    {"code": "10-NIOS-MATH-LE-06", "topic_name": "Methods Of Solving Systems", "bloom": BloomLevel.APPLY,
     "description": "Solve a system of two linear equations using the substitution method."},
    {"code": "10-NIOS-MATH-LE-07", "topic_name": "Methods Of Solving Systems", "bloom": BloomLevel.APPLY,
     "description": "Solve a system of two linear equations using the elimination (addition/subtraction) method, including cross-multiplication where convenient."},
    {"code": "10-NIOS-MATH-LE-08", "topic_name": "Word Problems Two Variables", "bloom": BloomLevel.APPLY,
     "description": "Translate a two-unknown word problem into a system of linear equations, solve it and interpret the answer."},
]


BLOBS: list[tuple[str, GeneratedContentType, type, dict[str, Any], object | None, str | None]] = [
    (f"{PREFIX}_chapter_summary.json", GeneratedContentType.CHAPTER_SUMMARY, ChapterSummaryOutput, {}, None, None),
    (f"{PREFIX}_lesson_plan.json", GeneratedContentType.LESSON_PLAN, LessonPlanOutput, {}, render_lesson_plan_docx, "docx"),
    (f"{PREFIX}_worksheet.json", GeneratedContentType.WORKSHEET, WorksheetOutput, {}, "worksheet", "pdf"),
    (f"{PREFIX}_ppt.json", GeneratedContentType.PPT, PPTOutlineOutput, {}, render_ppt_outline, "pptx"),
    (f"{PREFIX}_diagram.json", GeneratedContentType.DIAGRAM, DiagramOutput, {}, render_concept_map_svg, "svg"),
    (f"{PREFIX}_simulation.json", GeneratedContentType.SIMULATION, SimulationOutput, {}, render_simulation_html, "html"),
]


def _slice(text: str, start_header: str, end_header: str) -> str:
    i = text.index(start_header)
    j = text.index(end_header, i + 1)
    return text[i:j].strip()


def _options_payload(q: dict) -> dict | None:
    if q.get("options"):
        return {"choices": list(q["options"])}
    return None


def _title(content_type, chapter, subject_name):
    return (
        f"{content_type.value.replace('_', ' ').title()} - "
        f"Class {CLASS_LEVEL} - {subject_name} - "
        f"Chapter {chapter.chapter_number}: {chapter.title}"
    )


def main() -> None:
    full_text = (DATA_DIR / f"{PREFIX}_full_text.txt").read_text(encoding="utf-8")
    db = SessionLocal()
    store = get_artifact_store()
    try:
        chapter = db.get(Chapter, CHAPTER_ID)
        if chapter is None:
            raise SystemExit(f"chapter {CHAPTER_ID} not found")
        chapter.full_text = full_text
        chapter.content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        chapter.imported_at = datetime.now(timezone.utc)

        existing_names = {t.name for t in db.scalars(select(Topic).where(Topic.chapter_id == CHAPTER_ID)).all()}
        added = 0
        for spec in TOPICS:
            if spec["name"] in existing_names:
                continue
            slice_text = _slice(full_text, spec["section_header"], spec["next_section_header"])
            db.add(Topic(chapter_id=CHAPTER_ID, name=spec["name"], description=spec["description"], full_text=slice_text))
            added += 1
        db.flush()
        print(f"[ok] topics inserted: {added} (skipped {len(TOPICS) - added})")

        topic_id_by_name = {t.name: t.id for t in db.scalars(select(Topic).where(Topic.chapter_id == CHAPTER_ID)).all()}
        existing_codes = {r.code for r in db.scalars(select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)).all()}
        added_o = 0
        for o in OUTCOMES:
            if o["code"] in existing_codes:
                continue
            db.add(LearningOutcome(
                chapter_id=CHAPTER_ID,
                topic_id=topic_id_by_name.get(o["topic_name"]),
                code=o["code"],
                description=o["description"],
                bloom_level=o["bloom"],
            ))
            added_o += 1
        db.commit()
        print(f"[ok] outcomes inserted: {added_o} (skipped {len(OUTCOMES) - added_o})")

        outcome_map = {r.code: r.id for r in db.scalars(select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)).all()}
        questions_data = json.loads((DATA_DIR / f"{PREFIX}_questions.json").read_text(encoding="utf-8"))["questions"]
        existing_texts = {r.text for r in db.scalars(select(Question).where(Question.chapter_id == CHAPTER_ID)).all()}
        q_added = 0
        for q in questions_data:
            if q["question"] in existing_texts:
                continue
            outcome_code = q.get("outcome_code")
            outcome_id = outcome_map.get(outcome_code) if outcome_code else None
            db.add(Question(
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
            ))
            q_added += 1
        db.commit()
        print(f"[ok] questions inserted: {q_added} (skipped {len(questions_data) - q_added})")

        subject_name = chapter.book.subject.name
        for filename, content_type, schema, options, renderer, extension in BLOBS:
            payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
            validated = schema.model_validate(payload)
            cache_key = build_generation_cache_key(
                content_type=content_type.value, academic_year=ACADEMIC_YEAR, class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID, chapter_id=CHAPTER_ID, topic_id=None, prompt=None, options=options or None,
            )
            existing_row = db.scalar(select(GeneratedContent).where(GeneratedContent.cache_key == cache_key))
            if existing_row is not None:
                print(f"  [skip] {content_type.value}: row {existing_row.id} already exists")
                continue
            now = datetime.now(timezone.utc)
            row = GeneratedContent(
                content_type=content_type, status=GeneratedContentStatus.APPROVED, cache_key=cache_key,
                academic_year=ACADEMIC_YEAR, class_level=CLASS_LEVEL, subject_id=SUBJECT_ID, chapter_id=CHAPTER_ID, topic_id=None,
                title=_title(content_type, chapter, subject_name), source_context=(chapter.full_text or "")[:4000],
                output_json=validated.model_dump(mode="json"), request_options=options or None,
                llm_provider="hand-authored", llm_model="curated-claude-agent",
                created_by_id=CREATED_BY_ID, published_at=now, published_by_id=CREATED_BY_ID,
            )
            db.add(row); db.flush()
            if renderer is None:
                pass
            elif renderer == "worksheet":
                pdf_bytes = render_worksheet_pdf(validated, class_level=CLASS_LEVEL, subject=subject_name,
                    chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}", include_answer_key=True)
                row.artifact_url = store.save(content_id=row.id, extension="pdf", data=pdf_bytes)
            else:
                data = renderer(validated)
                row.artifact_url = store.save(content_id=row.id, extension=extension, data=data)
            db.commit()
            print(f"  [ok]   {content_type.value}: row {row.id} -> {row.artifact_url or '(json-only)'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
