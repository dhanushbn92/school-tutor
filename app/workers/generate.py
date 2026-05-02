import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.llm import LLMError, get_llm_provider
from app.llm.prompts.chapter_summary import (
    CHAPTER_SUMMARY_SYSTEM_PROMPT,
    build_chapter_summary_user_prompt,
)
from app.llm.prompts.diagram import DIAGRAM_SYSTEM_PROMPT, build_diagram_user_prompt
from app.llm.prompts.lesson_plan import (
    LESSON_PLAN_SYSTEM_PROMPT,
    build_lesson_plan_user_prompt,
)
from app.llm.prompts.ppt import PPT_SYSTEM_PROMPT, build_ppt_user_prompt
from app.llm.prompts.quiz import QUIZ_SYSTEM_PROMPT, build_quiz_user_prompt
from app.llm.prompts.simulation import SIMULATION_SYSTEM_PROMPT, build_simulation_user_prompt
from app.llm.prompts.worksheet import (
    WORKSHEET_SYSTEM_PROMPT,
    WorksheetRequest,
    build_worksheet_user_prompt,
)
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.quiz import QuizOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput, WorksheetQuestion
from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.generation import GeneratedContent, GeneratedContentStatus, GeneratedContentType
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf
from app.services.artifact_store import get_artifact_store
from app.services.curriculum_service import build_curriculum_context


log = logging.getLogger(__name__)


def run_generation_job(content_id: int) -> None:
    """Background entry point. Idempotent for non-PENDING rows."""
    with SessionLocal() as db:
        row = db.get(GeneratedContent, content_id)
        if row is None:
            log.warning("generation job %s: row missing", content_id)
            return
        if row.status != GeneratedContentStatus.PENDING:
            log.info("generation job %s: status=%s, skipping", content_id, row.status)
            return

        try:
            if row.content_type == GeneratedContentType.WORKSHEET:
                _run_worksheet_job(db, row)
            elif row.content_type == GeneratedContentType.QUIZ:
                _run_quiz_job(db, row)
            elif row.content_type == GeneratedContentType.LESSON_PLAN:
                _run_lesson_plan_job(db, row)
            elif row.content_type == GeneratedContentType.PPT:
                _run_ppt_job(db, row)
            elif row.content_type == GeneratedContentType.DIAGRAM:
                _run_diagram_job(db, row)
            elif row.content_type == GeneratedContentType.SIMULATION:
                _run_simulation_job(db, row)
            elif row.content_type == GeneratedContentType.CHAPTER_SUMMARY:
                _run_chapter_summary_job(db, row)
            else:
                row.status = GeneratedContentStatus.FAILED
                row.error_message = (
                    f"Content type {row.content_type.value} is not implemented yet."
                )
        except LLMError as exc:
            log.exception("generation job %s: LLM error", content_id)
            row.status = GeneratedContentStatus.FAILED
            row.error_message = f"LLM error: {exc}"
        except Exception as exc:  # noqa: BLE001
            log.exception("generation job %s: unexpected failure", content_id)
            row.status = GeneratedContentStatus.FAILED
            row.error_message = f"{type(exc).__name__}: {exc}"
        finally:
            db.commit()


# Cap chapter-text size fed to the LLM so we stay under provider per-request
# token limits (Groq free tier is 12k TPM per request). 25k chars ≈ 6k tokens,
# leaves ~6k tokens for prompt scaffold + JSON schema + response headroom.
_MAX_CHAPTER_TEXT_CHARS = 25_000


def _build_request(db: Session, row: GeneratedContent) -> tuple[WorksheetRequest, dict]:
    if row.chapter_id is None:
        raise ValueError("Generation requires chapter_id for this content type")
    context = build_curriculum_context(db, row.chapter_id, row.topic_id)
    if context is None:
        raise ValueError(f"Chapter {row.chapter_id} not found")
    if not context.get("outcomes"):
        raise ValueError(
            f"Chapter {row.chapter_id} has no learning outcomes; author them first."
        )

    chapter_text = context["chapter_text"]
    if len(chapter_text) > _MAX_CHAPTER_TEXT_CHARS:
        chapter_text = chapter_text[:_MAX_CHAPTER_TEXT_CHARS] + "\n…[truncated for token budget]"

    options: dict[str, Any] = row.request_options or {}
    req = WorksheetRequest(
        class_level=context["class_level"],
        subject_name=context["subject"],
        chapter_number=context["chapter_number"],
        chapter_title=context["chapter_title"],
        chapter_text=chapter_text,
        outcomes=context["outcomes"],
        topics=context["topics"],
        question_count=int(options.get("question_count", 10)),
        difficulty_mix=options.get("difficulty_mix"),
        cognitive_mix=options.get("cognitive_mix"),
        question_types=options.get("question_types"),
        focus_outcome_codes=options.get("focus_outcome_codes"),
    )
    return req, context


