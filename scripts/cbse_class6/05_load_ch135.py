"""Load CBSE Class 6 Social Science (Exploring Society) Chapter 1 — Locating Places on the Earth (chapter_id=135)."""

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

CHAPTER_ID = 135
SUBJECT_ID = 16
CLASS_LEVEL = 6
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch135"

TOPICS = [
    {"name": "Shape Of The Earth",
     "description": "The Earth as an oblate spheroid; spinning axis and the poles.",
     "section_header": "1.1 THE SHAPE OF THE EARTH",
     "next_section_header": "1.2 GLOBES AND MAPS"},
    {"name": "Globes And Maps",
     "description": "Globe = round model; map = flat drawing; advantages and limitations of each.",
     "section_header": "1.2 GLOBES AND MAPS",
     "next_section_header": "1.3 LATITUDES — IMAGINARY EAST-WEST LINES"},
    {"name": "Latitudes",
     "description": "Parallels; equator (0°); Tropics, Polar Circles, Poles; heat zones.",
     "section_header": "1.3 LATITUDES — IMAGINARY EAST-WEST LINES",
     "next_section_header": "1.4 LONGITUDES — IMAGINARY NORTH-SOUTH LINES"},
    {"name": "Longitudes",
     "description": "Meridians; Prime Meridian (0°); 180° lines; International Date Line.",
     "section_header": "1.4 LONGITUDES — IMAGINARY NORTH-SOUTH LINES",
     "next_section_header": "1.5 THE GEOGRAPHIC GRID — LOCATING A PLACE"},
    {"name": "Geographic Grid",
     "description": "Coordinates (latitude, longitude); finding places and reading coordinates.",
     "section_header": "1.5 THE GEOGRAPHIC GRID — LOCATING A PLACE",
     "next_section_header": "1.6 GREAT CIRCLES AND TIME ZONES"},
    {"name": "Great Circles And Time Zones",
     "description": "Great vs small circles; 15° per hour rotation; IST at 82.5° E.",
     "section_header": "1.6 GREAT CIRCLES AND TIME ZONES",
     "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "6-CBSE-SOC-LPE-01", "topic_name": "Shape Of The Earth", "bloom": BloomLevel.UNDERSTAND,
     "description": "Describe the shape of the Earth and identify its geographic poles."},
    {"code": "6-CBSE-SOC-LPE-02", "topic_name": "Globes And Maps", "bloom": BloomLevel.UNDERSTAND,
     "description": "Compare a globe and a map; state the advantage and limitation of each."},
    {"code": "6-CBSE-SOC-LPE-03", "topic_name": "Latitudes", "bloom": BloomLevel.REMEMBER,
     "description": "Name the major parallels (Equator, Tropic of Cancer, Tropic of Capricorn, Arctic Circle, Antarctic Circle, Poles) and their degree values."},
    {"code": "6-CBSE-SOC-LPE-04", "topic_name": "Latitudes", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify the three heat zones (Torrid, Temperate, Frigid) and their relation to the parallels."},
    {"code": "6-CBSE-SOC-LPE-05", "topic_name": "Longitudes", "bloom": BloomLevel.REMEMBER,
     "description": "Identify the Prime Meridian (0°), the 180° meridian and the International Date Line."},
    {"code": "6-CBSE-SOC-LPE-06", "topic_name": "Geographic Grid", "bloom": BloomLevel.APPLY,
     "description": "Read a (latitude, longitude) coordinate and use it to locate a place on a globe / map."},
    {"code": "6-CBSE-SOC-LPE-07", "topic_name": "Great Circles And Time Zones", "bloom": BloomLevel.APPLY,
     "description": "Use the 15°-per-hour rule to compute time differences between two places."},
    {"code": "6-CBSE-SOC-LPE-08", "topic_name": "Geographic Grid", "bloom": BloomLevel.ANALYZE,
     "description": "Compare two places given their coordinates (which is north / east etc.)."},
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
