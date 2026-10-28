"""Public smart-speaker / voice integration API.

A single shared secret (``X-API-Key``, matched against ``SMART_SPEAKER_API_KEY``)
gates every call; the device names the learner with ``X-User-Email``. This is
the shared-key auth model — simple for a device to send, but a leaked key
exposes any user whose email is known, so keep the key secret and rotate it if
it leaks. Identity travels in a header (never the URL) so the learner's email
is not logged in query strings.

Endpoints
---------
GET  /smart-speaker/subjects            list the learner's subjects
GET  /smart-speaker/progress            subject-wise progress (all subjects)
GET  /smart-speaker/progress/{subject}  one subject's progress, per chapter
GET  /smart-speaker/summary             a chapter summary to read aloud
POST /smart-speaker/tests/start         begin a turn-by-turn quiz
POST /smart-speaker/tests/answer        submit one spoken answer, get verdict
POST /smart-speaker/tests/more          "tell me more" / another example

Every response includes a ready-to-speak ``spoken`` string.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.school import School, User
from app.schemas.smart_speaker import (
    AnswerRequest,
    AnswerResponse,
    ChapterSummaryResponse,
    ExplainMoreRequest,
    ExplainMoreResponse,
    ProgressResponse,
    StartTestRequest,
    StartTestResponse,
    SubjectListResponse,
    SubjectProgress,
)
from app.services import smart_speaker_service as svc
from app.services.smart_speaker_service import SpeakerError

router = APIRouter(prefix="/smart-speaker", tags=["smart-speaker"])


def require_speaker(
    x_api_key: str = Header(..., alias="X-API-Key"),
    x_user_email: str = Header(..., alias="X-User-Email"),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate a device call: shared key + learner email.

    The key is compared in constant time to avoid a timing oracle. Identity is
    the email header (kept out of the URL). Returns the resolved active User.
    """
    settings = get_settings()
    configured = settings.smart_speaker_api_key
    if not configured:
        raise HTTPException(status_code=503, detail="Smart speaker API is not enabled.")
    if not hmac.compare_digest((x_api_key or "").encode("utf-8"), configured.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    email = (x_user_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Missing user identity.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Unknown or inactive user.")
    # Same tenant kill-switch as get_current_user: a disabled (non-personal)
    # school's learners are locked out of the speaker API as well.
    if user.school_id is not None:
        school = db.get(School, user.school_id)
        if school is not None and not school.is_personal and not school.is_active:
            raise HTTPException(status_code=401, detail="Your school has been disabled.")
    return user


def _handle(exc: SpeakerError) -> HTTPException:
    detail: dict = {"message": exc.message}
    detail.update(exc.extra)
    return HTTPException(status_code=exc.status_code, detail=detail)


@router.get("/subjects", response_model=SubjectListResponse)
def list_subjects(
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.list_subjects(db, user)
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.all_progress(db, user)
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.get("/progress/{subject}", response_model=SubjectProgress)
def get_subject_progress(
    subject: str,
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.subject_progress(db, user, subject)
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.get("/summary", response_model=ChapterSummaryResponse)
def get_summary(
    subject: str = Query(..., min_length=1, max_length=120),
    chapter_id: int | None = Query(default=None),
    chapter_number: int | None = Query(default=None),
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.chapter_summary(
            db, user, subject_ref=subject, chapter_id=chapter_id, chapter_number=chapter_number
        )
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.post("/tests/start", response_model=StartTestResponse, status_code=201)
def start_test(
    payload: StartTestRequest,
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.start_test(
            db,
            user,
            subject_ref=payload.subject,
            chapter_id=payload.chapter_id,
            chapter_number=payload.chapter_number,
            question_count=payload.question_count,
        )
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.post("/tests/answer", response_model=AnswerResponse)
def submit_answer(
    payload: AnswerRequest,
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.answer(
            db, user, session_token=payload.session_token, answer_text=payload.answer_text
        )
    except SpeakerError as exc:
        raise _handle(exc) from exc


@router.post("/tests/more", response_model=ExplainMoreResponse)
def explain_more(
    payload: ExplainMoreRequest,
    user: User = Depends(require_speaker),
    db: Session = Depends(get_db),
):
    try:
        return svc.explain_more(
            db,
            user,
            session_token=payload.session_token,
            question_id=payload.question_id,
            kind=payload.kind,
        )
    except SpeakerError as exc:
        raise _handle(exc) from exc
