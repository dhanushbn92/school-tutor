"""Load CBSE Class 6 Social Science (Exploring Society) Chapter 4 — Timeline and Sources of History (chapter_id=138)."""

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

CHAPTER_ID = 138
SUBJECT_ID = 16
CLASS_LEVEL = 6
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch138"

TOPICS = [
    {"name": "The Timeline",
     "description": "Order, duration and simultaneity on a line; how a timeline is read.",
     "section_header": "4.1 THE IDEA OF A TIMELINE",
     "next_section_header": "4.2 HOW TIME IS COUNTED — BCE AND CE"},
    {"name": "Counting Years BCE And CE",
     "description": "BCE / CE meaning, no year zero, BCE/CE arithmetic, Vikram and Shaka eras.",
     "section_header": "4.2 HOW TIME IS COUNTED — BCE AND CE",
     "next_section_header": "4.3 BIG BLOCKS OF TIME"},
    {"name": "Big Blocks And Indian Periods",
     "description": "Decade / century / millennium; Stone, Bronze, Iron Ages; Ancient, Medieval, Modern.",
     "section_header": "4.3 BIG BLOCKS OF TIME",
     "next_section_header": "4.5 SOURCES — HOW HISTORIANS KNOW THE PAST"},
    {"name": "Three Families Of Sources",
     "description": "Archaeological, literary, oral; strengths and limitations of each.",
     "section_header": "4.5 SOURCES — HOW HISTORIANS KNOW THE PAST",
     "next_section_header": "4.6 ARCHAEOLOGY UP CLOSE"},
    {"name": "Archaeology And Dating",
     "description": "Stratigraphy (layers), radiocarbon dating, famous Indian sites.",
     "section_header": "4.6 ARCHAEOLOGY UP CLOSE",
     "next_section_header": "4.7 LITERARY SOURCES UP CLOSE"},
    {"name": "Texts Inscriptions And Asking Questions",
     "description": "Vedas, epics, Tripiṭakas, Sangam, Ashoka's edicts, coins; how to question a source.",
     "section_header": "4.7 LITERARY SOURCES UP CLOSE",
     "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "6-CBSE-SOC-TSH-01", "topic_name": "The Timeline", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define a timeline and explain what it shows (order, duration, simultaneity)."},
    {"code": "6-CBSE-SOC-TSH-02", "topic_name": "Counting Years BCE And CE", "bloom": BloomLevel.APPLY,
     "description": "Use BCE / CE correctly, including the no-year-zero rule, to compute the gap between two dates."},
    {"code": "6-CBSE-SOC-TSH-03", "topic_name": "Big Blocks And Indian Periods", "bloom": BloomLevel.REMEMBER,
     "description": "Recall decade / century / millennium as 10 / 100 / 1000 years and the meaning of Stone/Bronze/Iron Ages."},
    {"code": "6-CBSE-SOC-TSH-04", "topic_name": "Big Blocks And Indian Periods", "bloom": BloomLevel.ANALYZE,
     "description": "Place Indian historical events into the broad periods Ancient, Medieval and Modern."},
    {"code": "6-CBSE-SOC-TSH-05", "topic_name": "Three Families Of Sources", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish archaeological, literary and oral sources with examples."},
    {"code": "6-CBSE-SOC-TSH-06", "topic_name": "Archaeology And Dating", "bloom": BloomLevel.UNDERSTAND,
     "description": "Explain stratigraphy and radiocarbon (C-14) dating and what kinds of samples each can date."},
    {"code": "6-CBSE-SOC-TSH-07", "topic_name": "Texts Inscriptions And Asking Questions", "bloom": BloomLevel.REMEMBER,
     "description": "Identify major Indian literary sources (Vedas, epics, Tripiṭakas, Sangam, inscriptions) and what each tells us."},
    {"code": "6-CBSE-SOC-TSH-08", "topic_name": "Texts Inscriptions And Asking Questions", "bloom": BloomLevel.EVALUATE,
     "description": "Ask careful questions of a source (who, when, why, what is left out) and judge reliability by cross-checking."},
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
