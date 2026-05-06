"""Load NIOS Class 10 Math, Chapter 3 (Algebraic Expressions and
Polynomials, chapter_id=101): refresh full_text, insert topics +
outcomes, load the question bank, load + render the 6 content blobs.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class10_math/07_load_ch101.py
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


CHAPTER_ID = 101
SUBJECT_ID = 12     # NIOS Class 10 Mathematics
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14  # platform.team@anaadi.org

DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch101"


TOPICS = [
    {"name": "Algebraic Expressions Vocabulary",
     "description": "Variables, constants, terms, coefficients, like vs unlike terms, the constant term.",
     "section_header": "3.1 ALGEBRAIC EXPRESSIONS — VOCABULARY",
     "next_section_header": "3.2 CLASSIFYING EXPRESSIONS BY NUMBER OF TERMS"},
    {"name": "Classifying By Number Of Terms",
     "description": "Monomials, binomials, trinomials and multinomials.",
     "section_header": "3.2 CLASSIFYING EXPRESSIONS BY NUMBER OF TERMS",
     "next_section_header": "3.3 POLYNOMIALS"},
    {"name": "Polynomials And Degree",
     "description": "Definition of a polynomial, examples and non-examples, degree in one and several variables, standard form.",
     "section_header": "3.3 POLYNOMIALS",
     "next_section_header": "3.4 ADDING AND SUBTRACTING POLYNOMIALS"},
    {"name": "Addition And Subtraction",
     "description": "Combining like terms via the horizontal and vertical methods, sign-flipping for subtraction.",
     "section_header": "3.4 ADDING AND SUBTRACTING POLYNOMIALS",
     "next_section_header": "3.5 MULTIPLYING POLYNOMIALS"},
    {"name": "Multiplication Of Polynomials",
     "description": "Distributive law, FOIL for binomials, vertical long-multiplication, exponent rules during product.",
     "section_header": "3.5 MULTIPLYING POLYNOMIALS",
     "next_section_header": "3.6 LAWS OF EXPONENTS IN POLYNOMIAL MULTIPLICATION"},
    {"name": "Evaluating Polynomials And Zeros",
     "description": "Substituting a number for the variable to compute a value; definition of a zero (root) of a polynomial.",
     "section_header": "3.7 VALUE OF A POLYNOMIAL AT A NUMBER",
     "next_section_header": "SUMMARY"},
]


OUTCOMES = [
    {"code": "10-NIOS-MATH-AEP-01", "topic_name": "Algebraic Expressions Vocabulary", "bloom": BloomLevel.REMEMBER,
     "description": "Identify variables, constants, terms, coefficients and the constant term in a given algebraic expression."},
    {"code": "10-NIOS-MATH-AEP-02", "topic_name": "Algebraic Expressions Vocabulary", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish like terms from unlike terms; combine like terms by adding or subtracting their coefficients."},
    {"code": "10-NIOS-MATH-AEP-03", "topic_name": "Classifying By Number Of Terms", "bloom": BloomLevel.UNDERSTAND,
     "description": "Classify a given expression as a monomial, binomial, trinomial or multinomial based on its number of unlike terms."},
    {"code": "10-NIOS-MATH-AEP-04", "topic_name": "Polynomials And Degree", "bloom": BloomLevel.UNDERSTAND,
     "description": "Determine whether a given algebraic expression is a polynomial and, if so, find its degree (in one or several variables) and write it in standard form."},
    {"code": "10-NIOS-MATH-AEP-05", "topic_name": "Addition And Subtraction", "bloom": BloomLevel.APPLY,
     "description": "Add and subtract polynomials in one or several variables using either the horizontal or the vertical method."},
    {"code": "10-NIOS-MATH-AEP-06", "topic_name": "Multiplication Of Polynomials", "bloom": BloomLevel.APPLY,
     "description": "Multiply two polynomials by applying the distributive law, including FOIL for binomials and long multiplication for higher-degree cases."},
    {"code": "10-NIOS-MATH-AEP-07", "topic_name": "Multiplication Of Polynomials", "bloom": BloomLevel.ANALYZE,
     "description": "Determine the degree of a polynomial product without expanding it, by adding the degrees of the factors."},
    {"code": "10-NIOS-MATH-AEP-08", "topic_name": "Evaluating Polynomials And Zeros", "bloom": BloomLevel.APPLY,
     "description": "Evaluate a polynomial at a given value of the variable, and verify whether a candidate value is a zero of the polynomial."},
]


# (filename, content_type, schema, options, renderer, ext) — same shape
# the chapter-71/72 loaders used.
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
        # 1. Chapter full_text + content_hash + title fix.
        chapter = db.get(Chapter, CHAPTER_ID)
        if chapter is None:
            raise SystemExit(f"chapter {CHAPTER_ID} not found")
        chapter.full_text = full_text
        chapter.content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        chapter.imported_at = datetime.now(timezone.utc)
        # Normalise title casing if it's still the scaffolded form.
        if chapter.title and chapter.title != "Algebraic Expressions and Polynomials":
            print(f"[note] chapter {CHAPTER_ID} title was {chapter.title!r}; leaving as-is")

        # 2. Topics with verbatim slices.
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

        # 3. Learning outcomes.
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

        # 4. Questions.
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

        # 5. Content blobs (validate + insert APPROVED + render artifact).
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
