"""Load CBSE Class 10 English (First Flight) Chapter 2 — Nelson Mandela + A Tiger in the Zoo (chapter_id=220)."""

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

CHAPTER_ID = 220
SUBJECT_ID = 22
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch220"

TOPICS = [
    {"name": "Inauguration Day",
     "description": "10 May 1994 — Mandela inaugurated as first black President.",
     "section_header": "2.1 'LONG WALK TO FREEDOM' — THE INAUGURATION DAY",
     "next_section_header": "2.2 WHAT MANDELA SAID — KEY IDEAS"},
    {"name": "Mandela Key Ideas",
     "description": "Twin obligations, courage, love, freedom — Mandela's central ideas.",
     "section_header": "2.2 WHAT MANDELA SAID — KEY IDEAS",
     "next_section_header": "2.3 SOUTH AFRICA AND APARTHEID — A SHORT BACKGROUND"},
    {"name": "Apartheid Background",
     "description": "Apartheid system, ANC, Mandela's prison years.",
     "section_header": "2.3 SOUTH AFRICA AND APARTHEID — A SHORT BACKGROUND",
     "next_section_header": "2.4 THEMES OF 'LONG WALK TO FREEDOM'"},
    {"name": "Mandela Themes And Craft",
     "description": "Themes — freedom, struggle, forgiveness, unity, courage, ubuntu.",
     "section_header": "2.4 THEMES OF 'LONG WALK TO FREEDOM'",
     "next_section_header": "2.6 'A TIGER IN THE ZOO' — PARAPHRASE OF MEANING"},
    {"name": "Tiger In The Zoo",
     "description": "Norris's poem — caged tiger and wild tiger alternated.",
     "section_header": "2.6 'A TIGER IN THE ZOO' — PARAPHRASE OF MEANING",
     "next_section_header": "2.9 PUTTING THE TWO PIECES TOGETHER"},
    {"name": "Connecting The Chapter",
     "description": "The two pieces as a meditation on freedom from opposite poles.",
     "section_header": "2.9 PUTTING THE TWO PIECES TOGETHER",
     "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "10-CBSE-ENG-NM-01", "topic_name": "Inauguration Day", "bloom": BloomLevel.REMEMBER,
     "description": "Recall the events of Mandela's inauguration on 10 May 1994."},
    {"code": "10-CBSE-ENG-NM-02", "topic_name": "Apartheid Background", "bloom": BloomLevel.UNDERSTAND,
     "description": "Explain what apartheid was and the long South African struggle against it."},
    {"code": "10-CBSE-ENG-NM-03", "topic_name": "Mandela Key Ideas", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse Mandela's idea of 'twin obligations' to family and to people."},
    {"code": "10-CBSE-ENG-NM-04", "topic_name": "Mandela Key Ideas", "bloom": BloomLevel.UNDERSTAND,
     "description": "Discuss Mandela's ideas on courage, love and hate."},
    {"code": "10-CBSE-ENG-NM-05", "topic_name": "Mandela Key Ideas", "bloom": BloomLevel.EVALUATE,
     "description": "Evaluate Mandela's evolving understanding of freedom — boy, young man, adult."},
    {"code": "10-CBSE-ENG-NM-06", "topic_name": "Mandela Themes And Craft", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse the symbols and gestures of the inauguration that represent the new South Africa."},
    {"code": "10-CBSE-ENG-NM-07", "topic_name": "Mandela Themes And Craft", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify Mandela's view of apartheid as 'an extraordinary human disaster'."},
    {"code": "10-CBSE-ENG-NM-08", "topic_name": "Apartheid Background", "bloom": BloomLevel.REMEMBER,
     "description": "Trace the timeline of Mandela's life from boyhood to presidency."},
    {"code": "10-CBSE-ENG-NM-09", "topic_name": "Connecting The Chapter", "bloom": BloomLevel.ANALYZE,
     "description": "Connect Mandela's prose with Norris's poem as a meditation on freedom."},
    {"code": "10-CBSE-ENG-TZ-01", "topic_name": "Tiger In The Zoo", "bloom": BloomLevel.REMEMBER,
     "description": "Recall the form, author and structure of 'A Tiger in the Zoo'."},
    {"code": "10-CBSE-ENG-TZ-02", "topic_name": "Tiger In The Zoo", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse the contrast between caged and wild tiger across the alternating stanzas."},
    {"code": "10-CBSE-ENG-TZ-03", "topic_name": "Tiger In The Zoo", "bloom": BloomLevel.UNDERSTAND,
     "description": "Identify the key vocabulary, rhyme scheme and imagery of the poem."},
    {"code": "10-CBSE-ENG-TZ-04", "topic_name": "Tiger In The Zoo", "bloom": BloomLevel.EVALUATE,
     "description": "Evaluate the poem's indirect critique of zoos and its symbol of distant freedom (the brilliant stars)."},
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
