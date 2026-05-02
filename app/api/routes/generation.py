import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    is_platform_admin,
    require_platform_admin,
)
from app.db.session import get_db
from app.models.curriculum import AcademicYear, Book, Chapter, SchoolClass, Subject
from app.models.generation import GeneratedContent, GeneratedContentStatus, GeneratedContentType
from app.models.question import Question, QuestionStatus
from app.models.school import User
from app.schemas.generation import (
    GeneratedContentRead,
    GenerateContentRequest,
    UploadStructuredContentRequest,
)
from app.llm.schemas.chapter_summary import ChapterSummaryOutput
from app.llm.schemas.classroom_activity import ClassroomActivitySetOutput
from app.llm.schemas.diagram import DiagramOutput
from app.llm.schemas.flow_diagram import FlowDiagramOutput
from app.llm.schemas.lesson_plan import LessonPlanOutput
from app.llm.schemas.ppt import PPTOutlineOutput
from app.llm.schemas.worksheet import WorksheetOutput
from pydantic import BaseModel, ValidationError
from app.services.artifact_repair import (
    ArtifactRepairError,
    EXTENSION_FOR_TYPE,
    rerender_from_output_json,
)
from app.services.artifact_store import get_artifact_store
from app.services.generation_service import create_or_reuse_generated_content
from app.workers.generate import run_generation_job


router = APIRouter(prefix="/generated-content", tags=["generated-content"])


_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "svg": "image/svg+xml",
    "png": "image/png",
    "html": "text/html",
    "json": "application/json",
}

# Extensions whose content the browser can render in-place. We send these
# with `Content-Disposition: inline` so an authenticated direct hit on the
# URL renders instead of forcing a save dialog. DOCX/PPTX have no in-browser
# viewer, so they keep `attachment`.
_INLINE_VIEWABLE_EXTS = {"pdf", "svg", "png", "html"}


