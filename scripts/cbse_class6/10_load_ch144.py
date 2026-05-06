"""Load CBSE Class 6 Social Science Chapter 10 — Grassroots Democracy Part 1: Governance (chapter_id=144)."""

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

CHAPTER_ID = 144
SUBJECT_ID = 16
CLASS_LEVEL = 6
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch144"

TOPICS = [
    {"name": "What Is Governance",
     "description": "Definition, three pillars, three big questions of governance.",
     "section_header": "10.1 WHAT IS GOVERNANCE?",
     "next_section_header": "10.3 WHAT IS DEMOCRACY?"},
    {"name": "What Is Democracy",
     "description": "Greek roots, representative model, five features of a democracy.",
     "section_header": "10.3 WHAT IS DEMOCRACY?",
     "next_section_header": "10.4 INDIA AS THE WORLD'S LARGEST DEMOCRACY"},
    {"name": "India As Democratic Republic",
     "description": "1947, 1950, Ambedkar, the five Preamble words.",
     "section_header": "10.4 INDIA AS THE WORLD'S LARGEST DEMOCRACY",
     "next_section_header": "10.5 LEVELS OF GOVERNMENT IN INDIA"},
    {"name": "Three Levels Of Government",
     "description": "Union, State, Local — what each handles.",
     "section_header": "10.5 LEVELS OF GOVERNMENT IN INDIA",
     "next_section_header": "10.6 WHY LOCAL GOVERNMENT MATTERS"},
    {"name": "Local Government And Gram Swaraj",
     "description": "Gram Swaraj; 73rd & 74th Amendments; why local matters.",
     "section_header": "10.6 WHY LOCAL GOVERNMENT MATTERS",
     "next_section_header": "10.7 RIGHTS, DUTIES AND PARTICIPATION"},
    {"name": "Citizenship And Watchdogs",
     "description": "Rights, Duties, participation; free press, courts, civil society.",
     "section_header": "10.7 RIGHTS, DUTIES AND PARTICIPATION",
     "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "6-CBSE-SOC-GOV-01", "topic_name": "What Is Governance", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define governance and list the three pillars of good governance (rules, processes, accountability)."},
    {"code": "6-CBSE-SOC-GOV-02", "topic_name": "What Is Governance", "bloom": BloomLevel.REMEMBER,
     "description": "State the three big questions of governance: who rules, how decisions are made, how power is limited."},
    {"code": "6-CBSE-SOC-GOV-03", "topic_name": "What Is Democracy", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define democracy and list its key features (fair elections, equal vote, multi-party, limited power, citizen rights)."},
    {"code": "6-CBSE-SOC-GOV-04", "topic_name": "India As Democratic Republic", "bloom": BloomLevel.REMEMBER,
     "description": "State the key dates and Preamble words of the Indian Republic (1947, 1950, sovereign, secular, republic)."},
    {"code": "6-CBSE-SOC-GOV-05", "topic_name": "Three Levels Of Government", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify the three levels of Indian government and which subjects each level mainly handles."},
    {"code": "6-CBSE-SOC-GOV-06", "topic_name": "Local Government And Gram Swaraj", "bloom": BloomLevel.ANALYZE,
     "description": "Explain why local government matters most for everyday life, citing Gram Swaraj and the 73rd/74th Amendments."},
    {"code": "6-CBSE-SOC-GOV-07", "topic_name": "Citizenship And Watchdogs", "bloom": BloomLevel.APPLY,
     "description": "List ways a citizen can participate in democracy beyond voting and recall key Fundamental Rights and Duties."},
    {"code": "6-CBSE-SOC-GOV-08", "topic_name": "Citizenship And Watchdogs", "bloom": BloomLevel.EVALUATE,
     "description": "Explain why elections alone are not enough; describe the role of free press, courts, institutions and civil society."},
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
