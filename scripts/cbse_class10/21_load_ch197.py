"""Load CBSE Class 10 Social Science (History) Chapter 1 — The Rise of Nationalism in Europe (chapter_id=197)."""

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

CHAPTER_ID = 197
SUBJECT_ID = 21
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch197"

TOPICS = [
    {"name": "Sorrieu And The Idea Of A Nation",
     "description": "Sorrieu's 1848 print and the dream of free, self-governing nations.",
     "section_header": "INTRODUCTION",
     "next_section_header": "1.1 THE FRENCH REVOLUTION AND THE IDEA OF THE NATION"},
    {"name": "French Revolution And The Nation",
     "description": "1789 — popular sovereignty; la patrie + le citoyen; tricolour; uniform laws.",
     "section_header": "1.1 THE FRENCH REVOLUTION AND THE IDEA OF THE NATION",
     "next_section_header": "1.2 NAPOLEON AND THE 'CIVIL CODE OF 1804'"},
    {"name": "Napoleonic Code",
     "description": "1804 Civil Code; equality + property; reforms abroad; backlash from conscription and taxation.",
     "section_header": "1.2 NAPOLEON AND THE 'CIVIL CODE OF 1804'",
     "next_section_header": "1.3 THE MAKING OF NATIONALISM IN EUROPE"},
    {"name": "Middle Class And Romanticism",
     "description": "Liberal middle class + Romantic culture; Herder; folk culture; Polish language.",
     "section_header": "1.3 THE MAKING OF NATIONALISM IN EUROPE",
     "next_section_header": "1.4 THE AGE OF REVOLUTIONS — 1830 AND 1848"},
    {"name": "Revolutions Of 1830 And 1848",
     "description": "July Revolution; Belgium; Greek independence; 1848 uprisings; Frankfurt parliament; women's suffrage.",
     "section_header": "1.4 THE AGE OF REVOLUTIONS — 1830 AND 1848",
     "next_section_header": "1.5 THE UNIFICATION OF GERMANY AND ITALY"},
    {"name": "Unification Of Germany And Italy",
     "description": "Bismarck — three wars 1864-71; Mazzini-Cavour-Garibaldi; Italy 1861, Germany 1871.",
     "section_header": "1.5 THE UNIFICATION OF GERMANY AND ITALY",
     "next_section_header": "1.6 THE STRANGE CASE OF BRITAIN"},
    {"name": "British Nation",
     "description": "Slow forging of a British nation through Acts of Union 1707 and 1801.",
     "section_header": "1.6 THE STRANGE CASE OF BRITAIN",
     "next_section_header": "1.7 VISUALISING THE NATION"},
    {"name": "Allegories Marianne And Germania",
     "description": "Female personifications of nations — Marianne for France, Germania for Germany.",
     "section_header": "1.7 VISUALISING THE NATION",
     "next_section_header": "1.8 NATIONALISM AND IMPERIALISM"},
    {"name": "Nationalism Imperialism Balkans",
     "description": "Late 19th c. narrow nationalism; Balkan rivalries; First World War 1914.",
     "section_header": "1.8 NATIONALISM AND IMPERIALISM",
     "next_section_header": "SUMMARY"},
]

OUTCOMES = [
    {"code": "10-CBSE-SOC-HIS-RNE-01", "topic_name": "Sorrieu And The Idea Of A Nation", "bloom": BloomLevel.UNDERSTAND,
     "description": "Interpret Sorrieu's 1848 print and explain the 19th-century vision of nations as free, self-governing peoples."},
    {"code": "10-CBSE-SOC-HIS-RNE-02", "topic_name": "French Revolution And The Nation", "bloom": BloomLevel.UNDERSTAND,
     "description": "Explain how the French Revolution shifted sovereignty to the people and created a sense of common French identity."},
    {"code": "10-CBSE-SOC-HIS-RNE-03", "topic_name": "Napoleonic Code", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse the impact of Napoleon's Civil Code on European societies — both reforms and backlash."},
    {"code": "10-CBSE-SOC-HIS-RNE-04", "topic_name": "Middle Class And Romanticism", "bloom": BloomLevel.ANALYZE,
     "description": "Describe the role of the educated middle class and the Romantic movement in spreading nationalism."},
    {"code": "10-CBSE-SOC-HIS-RNE-05", "topic_name": "Revolutions Of 1830 And 1848", "bloom": BloomLevel.EVALUATE,
     "description": "Evaluate the causes and outcomes of the liberal-nationalist revolutions of 1830 and 1848."},
    {"code": "10-CBSE-SOC-HIS-RNE-06", "topic_name": "Unification Of Germany And Italy", "bloom": BloomLevel.UNDERSTAND,
     "description": "Outline the unification of Italy (1861) and Germany (1871) and the role of key leaders."},
    {"code": "10-CBSE-SOC-HIS-RNE-07", "topic_name": "British Nation", "bloom": BloomLevel.ANALYZE,
     "description": "Compare the slow formation of the British nation-state with the revolutionary path of France and Germany."},
    {"code": "10-CBSE-SOC-HIS-RNE-08", "topic_name": "Allegories Marianne And Germania", "bloom": BloomLevel.ANALYZE,
     "description": "Interpret female allegories of nations (Marianne, Germania) and the values they represent."},
    {"code": "10-CBSE-SOC-HIS-RNE-09", "topic_name": "Nationalism Imperialism Balkans", "bloom": BloomLevel.EVALUATE,
     "description": "Explain how late-19th-century nationalism became imperialist and contributed to the First World War."},
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