@router.get("", response_model=list[GeneratedContentRead])
def list_generated_content(
    content_type: GeneratedContentType | None = Query(default=None),
    status: GeneratedContentStatus | None = Query(default=None),
    chapter_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    subject_id: int | None = Query(default=None),
    board: str | None = Query(
        default=None,
        description="Filter by board (e.g. CBSE, NIOS). Case-insensitive.",
    ),
    class_level: int | None = Query(default=None),
    created_by_id: int | None = Query(default=None),
    academic_year: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Catalog browse. Non-platform users see only `status=approved` rows;
    platform admins see all statuses (including DRAFT/READY for review).

    `board` joins through Subject to scope to one syllabus board (CBSE / NIOS
    / ...). It's case-insensitive — pass either "CBSE" or "cbse".
    """
    stmt = select(GeneratedContent).order_by(GeneratedContent.id.desc())

    if not is_platform_admin(user):
        # Force-narrow non-platform users to the published catalog. Even if
        # the caller passes an explicit status, we drop it.
        stmt = stmt.where(GeneratedContent.status == GeneratedContentStatus.APPROVED)
    elif status is not None:
        stmt = stmt.where(GeneratedContent.status == status)

    if content_type is not None:
        stmt = stmt.where(GeneratedContent.content_type == content_type)
    if chapter_id is not None:
        stmt = stmt.where(GeneratedContent.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(GeneratedContent.topic_id == topic_id)
    if subject_id is not None:
        stmt = stmt.where(GeneratedContent.subject_id == subject_id)
    if board is not None:
        # Join through Subject so we can scope to one syllabus board.
        # GeneratedContent.subject_id is nullable, so the join is INNER —
        # rows without a subject (rare; legacy chapter-less content) are
        # excluded by design when a board filter is requested.
        stmt = stmt.join(Subject, Subject.id == GeneratedContent.subject_id).where(
            Subject.board.ilike(board)
        )
    if class_level is not None:
        stmt = stmt.where(GeneratedContent.class_level == class_level)
    if created_by_id is not None:
        stmt = stmt.where(GeneratedContent.created_by_id == created_by_id)
    if academic_year is not None:
        stmt = stmt.where(GeneratedContent.academic_year == academic_year)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.post("", response_model=GeneratedContentRead, status_code=202)
def request_generated_content(
    request: GenerateContentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Generate new content. Platform-admin only — schools and individuals
    consume the published catalog produced by this endpoint."""
    row = create_or_reuse_generated_content(db, request, creator_user_id=user.id)
    if row.status == GeneratedContentStatus.PENDING:
        background_tasks.add_task(run_generation_job, row.id)
    return row


# Permitted MIME types + extensions for the platform admin's "extra content"
# upload. PDFs render inline in the browser; DOCX/XLSX/PPTX are accepted but
# the SPA will only let users *view* them (DOCX has no in-browser renderer
# so we surface a viewer notice for those).
_EXTRA_CONTENT_ALLOWED: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # Office files served via msword content-type (older Word):
    "application/msword": "doc",
}
_EXTRA_CONTENT_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post(
    "/upload",
    response_model=GeneratedContentRead,
    status_code=201,
)
async def upload_extra_content(
    title: str = Form(..., min_length=2, max_length=200),
    class_level: int = Form(..., ge=1, le=12),
    subject_id: int = Form(...),
    chapter_id: int | None = Form(default=None),
    description: str | None = Form(default=None, max_length=500),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Upload a supplementary document (PDF / DOCX) for a chapter.

    The file is stored as the row's `artifact_url`; `output_json` carries
    the descriptive metadata. Status is set to APPROVED immediately —
    these aren't LLM drafts, they're admin-curated material — so they
    appear in the catalog right away.
    """
    # 1. Validate inputs against the curriculum.
    cls = db.scalar(select(SchoolClass).where(SchoolClass.level == class_level))
    if cls is None:
        raise HTTPException(status_code=400, detail=f"Class level {class_level} not configured")
    subject = db.get(Subject, subject_id)
    if subject is None or subject.class_id != cls.id:
        raise HTTPException(status_code=400, detail="Subject does not belong to that class")
    chapter = None
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise HTTPException(status_code=400, detail="Unknown chapter_id")
        # Confirm the chapter is part of the picked subject.
        book = db.get(Book, chapter.book_id) if chapter.book_id else None
        if book is None or book.subject_id != subject_id:
            raise HTTPException(
                status_code=400,
                detail="Chapter does not belong to that subject",
            )

    # 2. Validate file metadata.
    content_type = (file.content_type or "").lower()
    extension = _EXTRA_CONTENT_ALLOWED.get(content_type)
    if extension is None:
        # Fall back on the filename extension if the client's content-type
        # isn't one we recognise — common with Office files from older
        # browsers.
        if file.filename and "." in file.filename:
            ext_guess = file.filename.rsplit(".", 1)[-1].lower()
            if ext_guess in {"pdf", "docx", "doc"}:
                extension = ext_guess
                # Normalise the content_type header we'll serve later.
                content_type = {
                    "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "doc": "application/msword",
                }[ext_guess]
        if extension is None:
            raise HTTPException(
                status_code=400,
                detail="Only PDF or Word (.pdf, .docx) uploads are supported.",
            )

    # 3. Read with a hard size cap (don't load 1GB into memory).
    data = await file.read()
    if len(data) > _EXTRA_CONTENT_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; limit is {_EXTRA_CONTENT_MAX_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    # 4. Pick an academic year (current first, fallback to most recent).
    year = db.scalar(select(AcademicYear).where(AcademicYear.is_current.is_(True)))
    if year is None:
        year = db.scalar(select(AcademicYear).order_by(AcademicYear.id.desc()))
    if year is None:
        raise HTTPException(
            status_code=500,
            detail="No academic year configured on the platform.",
        )

    # 5. Insert the row + write the artefact.
    row = GeneratedContent(
        content_type=GeneratedContentType.EXTRA_CONTENT,
        academic_year=year.name,
        class_level=class_level,
        subject_id=subject_id,
        chapter_id=chapter.id if chapter else None,
        topic_id=None,
        title=title.strip(),
        status=GeneratedContentStatus.APPROVED,
        published_at=datetime.now(timezone.utc),
        published_by_id=user.id,
        created_by_id=user.id,
        cache_key=f"upload:{user.id}:{datetime.now(timezone.utc).isoformat()}",
        request_options={
            "uploaded_filename": file.filename or "upload",
            "content_type": content_type,
        },
        output_json={
            "title": title.strip(),
            "description": (description or "").strip() or None,
            "original_filename": file.filename or "upload",
            "size_bytes": len(data),
            "content_type": content_type,
        },
        llm_model=None,
    )
    db.add(row)
    db.flush()  # need row.id for the artifact filename

    store = get_artifact_store()
    artifact_path = store.save(content_id=row.id, extension=extension, data=data)
    row.artifact_url = artifact_path
    db.commit()
    db.refresh(row)
    return row


# --------------------------------------------------------------------------
# Structured-JSON upload (platform admin manual content creation)
#
# Maps every content_type that has a defined Pydantic output schema to the
# corresponding model class. Uploads for types NOT listed here are rejected
# with a clear "doesn't accept structured upload" error.
#
# Why not also accept quiz / half_yearly_exam: quizzes carry side effects
# (each question becomes a Question row in the bank with its own status
# lifecycle), so they need a different upload pipeline. Same with
# half_yearly_exam (not implemented anywhere yet). Those are explicit
# follow-ups; this endpoint covers the read-only inline-rendered types.
# --------------------------------------------------------------------------
_STRUCTURED_UPLOAD_SCHEMAS: dict[GeneratedContentType, type[BaseModel]] = {
    GeneratedContentType.CHAPTER_SUMMARY: ChapterSummaryOutput,
    GeneratedContentType.LESSON_PLAN: LessonPlanOutput,
    GeneratedContentType.CLASSROOM_ACTIVITY: ClassroomActivitySetOutput,
    GeneratedContentType.WORKSHEET: WorksheetOutput,
    GeneratedContentType.PPT: PPTOutlineOutput,
    GeneratedContentType.DIAGRAM: DiagramOutput,
    GeneratedContentType.FLOW_DIAGRAM: FlowDiagramOutput,
}


@router.post(
    "/upload-structured",
    response_model=GeneratedContentRead,
    status_code=201,
)
def upload_structured_content(
    payload: UploadStructuredContentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Upload hand-crafted structured content (JSON) for any schema-backed
    content type. The platform admin owns this content end-to-end; status
    is set to APPROVED immediately so it appears in the catalog without a
    further review step.

    Validation:
      - `content_type` must be one of the seven schema-backed types
      - `output_json` must validate against the matching Pydantic model
      - subject_id, chapter_id, topic_id must form a consistent FK chain
        (same checks as the extra_content upload endpoint)
    """
    # 1. content_type must be one we know how to validate.
    schema_cls = _STRUCTURED_UPLOAD_SCHEMAS.get(payload.content_type)
    if schema_cls is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"content_type '{payload.content_type.value}' doesn't support "
                f"structured upload. Supported types: "
                f"{sorted(t.value for t in _STRUCTURED_UPLOAD_SCHEMAS)}."
            ),
        )

    # 2. Validate the output_json payload against that schema.
    try:
        validated = schema_cls.model_validate(payload.output_json)
    except ValidationError as e:
        # Surface the first few errors so the admin can fix them. Raw
        # ValidationError can be huge; trim to the most useful items.
        errors = e.errors()[:5]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "output_json failed schema validation",
                "errors": [
                    {
                        "loc": ".".join(str(p) for p in err["loc"]),
                        "msg": err["msg"],
                        "type": err["type"],
                    }
                    for err in errors
                ],
            },
        ) from e

    # 3. Validate the curriculum FK chain — same rules as extra_content.
    cls = db.scalar(select(SchoolClass).where(SchoolClass.level == payload.class_level))
    if cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Class level {payload.class_level} not configured",
        )
    subject = db.get(Subject, payload.subject_id)
    if subject is None or subject.class_id != cls.id:
        raise HTTPException(
            status_code=400,
            detail="Subject does not belong to that class",
        )
    chapter = None
    if payload.chapter_id is not None:
        chapter = db.get(Chapter, payload.chapter_id)
        if chapter is None:
            raise HTTPException(status_code=400, detail="Unknown chapter_id")
        book = db.get(Book, chapter.book_id) if chapter.book_id else None
        if book is None or book.subject_id != payload.subject_id:
            raise HTTPException(
                status_code=400,
                detail="Chapter does not belong to that subject",
            )

    # 4. Pick an academic year (current first, fallback to most recent).
    year = db.scalar(select(AcademicYear).where(AcademicYear.is_current.is_(True)))
    if year is None:
        year = db.scalar(select(AcademicYear).order_by(AcademicYear.id.desc()))
    if year is None:
        raise HTTPException(
            status_code=500,
            detail="No academic year configured on the platform.",
        )

    # 5. Insert the row. We intentionally store the *validated* model output
    # (round-tripped through Pydantic) rather than the raw payload so any
    # default values, coerced types, or normalisations are preserved.
    now = datetime.now(timezone.utc)
    row = GeneratedContent(
        content_type=payload.content_type,
        academic_year=year.name,
        class_level=payload.class_level,
        subject_id=payload.subject_id,
        chapter_id=chapter.id if chapter else None,
        topic_id=payload.topic_id,
        title=payload.title.strip(),
        status=GeneratedContentStatus.APPROVED,
        published_at=now,
        published_by_id=user.id,
        created_by_id=user.id,
        cache_key=f"upload:struct:{user.id}:{now.isoformat()}",
        request_options={"source": "manual_structured_upload"},
        output_json=validated.model_dump(),
        llm_model=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{content_id}", response_model=GeneratedContentRead)
def get_generated_content(
    content_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated content not found")
    if not is_platform_admin(user) and row.status != GeneratedContentStatus.APPROVED:
        # Non-platform users can't peek at unpublished generations.
        raise HTTPException(status_code=404, detail="Generated content not found")
    return row


@router.get("/{content_id}/artifact")
def download_artifact(
    content_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated content not found")

    # Non-platform users can only download published artifacts.
    if not is_platform_admin(user) and row.status != GeneratedContentStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Generated content not found")

    if row.status not in (GeneratedContentStatus.READY, GeneratedContentStatus.APPROVED):
        raise HTTPException(status_code=409, detail=f"Artifact not ready (status={row.status.value})")

    store = get_artifact_store()

    # Auto-heal: if the on-disk file is missing (or the row never had
    # one because a previous render crashed half-way), re-render from
    # the stored output_json and persist before serving. This means
    # accidental file-store drift is invisible to the SPA — the user
    # never sees a 410 unless the row itself is corrupt.
    needs_rerender = (not row.artifact_url) or (not store.exists(row.artifact_url))
    if needs_rerender:
        try:
            rendered, ext = rerender_from_output_json(db, row)
        except ArtifactRepairError as exc:
            # Output_json missing / corrupt / content type without a
            # renderer. Surface 410 with the actual reason so the
            # platform admin gets useful triage info instead of the
            # generic "file missing on disk".
            raise HTTPException(
                status_code=410,
                detail=f"Artifact missing and re-render failed: {exc}",
            ) from exc
        # Persist the freshly rendered file using the row's existing
        # filename if any; fall back to the canonical "<id>.<ext>".
        target_url = row.artifact_url or f"{row.id}.{ext}"
        target_ext = target_url.rsplit(".", 1)[-1].lower() if "." in target_url else ext
        store.save(content_id=row.id, extension=target_ext, data=rendered)
        if not row.artifact_url:
            row.artifact_url = f"{row.id}.{target_ext}"
            db.commit()

    data = store.read(row.artifact_url)
    extension = row.artifact_url.rsplit(".", 1)[-1].lower() if "." in row.artifact_url else "bin"
    media_type = _MEDIA_TYPES.get(extension, "application/octet-stream")
    raw_name = row.title or f"content-{row.id}"
    # HTTP headers must be Latin-1. Generated titles routinely contain
    # em-dashes (—), middle-dots, etc. that bust Latin-1 encoding.
    # Strategy: keep an ASCII-fallback `filename=` that's always safe AND a
    # UTF-8 `filename*=` per RFC 5987 so modern browsers preserve the
    # original characters in the download dialog.
    ascii_name = (
        unicodedata.normalize("NFKD", raw_name)
        .encode("ascii", "ignore")
        .decode("ascii")
        .replace(" ", "_")
        .strip("_") or f"content-{row.id}"
    )
    ascii_filename = f"{ascii_name}.{extension}"
    utf8_filename = f"{raw_name}.{extension}".replace(" ", "_")
    disposition_kind = "inline" if extension in _INLINE_VIEWABLE_EXTS else "attachment"
    disposition = (
        f'{disposition_kind}; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{quote(utf8_filename)}"
    )
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


@router.post("/{content_id}/publish", response_model=GeneratedContentRead)
def publish_generated_content(
    content_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Move a READY generation to APPROVED so the catalog exposes it.

    For QUIZ generations, also approves any still-DRAFT child questions in one
    pass — the catalog quiz pool only sees APPROVED questions, so an unpublished
    quiz with DRAFT child questions would never serve any traffic.
    """
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated content not found")
    if row.status != GeneratedContentStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish; current status is {row.status.value}",
        )

    row.status = GeneratedContentStatus.APPROVED
    row.published_at = datetime.now(timezone.utc)
    row.published_by_id = user.id

    if row.content_type == GeneratedContentType.QUIZ:
        drafts = db.scalars(
            select(Question).where(
                Question.source_generated_content_id == content_id,
                Question.status == QuestionStatus.DRAFT,
            )
        ).all()
        for q in drafts:
            q.status = QuestionStatus.APPROVED
            q.reviewed_by_id = user.id

    db.commit()
    db.refresh(row)
    return row


@router.post("/{content_id}/approve", response_model=dict)
def bulk_approve_questions(
    content_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Approve all DRAFT questions spawned by one generation. Distinct from
    /publish because this only moves Question rows; it does not transition the
    parent GeneratedContent to APPROVED. Useful when curating the bank
    iteratively.
    """
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated content not found")

    drafts = db.scalars(
        select(Question).where(
            Question.source_generated_content_id == content_id,
            Question.status == QuestionStatus.DRAFT,
        )
    ).all()

    approved_ids: list[int] = []
    for q in drafts:
        q.status = QuestionStatus.APPROVED
        q.reviewed_by_id = user.id
        approved_ids.append(q.id)
    db.commit()

    return {
        "generated_content_id": content_id,
        "approved_count": len(approved_ids),
        "approved_question_ids": approved_ids,
    }
