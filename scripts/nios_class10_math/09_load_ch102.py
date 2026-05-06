"""Load NIOS Class 10 Math, Chapter 4 (Special Products and
Factorisation, chapter_id=102): refresh full_text, insert topics +
outcomes, load the question bank, load + render the 6 content blobs.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/09_load_ch102.py
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
from app.models.curriculum import (
    BloomLevel,
    Chapter,
    LearningOutcome,
    Topic,
)
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


CHAPTER_ID = 102
SUBJECT_ID = 12
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14

DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch102"


TOPICS = [
    {"name": "Square Of A Binomial",
     "description": "(a+b)^2 and (a−b)^2 as perfect-square trinomials.",
     "section_header": "4.1 SPECIAL PRODUCTS — SQUARE OF A BINOMIAL",
     "next_section_header": "4.2 SPECIAL PRODUCTS — DIFFERENCE OF SQUARES AND PRODUCT-SUM"},
    {"name": "Difference Of Squares And Product-Sum",
     "description": "(a+b)(a−b) = a^2 − b^2, and (x+a)(x+b) = x^2 + (a+b)x + ab.",
     "section_header": "4.2 SPECIAL PRODUCTS — DIFFERENCE OF SQUARES AND PRODUCT-SUM",
     "next_section_header": "4.3 SPECIAL PRODUCTS — CUBES"},
    {"name": "Cubes Of Binomials",
     "description": "(a±b)^3 expansions, and the sum/difference-of-cubes factor identities.",
     "section_header": "4.3 SPECIAL PRODUCTS — CUBES",
     "next_section_header": "4.4 FACTORISATION — TAKING OUT THE COMMON FACTOR"},
    {"name": "Common Factor Method",
     "description": "Pulling out the greatest common factor from every term.",
     "section_header": "4.4 FACTORISATION — TAKING OUT THE COMMON FACTOR",
     "next_section_header": "4.5 FACTORISATION — REGROUPING"},
    {"name": "Factorisation By Regrouping",
     "description": "Pair terms so each subgroup has a common factor, exposing a shared binomial factor.",
     "section_header": "4.5 FACTORISATION — REGROUPING",
     "next_section_header": "4.6 FACTORISATION — QUADRATIC TRINOMIALS"},
    {"name": "Factorising Quadratic Trinomials",
     "description": "x^2 + bx + c by find-the-pair; ax^2 + bx + c by splitting the middle term.",
     "section_header": "4.6 FACTORISATION — QUADRATIC TRINOMIALS",
     "next_section_header": "4.7 FACTORISATION — RECOGNISING THE SPECIAL-PRODUCT PATTERNS"},
    {"name": "Factorisation Via Special-Product Patterns",
     "description": "Spotting difference-of-squares, perfect-square trinomials, sum/difference of cubes in factor problems.",
     "section_header": "4.7 FACTORISATION — RECOGNISING THE SPECIAL-PRODUCT PATTERNS",
     "next_section_header": "SUMMARY"},
]


OUTCOMES = [
    {"code": "10-NIOS-MATH-SPF-01", "topic_name": "Square Of A Binomial", "bloom": BloomLevel.REMEMBER,
     "description": "Recall and apply the identities (a+b)^2 = a^2 + 2ab + b^2 and (a−b)^2 = a^2 − 2ab + b^2."},
    {"code": "10-NIOS-MATH-SPF-02", "topic_name": "Difference Of Squares And Product-Sum", "bloom": BloomLevel.UNDERSTAND,
     "description": "Apply (a+b)(a−b) = a^2 − b^2 to expand products and to perform clever mental arithmetic such as 103 × 97."},
    {"code": "10-NIOS-MATH-SPF-03", "topic_name": "Difference Of Squares And Product-Sum", "bloom": BloomLevel.APPLY,
     "description": "Use (x+a)(x+b) = x^2 + (a+b)x + ab to expand and (in the reverse direction) to factor x^2 + bx + c."},
    {"code": "10-NIOS-MATH-SPF-04", "topic_name": "Cubes Of Binomials", "bloom": BloomLevel.APPLY,
     "description": "Expand (a±b)^3 and apply the sum/difference-of-cubes identities a^3 ± b^3 = (a ± b)(a^2 ∓ ab + b^2)."},
    {"code": "10-NIOS-MATH-SPF-05", "topic_name": "Common Factor Method", "bloom": BloomLevel.APPLY,
     "description": "Identify the greatest common factor of every term and rewrite a polynomial as common-factor × (sum of quotients)."},
    {"code": "10-NIOS-MATH-SPF-06", "topic_name": "Factorisation By Regrouping", "bloom": BloomLevel.APPLY,
     "description": "Factor a four-term polynomial by grouping pairs of terms so that each pair pulls out a matching binomial factor."},
    {"code": "10-NIOS-MATH-SPF-07", "topic_name": "Factorising Quadratic Trinomials", "bloom": BloomLevel.APPLY,
     "description": "Factor a quadratic trinomial x^2 + bx + c by finding two numbers with sum b and product c, and a general quadratic ax^2 + bx + c by splitting the middle term."},
    {"code": "10-NIOS-MATH-SPF-08", "topic_name": "Factorisation Via Special-Product Patterns", "bloom": BloomLevel.ANALYZE,
     "description": "Recognise difference-of-squares, perfect-square-trinomial and sum/difference-of-cubes patterns in a polynomial and factor it accordingly."},
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


def _title(content_type: GeneratedContentType, chapter: Chapter, subject_name: str) -> str:
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
            db.add(Topic(
                chapter_id=CHAPTER_ID,
                name=spec["name"],
                description=spec["description"],
                full_text=slice_text,
            ))
            added += 1
        db.flush()
        print(f"[ok] topics inserted: {added} (skipped {len(TOPICS) - added})")

        topic_id_by_name = {
            t.name: t.id
            for t in db.scalars(select(Topic).where(Topic.chapter_id == CHAPTER_ID)).all()
        }
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
                content_type=content_type.value,
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=CHAPTER_ID,
                topic_id=None,
                prompt=None,
                options=options or None,
            )
            existing_row = db.scalar(select(GeneratedContent).where(GeneratedContent.cache_key == cache_key))
            if existing_row is not None:
                print(f"  [skip] {content_type.value}: row {existing_row.id} already exists")
                continue
            now = datetime.now(timezone.utc)
            row = GeneratedContent(
                content_type=content_type,
                status=GeneratedContentStatus.APPROVED,
                cache_key=cache_key,
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=CHAPTER_ID,
                topic_id=None,
                title=_title(content_type, chapter, subject_name),
                source_context=(chapter.full_text or "")[:4000],
                output_json=validated.model_dump(mode="json"),
                request_options=options or None,
                llm_provider="hand-authored",
                llm_model="curated-claude-agent",
                created_by_id=CREATED_BY_ID,
                published_at=now,
                published_by_id=CREATED_BY_ID,
            )
            db.add(row)
            db.flush()
            if renderer is None:
                pass
            elif renderer == "worksheet":
                pdf_bytes = render_worksheet_pdf(
                    validated,
                    class_level=CLASS_LEVEL,
                    subject=subject_name,
                    chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
                    include_answer_key=True,
                )
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
