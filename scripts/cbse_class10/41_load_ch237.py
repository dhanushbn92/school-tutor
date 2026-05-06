"""Load CBSE Class 10 Hindi (Kshitij Bhag 2) Chapter 1 — सूरदास के पद (chapter_id=237)."""

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
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

CHAPTER_ID = 237
SUBJECT_ID = 23
CLASS_LEVEL = 10
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
DATA_DIR = Path(__file__).parent / "data"
PREFIX = "ch237"

TOPICS = [
    {"name": "सूरदास का परिचय",
     "description": "सूरदास का जीवन-काल, अष्टछाप, सूरसागर।",
     "section_header": "१.१ सूरदास का परिचय",
     "next_section_header": "१.२ भ्रमरगीत — पृष्ठभूमि"},
    {"name": "भ्रमरगीत-पृष्ठभूमि",
     "description": "कृष्ण-गोपी-उद्धव संवाद की पृष्ठभूमि।",
     "section_header": "१.२ भ्रमरगीत — पृष्ठभूमि",
     "next_section_header": "१.३ पहला पद — 'ऊधो, तुम हो बड़भागी'"},
    {"name": "पहला पद — बड़भागी",
     "description": "उद्धव की निर्लिप्तता पर व्यंग्य; कमल-पत्र और तेल की मटकी की उपमाएँ।",
     "section_header": "१.३ पहला पद — 'ऊधो, तुम हो बड़भागी'",
     "next_section_header": "१.४ दूसरा पद — 'मन की मन ही माँझ रही'"},
    {"name": "दूसरा पद — मन की मन माँझ",
     "description": "गोपियों की मनोव्यथा और योग-संदेश का अस्वीकरण।",
     "section_header": "१.४ दूसरा पद — 'मन की मन ही माँझ रही'",
     "next_section_header": "१.५ तीसरा पद — 'हमारे हरि हारिल की लकरी'"},
    {"name": "तीसरा पद — हारिल की लकरी",
     "description": "एकनिष्ठ कृष्ण-प्रेम; हारिल पक्षी की उपमा।",
     "section_header": "१.५ तीसरा पद — 'हमारे हरि हारिल की लकरी'",
     "next_section_header": "१.६ चौथा पद — 'हरि हैं राजनीति पढ़ि आए'"},
    {"name": "चौथा पद — राजनीति पढ़ि आए",
     "description": "कृष्ण से शिकायत; राजनीति पर व्यंग्य।",
     "section_header": "१.६ चौथा पद — 'हरि हैं राजनीति पढ़ि आए'",
     "next_section_header": "१.७ पदों का सम्मिलित भाव"},
    {"name": "काव्य-शैली और अलंकार",
     "description": "ब्रजभाषा, मुख्य अलंकार, रस।",
     "section_header": "१.८ काव्य-शैली और भाषा",
     "next_section_header": "१.९ शब्दार्थ"},
    {"name": "शब्दार्थ और आधुनिक संदर्भ",
     "description": "ब्रजभाषा के विशिष्ट शब्द और पाठ की आधुनिक प्रासंगिकता।",
     "section_header": "१.९ शब्दार्थ",
     "next_section_header": "संक्षिप्त सारांश"},
]

OUTCOMES = [
    {"code": "10-CBSE-HIN-SUR-01", "topic_name": "सूरदास का परिचय", "bloom": BloomLevel.REMEMBER,
     "description": "सूरदास का जीवन-काल, सम्प्रदाय, अष्टछाप और प्रमुख रचनाओं की जानकारी।"},
    {"code": "10-CBSE-HIN-SUR-02", "topic_name": "भ्रमरगीत-पृष्ठभूमि", "bloom": BloomLevel.UNDERSTAND,
     "description": "भ्रमरगीत प्रसंग की पृष्ठभूमि और उद्धव-गोपी संवाद का स्वरूप समझना।"},
    {"code": "10-CBSE-HIN-SUR-03", "topic_name": "पहला पद — बड़भागी", "bloom": BloomLevel.ANALYZE,
     "description": "पहले पद के व्यंग्य, उपमाओं और मूल भाव का विश्लेषण।"},
    {"code": "10-CBSE-HIN-SUR-04", "topic_name": "दूसरा पद — मन की मन माँझ", "bloom": BloomLevel.ANALYZE,
     "description": "गोपियों की मनोव्यथा और उद्धव के योग-संदेश के अस्वीकरण का विश्लेषण।"},
    {"code": "10-CBSE-HIN-SUR-05", "topic_name": "तीसरा पद — हारिल की लकरी", "bloom": BloomLevel.UNDERSTAND,
     "description": "हारिल पक्षी की उपमा और एकनिष्ठ कृष्ण-प्रेम के प्रतीक का अर्थ।"},
    {"code": "10-CBSE-HIN-SUR-06", "topic_name": "चौथा पद — राजनीति पढ़ि आए", "bloom": BloomLevel.EVALUATE,
     "description": "चौथे पद में राजनीति शब्द के बहुस्तरीय अर्थ और व्यंग्य का मूल्यांकन।"},
    {"code": "10-CBSE-HIN-SUR-07", "topic_name": "काव्य-शैली और अलंकार", "bloom": BloomLevel.ANALYZE,
     "description": "सूरदास की भाषा, शैली, अलंकार और रस-योजना का विश्लेषण।"},
    {"code": "10-CBSE-HIN-SUR-08", "topic_name": "शब्दार्थ और आधुनिक संदर्भ", "bloom": BloomLevel.REMEMBER,
     "description": "ब्रजभाषा के विशिष्ट शब्दों के अर्थ और प्रयोग की पहचान।"},
    {"code": "10-CBSE-HIN-SUR-09", "topic_name": "काव्य-शैली और अलंकार", "bloom": BloomLevel.EVALUATE,
     "description": "चारों पदों के सम्मिलित भाव और सगुण भक्ति की निर्गुण ज्ञान पर श्रेष्ठता का मूल्यांकन।"},
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