def _run_worksheet_job(db: Session, row: GeneratedContent) -> None:
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}
    user_prompt = build_worksheet_user_prompt(req)

    log.info(
        "generation job %s: calling LLM for worksheet ch=%s outcomes=%s q=%s",
        row.id,
        context["chapter_number"],
        len(context["outcomes"]),
        req.question_count,
    )
    worksheet = provider.generate_structured(
        system=WORKSHEET_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=WorksheetOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    pdf_bytes = render_worksheet_pdf(
        worksheet,
        class_level=context["class_level"],
        subject=context["subject"],
        chapter_title=f"Chapter {context['chapter_number']}: {context['chapter_title']}",
        include_answer_key=bool(options.get("include_answer_key", True)),
    )
    artifact_path = get_artifact_store().save(
        content_id=row.id, extension="pdf", data=pdf_bytes
    )

    row.output_json = worksheet.model_dump(mode="json")
    row.artifact_url = artifact_path
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None


def _run_quiz_job(db: Session, row: GeneratedContent) -> None:
    if row.created_by_id is None:
        raise ValueError("Quiz generation requires an authenticated creator")

    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}
    user_prompt = build_quiz_user_prompt(req)

    log.info(
        "generation job %s: calling LLM for quiz ch=%s outcomes=%s q=%s",
        row.id,
        context["chapter_number"],
        len(context["outcomes"]),
        req.question_count,
    )
    quiz = provider.generate_structured(
        system=QUIZ_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=QuizOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    outcome_code_to_id = _load_outcome_code_map(db, row.chapter_id)
    created_count = 0
    unresolved_codes: list[str] = []
    for llm_q in quiz.questions:
        outcome_id = outcome_code_to_id.get(llm_q.outcome_code) if llm_q.outcome_code else None
        if llm_q.outcome_code and outcome_id is None:
            unresolved_codes.append(llm_q.outcome_code)

        db.add(_question_from_llm(llm_q, row=row, outcome_id=outcome_id))
        created_count += 1

    row.output_json = quiz.model_dump(mode="json")
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None
    if unresolved_codes:
        log.info(
            "generation job %s: %s questions had outcome_codes not found for chapter %s: %s",
            row.id,
            len(unresolved_codes),
            row.chapter_id,
            sorted(set(unresolved_codes)),
        )


def _question_from_llm(
    llm_q: WorksheetQuestion,
    *,
    row: GeneratedContent,
    outcome_id: int | None,
) -> Question:
    options_payload = {"choices": list(llm_q.options)} if llm_q.options else None
    # The LLM emits a 6-level Bloom string; coerce to the canonical enum.
    cognitive = BloomLevel(llm_q.cognitive_level.value)
    return Question(
        chapter_id=row.chapter_id,
        topic_id=row.topic_id,
        outcome_id=outcome_id,
        outcome_code=llm_q.outcome_code,
        type=QuestionType(llm_q.type.value),
        difficulty=QuestionDifficulty(llm_q.difficulty.value),
        cognitive_level=cognitive,
        status=QuestionStatus.DRAFT,
        text=llm_q.question,
        options=options_payload,
        correct_answer=llm_q.answer,
        explanation=llm_q.explanation,
        marks=llm_q.marks,
        source_generated_content_id=row.id,
        created_by_id=row.created_by_id,
    )


def _load_outcome_code_map(db: Session, chapter_id: int) -> dict[str, int]:
    rows = db.scalars(select(LearningOutcome).where(LearningOutcome.chapter_id == chapter_id)).all()
    return {row.code: row.id for row in rows}


def _run_lesson_plan_job(db: Session, row: GeneratedContent) -> None:
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}
    duration = int(options.get("duration_minutes", 40))

    log.info("generation job %s: calling LLM for lesson_plan ch=%s", row.id, context["chapter_number"])
    plan = provider.generate_structured(
        system=LESSON_PLAN_SYSTEM_PROMPT,
        user=build_lesson_plan_user_prompt(req, duration_minutes=duration),
        response_model=LessonPlanOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    docx_bytes = render_lesson_plan_docx(plan)
    artifact_path = get_artifact_store().save(content_id=row.id, extension="docx", data=docx_bytes)
    row.output_json = plan.model_dump(mode="json")
    row.artifact_url = artifact_path
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None


def _run_ppt_job(db: Session, row: GeneratedContent) -> None:
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}
    slide_count = int(options.get("slide_count_target", 10))

    log.info("generation job %s: calling LLM for ppt ch=%s", row.id, context["chapter_number"])
    deck = provider.generate_structured(
        system=PPT_SYSTEM_PROMPT,
        user=build_ppt_user_prompt(req, slide_count_target=slide_count),
        response_model=PPTOutlineOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    pptx_bytes = render_ppt_outline(deck)
    artifact_path = get_artifact_store().save(content_id=row.id, extension="pptx", data=pptx_bytes)
    row.output_json = deck.model_dump(mode="json")
    row.artifact_url = artifact_path
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None


def _run_diagram_job(db: Session, row: GeneratedContent) -> None:
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}

    log.info("generation job %s: calling LLM for diagram ch=%s", row.id, context["chapter_number"])
    diagram = provider.generate_structured(
        system=DIAGRAM_SYSTEM_PROMPT,
        user=build_diagram_user_prompt(req),
        response_model=DiagramOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    svg_bytes = render_concept_map_svg(diagram)
    artifact_path = get_artifact_store().save(content_id=row.id, extension="svg", data=svg_bytes)
    row.output_json = diagram.model_dump(mode="json")
    row.artifact_url = artifact_path
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None


_SIMULATION_TEMPLATES = {
    "match_pairs",
    "categorize",
    "three_d_scene",
    "timeline_order",
    "three_d_projectile",
    "three_d_orbit",
    "three_d_field_lines",
    "three_d_wave",
    "graph_explorer",
    "labeled_hotspots",
    "sentence_builder",
    "vocab_pairs",
    "molecule_3d",
    "circuit_2d",
    "custom_html",
}


def _run_simulation_job(db: Session, row: GeneratedContent) -> None:
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}

    forced_template = options.get("template")
    if forced_template is not None and forced_template not in _SIMULATION_TEMPLATES:
        raise ValueError(
            f"Unknown simulation template {forced_template!r}. "
            f"Supported: {sorted(_SIMULATION_TEMPLATES)}"
        )

    log.info(
        "generation job %s: calling LLM for simulation ch=%s (template=%s)",
        row.id,
        context["chapter_number"],
        forced_template or "auto",
    )
    sim = provider.generate_structured(
        system=SIMULATION_SYSTEM_PROMPT,
        user=build_simulation_user_prompt(req, forced_template=forced_template),
        response_model=SimulationOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    html_bytes = render_simulation_html(sim)
    artifact_path = get_artifact_store().save(content_id=row.id, extension="html", data=html_bytes)
    row.output_json = sim.model_dump(mode="json")
    row.artifact_url = artifact_path
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None


def _run_chapter_summary_job(db: Session, row: GeneratedContent) -> None:
    """Generate a structured, JSON-only chapter summary.

    No artifact file: the frontend renders directly from `output_json` so
    the mind-maps stay interactive (and we avoid PDF/HTML export overhead
    for an on-screen-only feature).
    """
    req, context = _build_request(db, row)
    provider = get_llm_provider()
    options = row.request_options or {}

    log.info(
        "generation job %s: calling LLM for chapter_summary ch=%s",
        row.id, context["chapter_number"],
    )
    summary = provider.generate_structured(
        system=CHAPTER_SUMMARY_SYSTEM_PROMPT,
        user=build_chapter_summary_user_prompt(req),
        response_model=ChapterSummaryOutput,
        temperature=float(options.get("temperature", 0.3)),
    )

    row.output_json = summary.model_dump(mode="json")
    row.source_context = context["chapter_text"][:4000]
    row.status = GeneratedContentStatus.READY
    row.error_message = None
