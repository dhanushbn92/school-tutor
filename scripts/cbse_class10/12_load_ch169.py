"""Load CBSE Class 10 Mathematics Chapter 2 — Polynomials (chapter_id=169)."""

import hashlib, json
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
from app.models.generation import GeneratedContent, GeneratedContentStatus, GeneratedContentType
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key

CHAPTER_ID = 169
SUBJECT_ID = 19
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch169"

TOPICS = [
    {"name": "Polynomials Recap", "description": "Definition; degree; constant, linear, quadratic, cubic.",
     "section_header": "2.1 RECAP OF POLYNOMIALS", "next_section_header": "2.2 ZEROES OF A POLYNOMIAL"},
    {"name": "Zeros Of A Polynomial", "description": "Definition; geometric meaning (x-intercepts); discriminant cases for quadratics.",
     "section_header": "2.2 ZEROES OF A POLYNOMIAL", "next_section_header": "2.3 RELATIONSHIP BETWEEN ZEROES AND COEFFICIENTS — QUADRATIC"},
    {"name": "Zeros And Coefficients Quadratic", "description": "α + β = −b/a; αβ = c/a; build a quadratic from zeros.",
     "section_header": "2.3 RELATIONSHIP BETWEEN ZEROES AND COEFFICIENTS — QUADRATIC", "next_section_header": "2.4 RELATIONSHIP BETWEEN ZEROES AND COEFFICIENTS — CUBIC"},
    {"name": "Zeros And Coefficients Cubic", "description": "Sum, sum of pair products, product for a cubic.",
     "section_header": "2.4 RELATIONSHIP BETWEEN ZEROES AND COEFFICIENTS — CUBIC", "next_section_header": "2.5 DIVISION ALGORITHM FOR POLYNOMIALS"},
    {"name": "Polynomial Division", "description": "Division algorithm for polynomials; long division procedure.",
     "section_header": "2.5 DIVISION ALGORITHM FOR POLYNOMIALS", "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "10-CBSE-MATH-PO-01", "topic_name": "Polynomials Recap", "bloom": BloomLevel.REMEMBER,
     "description": "Identify a polynomial, state its degree, and classify it (constant, linear, quadratic, cubic, biquadratic)."},
    {"code": "10-CBSE-MATH-PO-02", "topic_name": "Zeros Of A Polynomial", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define a zero (root) of a polynomial and verify whether a given value is a zero by substitution."},
    {"code": "10-CBSE-MATH-PO-03", "topic_name": "Zeros Of A Polynomial", "bloom": BloomLevel.ANALYZE,
     "description": "Use the discriminant to determine how many real zeros a quadratic has and connect to the graph."},
    {"code": "10-CBSE-MATH-PO-04", "topic_name": "Zeros And Coefficients Quadratic", "bloom": BloomLevel.APPLY,
     "description": "Apply α + β = −b/a and αβ = c/a to find sums, products and combinations of zeros of a quadratic."},
    {"code": "10-CBSE-MATH-PO-05", "topic_name": "Zeros And Coefficients Quadratic", "bloom": BloomLevel.APPLY,
     "description": "Construct a quadratic given its zeros (or sum + product of zeros)."},
    {"code": "10-CBSE-MATH-PO-06", "topic_name": "Zeros And Coefficients Cubic", "bloom": BloomLevel.APPLY,
     "description": "Apply the sum, sum of pair products, and product relations for the zeros of a cubic."},
    {"code": "10-CBSE-MATH-PO-07", "topic_name": "Polynomial Division", "bloom": BloomLevel.APPLY,
     "description": "Perform polynomial long division to find quotient and remainder; verify p = g·q + r."},
    {"code": "10-CBSE-MATH-PO-08", "topic_name": "Polynomial Division", "bloom": BloomLevel.ANALYZE,
     "description": "Use the division algorithm to find missing zeros of a polynomial when some zeros are known."},
]

BLOBS = [
    (f"{PREFIX}_chapter_summary.json", GeneratedContentType.CHAPTER_SUMMARY, ChapterSummaryOutput, {}, None, None),
    (f"{PREFIX}_lesson_plan.json", GeneratedContentType.LESSON_PLAN, LessonPlanOutput, {}, render_lesson_plan_docx, "docx"),
    (f"{PREFIX}_worksheet.json", GeneratedContentType.WORKSHEET, WorksheetOutput, {}, "worksheet", "pdf"),
    (f"{PREFIX}_ppt.json", GeneratedContentType.PPT, PPTOutlineOutput, {}, render_ppt_outline, "pptx"),
    (f"{PREFIX}_diagram.json", GeneratedContentType.DIAGRAM, DiagramOutput, {}, render_concept_map_svg, "svg"),
    (f"{PREFIX}_simulation.json", GeneratedContentType.SIMULATION, SimulationOutput, {}, render_simulation_html, "html"),
]


def _slice(text, start, end):
    i = text.index(start); j = text.index(end, i + 1); return text[i:j].strip()


def _options_payload(q):
    return {"choices": list(q["options"])} if q.get("options") else None


def _title(content_type, chapter, subject_name):
    return f"{content_type.value.replace('_', ' ').title()} - Class {CLASS_LEVEL} - {subject_name} - Chapter {chapter.chapter_number}: {chapter.title}"


def main() -> None:
    full_text = (DATA_DIR / f"{PREFIX}_full_text.txt").read_text(encoding="utf-8")
    db = SessionLocal(); store = get_artifact_store()
    try:
        chapter = db.get(Chapter, CHAPTER_ID)
        if chapter is None:
            raise SystemExit(f"chapter {CHAPTER_ID} not found")
        chapter.full_text = full_text
        chapter.content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        chapter.imported_at = datetime.now(timezone.utc)
        existing_names = {t.name for t in db.scalars(select(Topic).where(Topic.chapter_id == CHAPTER_ID)).all()}
        for spec in TOPICS:
            if spec["name"] in existing_names: continue
            slice_text = _slice(full_text, spec["section_header"], spec["next_section_header"])
            db.add(Topic(chapter_id=CHAPTER_ID, name=spec["name"], description=spec["description"], full_text=slice_text))
        db.flush()
        topic_id_by_name = {t.name: t.id for t in db.scalars(select(Topic).where(Topic.chapter_id == CHAPTER_ID)).all()}
        existing_codes = {r.code for r in db.scalars(select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)).all()}
        for o in OUTCOMES:
            if o["code"] in existing_codes: continue
            db.add(LearningOutcome(chapter_id=CHAPTER_ID, topic_id=topic_id_by_name.get(o["topic_name"]),
                code=o["code"], description=o["description"], bloom_level=o["bloom"]))
        db.commit()
        print("[ok] topics + outcomes inserted")

        outcome_map = {r.code: r.id for r in db.scalars(select(LearningOutcome).where(LearningOutcome.chapter_id == CHAPTER_ID)).all()}
        questions_data = json.loads((DATA_DIR / f"{PREFIX}_questions.json").read_text(encoding="utf-8"))["questions"]
        existing_texts = {r.text for r in db.scalars(select(Question).where(Question.chapter_id == CHAPTER_ID)).all()}
        q_added = 0
        for q in questions_data:
            if q["question"] in existing_texts: continue
            oc = q.get("outcome_code")
            db.add(Question(chapter_id=CHAPTER_ID, topic_id=q.get("topic_id"),
                outcome_id=outcome_map.get(oc) if oc else None, outcome_code=oc,
                type=QuestionType(q["type"]), difficulty=QuestionDifficulty(q["difficulty"]),
                status=QuestionStatus.APPROVED, cognitive_level=BloomLevel(q["cognitive_level"].lower()),
                text=q["question"], options=_options_payload(q), correct_answer=q["answer"],
                explanation=q.get("explanation"), marks=int(q.get("marks", 1)), created_by_id=CREATED_BY_ID))
            q_added += 1
        db.commit()
        print(f"[ok] questions inserted: {q_added}")

        subject_name = chapter.book.subject.name
        for filename, content_type, schema, options, renderer, extension in BLOBS:
            payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
            validated = schema.model_validate(payload)
            cache_key = build_generation_cache_key(content_type=content_type.value, academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL, subject_id=SUBJECT_ID, chapter_id=CHAPTER_ID, topic_id=None, prompt=None,
                options=options or None)
            existing_row = db.scalar(select(GeneratedContent).where(GeneratedContent.cache_key == cache_key))
            if existing_row is not None:
                print(f"  [skip] {content_type.value}: row {existing_row.id}"); continue
            now = datetime.now(timezone.utc)
            row = GeneratedContent(content_type=content_type, status=GeneratedContentStatus.APPROVED,
                cache_key=cache_key, academic_year=ACADEMIC_YEAR, class_level=CLASS_LEVEL, subject_id=SUBJECT_ID,
                chapter_id=CHAPTER_ID, topic_id=None, title=_title(content_type, chapter, subject_name),
                source_context=(chapter.full_text or "")[:4000], output_json=validated.model_dump(mode="json"),
                request_options=options or None, llm_provider="hand-authored", llm_model="curated-claude-agent",
                created_by_id=CREATED_BY_ID, published_at=now, published_by_id=CREATED_BY_ID)
            db.add(row); db.flush()
            if renderer is None: pass
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
