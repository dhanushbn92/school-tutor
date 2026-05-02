from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    is_platform_admin,
    require_platform_admin,
)
from app.core.boards import VALID_BOARDS, is_valid_board
from app.db.session import get_db
from app.models.school import School, User
from app.schemas.curriculum import (
    BookRead,
    BootstrapChapterResponse,
    BootstrapJobInfoOut,
    BulkOutcomesRequest,
    BulkTopicsRequest,
    ChapterDetailRead,
    ChapterRead,
    CreateBookRequest,
    CreateChapterRequest,
    CreateSubjectRequest,
    CurriculumContextRead,
    ExtractTopicsRequest,
    ExtractedPdfTextResponse,
    LearningOutcomesResponse,
    SchoolClassRead,
    SubjectRead,
    TopicTextExtractionError,
    TopicTextExtractionResponse,
    TopicsResponse,
)
from app.models.curriculum import Book, SchoolClass, Subject
from app.services import curriculum_service
from app.services.curriculum_ingest_service import (
    IngestError,
    bootstrap_chapter_content,
    bulk_replace_learning_outcomes,
    bulk_replace_topics,
    create_chapter,
    extract_pdf_text_only,
    extract_topic_texts_for_chapter,
    extract_topics_with_ai,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

# Hard cap so a 200 MB upload doesn't OOM the server. NCERT chapter PDFs
# are usually under 5 MB; we leave plenty of headroom for scanned PDFs
# while still rejecting obvious abuse.
_PDF_UPLOAD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("/classes", response_model=list[SchoolClassRead])
def get_classes(db: Session = Depends(get_db)):
    return curriculum_service.list_classes(db)


@router.get("/subjects", response_model=list[SubjectRead])
def get_subjects(
    class_level: int | None = Query(default=None, ge=1, le=12),
    board: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List subjects.

    Board scoping rules:
      - Platform admin sees everything; respects an explicit `board`
        query param if passed (so they can browse a single board's
        catalogue while curating).
      - Other users (school admin, teacher, student, individual learner)
        are auto-scoped to their school's board so the picker doesn't
        surface NIOS subjects to a CBSE school. The `board` query param
        is ignored for non-admins so the client can't broaden the scope
        by spoofing the URL.
    """
    effective_board = board
    if not is_platform_admin(user):
        # Resolve the user's school board. Personal-school users
        # (individual learners) inherit their school's board the same
        # way; the signup flow assigns one.
        school = db.get(School, user.school_id) if user.school_id else None
        effective_board = school.board if school else None
    return curriculum_service.list_subjects(
        db,
        class_level=class_level,
        board=effective_board,
    )


@router.get("/books", response_model=list[BookRead])
def get_books(subject_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    return curriculum_service.list_books(db, subject_id=subject_id, academic_year=academic_year)


@router.post("/subjects", response_model=SubjectRead, status_code=201)
def post_create_subject(
    payload: CreateSubjectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Create a new subject under an existing class for a given board.
    Used to seed NIOS / ICSE / State Board subjects without dropping to
    a script."""
    if not is_valid_board(payload.board):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown board {payload.board!r}. Allowed: {list(VALID_BOARDS)}.",
        )
    cls = db.get(SchoolClass, payload.class_id)
    if cls is None:
        raise HTTPException(
            status_code=400, detail=f"Class {payload.class_id} not found"
        )
    # The DB has a unique constraint on (class_id, name, language, board)
    # — relying on that for the dup check, but we surface a friendly
    # message before the IntegrityError fires.
    existing = db.scalar(
        select(Subject).where(
            Subject.class_id == payload.class_id,
            Subject.name == payload.name,
            Subject.language == payload.language,
            Subject.board == payload.board,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"A {payload.board} {payload.name} subject already exists "
                f"under this class (id={existing.id})."
            ),
        )
    subject = Subject(
        class_id=payload.class_id,
        name=payload.name.strip(),
        language=payload.language.strip(),
        board=payload.board,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.post("/books", response_model=BookRead, status_code=201)
def post_create_book(
    payload: CreateBookRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Create a new book under an existing subject. Mirrors the shape of
    NCERT manifest book entries — `ncert_code` is the curriculum vendor's
    book code (a slug like 'lemc101'); for non-NCERT boards, use any
    short identifier you want."""
    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(
            status_code=400, detail=f"Subject {payload.subject_id} not found"
        )
    existing = db.scalar(
        select(Book).where(
            Book.subject_id == payload.subject_id,
            Book.ncert_code == payload.ncert_code,
            Book.academic_year == payload.academic_year,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"A book with code {payload.ncert_code!r} already exists for "
                f"this subject in {payload.academic_year} (id={existing.id})."
            ),
        )
    book = Book(
        subject_id=payload.subject_id,
        title=payload.title.strip(),
        ncert_code=payload.ncert_code.strip(),
        academic_year=payload.academic_year.strip(),
        source_url=payload.source_url,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/chapters", response_model=list[ChapterRead])
def get_chapters(
    class_level: int | None = Query(default=None, ge=1, le=12),
    subject_id: int | None = None,
    book_id: int | None = None,
    academic_year: str | None = None,
    db: Session = Depends(get_db),
):
    return curriculum_service.list_chapters(
        db,
        class_level=class_level,
        subject_id=subject_id,
        book_id=book_id,
        academic_year=academic_year,
    )


@router.get("/chapters/{chapter_id}", response_model=ChapterDetailRead)
def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = curriculum_service.get_chapter_detail(db, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    # Pydantic from_attributes covers the chapter scalars; we then layer
    # the eager-loaded subject info on top so the frontend can theme the
    # chapter Learn page by subject family without an extra round-trip.
    response = ChapterDetailRead.model_validate(chapter)
    if chapter.book is not None and chapter.book.subject is not None:
        response.subject_id = chapter.book.subject.id
        response.subject_name = chapter.book.subject.name
    return response


@router.get("/context", response_model=CurriculumContextRead)
def get_context(chapter_id: int, topic_id: int | None = None, db: Session = Depends(get_db)):
    context = curriculum_service.build_curriculum_context(db, chapter_id=chapter_id, topic_id=topic_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return context


# ---------------------------------------------------------------------------
# Platform-admin chapter ingestion (UI lifts the work that previously only
# lived in `scripts/`). All endpoints below require platform admin.
# ---------------------------------------------------------------------------


@router.post("/extract-pdf-text", response_model=ExtractedPdfTextResponse)
async def post_extract_pdf_text(
    file: UploadFile = File(...),
    user: User = Depends(require_platform_admin),
):
    """Pull text + page count out of an uploaded PDF without writing any
    DB rows. Used by the "Onboard chapter" UI to pre-fill the chapter
    text box before the admin commits to creating the row."""
    if file.content_type and "pdf" not in (file.content_type or "").lower():
        # Be lenient on the content type — some browsers send odd values
        # for PDF uploads — but reject obviously wrong types up front.
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _PDF_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large; limit is {_PDF_UPLOAD_MAX_BYTES // (1024 * 1024)} MB.",
        )
    try:
        text, page_count = extract_pdf_text_only(data)
    except Exception as e:  # pypdf raises various unrelated exception types
        raise HTTPException(
            status_code=400,
            detail=f"Couldn't extract text from this PDF: {e}",
        ) from e
    return ExtractedPdfTextResponse(text=text, page_count=page_count)


@router.post("/chapters", response_model=ChapterRead, status_code=201)
def post_create_chapter(
    payload: CreateChapterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Create a chapter under an existing book. Used after the admin has
    pasted full text or extracted it from a PDF on the previous step."""
    try:
        chapter = create_chapter(
            db,
            book_id=payload.book_id,
            chapter_number=payload.chapter_number,
            title=payload.title,
            full_text=payload.full_text,
            source_url=payload.source_url,
            page_count=payload.page_count,
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return chapter


@router.post(
    "/chapters/{chapter_id}/topics",
    response_model=TopicsResponse,
)
def post_bulk_replace_topics(
    chapter_id: int,
    payload: BulkTopicsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Replace this chapter's topics with the supplied list."""
    try:
        rows = bulk_replace_topics(
            db,
            chapter_id=chapter_id,
            topics=[t.model_dump() for t in payload.topics],
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return TopicsResponse(topics=rows)  # Pydantic builds TopicRead from rows


@router.post(
    "/chapters/{chapter_id}/topics/extract",
    response_model=TopicsResponse,
)
def post_extract_topics_with_ai(
    chapter_id: int,
    payload: ExtractTopicsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Run the topic-extraction LLM prompt and upsert Topic rows. Idempotent
    by default (existing topics are returned unchanged); pass
    `overwrite=True` to clear and replace."""
    try:
        rows = extract_topics_with_ai(
            db,
            chapter_id=chapter_id,
            overwrite=payload.overwrite,
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return TopicsResponse(topics=rows)


@router.post(
    "/chapters/{chapter_id}/topics/extract-texts",
    response_model=TopicTextExtractionResponse,
)
def post_extract_topic_texts(
    chapter_id: int,
    payload: ExtractTopicsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """For each Topic on the chapter, slice the chapter's verbatim text
    down to the topic-specific portion (LLM) and store it on
    `Topic.full_text`. This populates the AI tutor's RAG context for
    topic-scoped chat sessions.

    Slow: roughly one LLM call per topic, so 30-90s for a typical
    4-8-topic chapter. The endpoint commits per-topic so a partial
    failure preserves earlier slices.

    Idempotent by default — already-populated topics are skipped. Pass
    `overwrite=True` to re-slice everything.
    """
    try:
        result = extract_topic_texts_for_chapter(
            db,
            chapter_id=chapter_id,
            overwrite=payload.overwrite,
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return TopicTextExtractionResponse(
        topics=result.topics,
        written=result.written,
        skipped=result.skipped,
        errored=result.errored,
        errors=[TopicTextExtractionError(**e) for e in result.errors],
    )


@router.post(
    "/chapters/{chapter_id}/bootstrap-content",
    response_model=BootstrapChapterResponse,
    status_code=202,
)
def post_bootstrap_chapter_content(
    chapter_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """One-click chapter bootstrap. Topic extraction runs synchronously
    so the admin sees topics immediately; topic-text slicing and every
    supported content-type generation are scheduled as background tasks
    that update their own DB rows. Returns 202 Accepted with a summary
    of what's been queued so the UI can link straight into the Content
    library to monitor progress.

    Idempotent: existing topics + GeneratedContent rows (matched by
    cache_key) are reused, not duplicated.
    """
    try:
        result = bootstrap_chapter_content(
            db,
            chapter_id=chapter_id,
            creator_user_id=user.id,
            background_tasks=background_tasks,
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return BootstrapChapterResponse(
        topics_extracted=result.topics_extracted,
        topic_texts_scheduled=result.topic_texts_scheduled,
        jobs_scheduled=[
            BootstrapJobInfoOut(
                id=j.id,
                content_type=j.content_type.value,
                status=j.status.value,
                title=j.title,
            )
            for j in result.jobs_scheduled
        ],
        jobs_reused=[
            BootstrapJobInfoOut(
                id=j.id,
                content_type=j.content_type.value,
                status=j.status.value,
                title=j.title,
            )
            for j in result.jobs_reused
        ],
    )


@router.post(
    "/chapters/{chapter_id}/learning-outcomes",
    response_model=LearningOutcomesResponse,
)
def post_bulk_replace_outcomes(
    chapter_id: int,
    payload: BulkOutcomesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Replace this chapter's learning outcomes with the supplied list."""
    try:
        rows = bulk_replace_learning_outcomes(
            db,
            chapter_id=chapter_id,
            outcomes=[o.model_dump() for o in payload.outcomes],
        )
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LearningOutcomesResponse(outcomes=rows)

