"""Re-render an artifact from a row's stored ``output_json``.

Used in two places:

* The ``GET /generated-content/{id}/artifact`` route, as an auto-heal
  step before returning 410. If the file on disk is missing but
  ``output_json`` is intact, we can rebuild the artifact deterministically
  — the SPA never sees a 410 unless the row itself is corrupt.

* The ``scripts/repair_missing_artifacts.py`` one-shot, which sweeps every
  READY/APPROVED row whose file is missing and rebuilds it.

The helper is content-type aware: each ``GeneratedContentType`` either
has a renderer (six of them do) or is JSON-only (``chapter_summary``,
``flow_diagram``, ``classroom_activity``, ``resource_list``,
``extra_content``) — those get returned as ``None`` so callers can
short-circuit.

Worksheet rendering needs extra context (class level, subject name,
chapter title, answer-key flag) which we resolve from the chapter
relationship on the fly, mirroring what
``app.workers.generate._run_worksheet_job`` does.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.simulation import SimulationOutput
from app.llm.schemas.worksheet import WorksheetOutput
from app.models.curriculum import Chapter
from app.models.generation import GeneratedContent, GeneratedContentType
from app.rendering.diagram_svg import render_concept_map_svg
from app.rendering.lesson_plan_docx import render_lesson_plan_docx
from app.rendering.ppt_pptx import render_ppt_outline
from app.rendering.simulation_html import render_simulation_html
from app.rendering.worksheet_pdf import render_worksheet_pdf


# Content types whose artifact is rendered (vs JSON-only and consumed
# directly from output_json by the SPA).
RENDERABLE_TYPES: set[GeneratedContentType] = {
    GeneratedContentType.LESSON_PLAN,
    GeneratedContentType.WORKSHEET,
    GeneratedContentType.PPT,
    GeneratedContentType.DIAGRAM,
    GeneratedContentType.SIMULATION,
}


# File extension we expect for each renderable type. Used when the row
# has no ``artifact_url`` to fall back on.
EXTENSION_FOR_TYPE: dict[GeneratedContentType, str] = {
    GeneratedContentType.LESSON_PLAN: "docx",
    GeneratedContentType.WORKSHEET: "pdf",
    GeneratedContentType.PPT: "pptx",
    GeneratedContentType.DIAGRAM: "svg",
    GeneratedContentType.SIMULATION: "html",
}


class ArtifactRepairError(Exception):
    """Raised when a row cannot be re-rendered (corrupt output_json,
    schema drift, missing chapter, unsupported content type, etc)."""


def rerender_from_output_json(
    db: Session,
    row: GeneratedContent,
    *,
    request_options: dict | None = None,
) -> tuple[bytes, str]:
    """Render `row.output_json` to artifact bytes plus the file extension.

    Caller is responsible for persisting the bytes via the artifact store
    and updating ``row.artifact_url``. We return a ``(data, ext)`` tuple
    instead of writing here so the call site stays explicit about IO.
    """
    if row.content_type not in RENDERABLE_TYPES:
        raise ArtifactRepairError(
            f"content_type {row.content_type.value!r} has no on-disk artifact"
        )
    if not row.output_json:
        raise ArtifactRepairError(
            f"row {row.id}: output_json is empty — nothing to re-render from"
        )

    options = request_options or row.request_options or {}

    if row.content_type == GeneratedContentType.LESSON_PLAN:
        plan = LessonPlanOutput.model_validate(row.output_json)
        return render_lesson_plan_docx(plan), "docx"

    if row.content_type == GeneratedContentType.PPT:
        deck = PPTOutlineOutput.model_validate(row.output_json)
        return render_ppt_outline(deck), "pptx"

    if row.content_type == GeneratedContentType.DIAGRAM:
        diagram = DiagramOutput.model_validate(row.output_json)
        return render_concept_map_svg(diagram), "svg"

    if row.content_type == GeneratedContentType.SIMULATION:
        sim = SimulationOutput.model_validate(row.output_json)
        return render_simulation_html(sim), "html"

    if row.content_type == GeneratedContentType.WORKSHEET:
        # Worksheet PDF needs class/subject/chapter context that lives on
        # the chapter row, not in output_json. Fetch from the FK chain.
        if row.chapter_id is None:
            raise ArtifactRepairError(
                f"row {row.id}: worksheet has no chapter_id — can't render header"
            )
        chapter = db.get(Chapter, row.chapter_id)
        if chapter is None or chapter.book is None or chapter.book.subject is None:
            raise ArtifactRepairError(
                f"row {row.id}: chapter / book / subject missing for worksheet"
            )
        worksheet = WorksheetOutput.model_validate(row.output_json)
        pdf_bytes = render_worksheet_pdf(
            worksheet,
            class_level=row.class_level,
            subject=chapter.book.subject.name,
            chapter_title=f"Chapter {chapter.chapter_number}: {chapter.title}",
            include_answer_key=bool(options.get("include_answer_key", True)),
        )
        return pdf_bytes, "pdf"

    raise ArtifactRepairError(
        f"unhandled renderable content_type {row.content_type.value!r}"
    )


# A separate exported list of "JSON-only" types so callers (e.g. the
# SPA's content viewer) can decide whether to fetch /artifact at all.
JSON_ONLY_TYPES: set[GeneratedContentType] = {
    GeneratedContentType.CHAPTER_SUMMARY,
    GeneratedContentType.CLASSROOM_ACTIVITY,
    GeneratedContentType.RESOURCE_LIST,
    GeneratedContentType.FLOW_DIAGRAM,
    GeneratedContentType.QUIZ,
    GeneratedContentType.HALF_YEARLY_EXAM,
    GeneratedContentType.EXTRA_CONTENT,  # admin-uploaded; artifact is the upload itself
}
