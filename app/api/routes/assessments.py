from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_learner,
    require_teacher_or_school_admin,
)
from app.db.session import get_db
from app.models.assessment import Assessment, Submission
from app.models.mastery import CognitiveBucket
from app.models.school import User
from app.models.question import QuestionDifficulty, QuestionType
from app.schemas.assessment import (
    AssessmentRead,
    CreateAssessmentRequest,
    FromBankRequest,
    GradeAnswerRequest,
    SubmissionRead,
    SubmitAssessmentRequest,
)
from app.services import assessment_service, question_bank_service, submission_service
from app.services.artifact_store import get_artifact_store
from app.services.assessment_service import AssessmentError
from app.services.question_bank_service import BankCoverageError
from app.services.submission_service import SubmissionError


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentRead, status_code=201)
def create_assessment(
    payload: CreateAssessmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    try:
        assessment = assessment_service.create_assessment(
            db,
            user=user,
            section_id=payload.section_id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            assessment_type=payload.type,
            title=payload.title,
            instructions=payload.instructions,
            question_ids=payload.question_ids,
            marks_overrides=payload.marks_overrides,
            duration_minutes=payload.duration_minutes,
            due_at=payload.due_at,
        )
    except AssessmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return assessment


@router.post("/from-bank", response_model=AssessmentRead, status_code=201)
def create_assessment_from_bank(
    payload: FromBankRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    """Sample APPROVED questions from the global bank to build a fresh quiz.

    Quizzes are no longer LLM-generated at request time. Platform admins
    populate the bank ahead of demand; this endpoint picks N questions
    matching the request and persists them as an Assessment.
    """
    diff_mix: dict[QuestionDifficulty, int] | None = None
    if payload.difficulty_mix is not None:
        try:
            diff_mix = {
                QuestionDifficulty(k.upper()): v for k, v in payload.difficulty_mix.items()
            }
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"difficulty_mix has unknown level: {exc}",
            ) from exc

    type_mix: dict[QuestionType, int] | None = None
    if payload.type_mix is not None:
        try:
            type_mix = {QuestionType(k.upper()): v for k, v in payload.type_mix.items()}
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"type_mix has unknown question type: {exc}",
            ) from exc

    cognitive_mix: dict[CognitiveBucket, int] | None = None
    if payload.cognitive_mix is not None:
        try:
            cognitive_mix = {
                CognitiveBucket(k.upper()): v for k, v in payload.cognitive_mix.items()
            }
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"cognitive_mix has unknown bucket: {exc}",
            ) from exc

    if payload.chapter_id is None and not payload.chapter_ids:
        raise HTTPException(
            status_code=400,
            detail="Provide chapter_id (single chapter) or chapter_ids (cumulative).",
        )
    if payload.chapter_id is not None and payload.chapter_ids:
        raise HTTPException(
            status_code=400,
            detail="Pass chapter_id OR chapter_ids, not both.",
        )

    try:
        sampled = question_bank_service.sample_questions(
            db,
            chapter_id=payload.chapter_id,
            chapter_ids=payload.chapter_ids,
            topic_id=payload.topic_id,
            count=payload.question_count,
            difficulty_mix=diff_mix,
            type_mix=type_mix,
            cognitive_mix=cognitive_mix,
        )
    except BankCoverageError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "gaps": exc.gaps},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Cumulative tests: store the first chapter_id so the assessment row stays
    # valid; the title is expected to mention all chapters covered.
    stored_chapter_id = (
        payload.chapter_id
        if payload.chapter_id is not None
        else (payload.chapter_ids[0] if payload.chapter_ids else None)
    )
    try:
        assessment = assessment_service.create_assessment(
            db,
            user=user,
            section_id=payload.section_id,
            subject_id=payload.subject_id,
            chapter_id=stored_chapter_id,
            assessment_type=payload.type,
            title=payload.title,
            instructions=payload.instructions,
            question_ids=[q.id for q in sampled],
            marks_overrides=None,
            duration_minutes=payload.duration_minutes,
            due_at=payload.due_at,
        )
    except AssessmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return assessment


@router.get("/{assessment_id}", response_model=AssessmentRead)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    # Tenant scope: only return the assessment if the caller belongs to the
    # owning school (admin/teacher) or is enrolled in its section
    # (student/individual). 404 (not 403) so we don't leak existence.
    visible_assessments = {
        a.id for a in assessment_service.list_assessments_for_user(db, user=user)
    }
    if assessment.id not in visible_assessments:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post("/{assessment_id}/publish", response_model=AssessmentRead)
def publish_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    try:
        return assessment_service.publish_assessment(db, user=user, assessment_id=assessment_id)
    except AssessmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{assessment_id}/close", response_model=AssessmentRead)
def close_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    try:
        return assessment_service.close_assessment(db, user=user, assessment_id=assessment_id)
    except AssessmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{assessment_id}/submissions", response_model=list[SubmissionRead])
def list_submissions(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    return submission_service.list_submissions_for_assessment(
        db, user=user, assessment_id=assessment_id
    )


@router.post("/{assessment_id}/submissions", response_model=SubmissionRead, status_code=201)
def submit_assessment(
    assessment_id: int,
    payload: SubmitAssessmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    try:
        return submission_service.create_submission(
            db, user=user, assessment_id=assessment_id, answers=payload.answers
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


submissions_router = APIRouter(prefix="/submissions", tags=["submissions"])


@submissions_router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.assessment import Assessment as AssessmentModel
    from app.models.school import Student as StudentModel, UserRole

    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Students and individual learners may read only their own submissions.
    if user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        student = db.scalar(select(StudentModel).where(StudentModel.user_id == user.id))
        if student is None or submission.student_id != student.id:
            raise HTTPException(status_code=404, detail="Submission not found")
        return submission

    # School admins / teachers may read submissions belonging to their tenant
    # (admin = any section in school; teacher = sections they class-teach).
    if user.role in (UserRole.SCHOOL_ADMIN, UserRole.TEACHER):
        assessment = db.get(AssessmentModel, submission.assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        if not submission_service._user_can_grade_submission_section(
            db, user, assessment.section_id
        ):
            raise HTTPException(status_code=404, detail="Submission not found")
        return submission

    # Platform admin should not peek at tenant submissions.
    raise HTTPException(status_code=404, detail="Submission not found")


@submissions_router.patch(
    "/{submission_id}/answers/{question_id}", response_model=SubmissionRead
)
def grade_answer(
    submission_id: int,
    question_id: int,
    payload: GradeAnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    try:
        submission_service.grade_answer(
            db,
            user=user,
            submission_id=submission_id,
            question_id=question_id,
            marks_awarded=payload.marks_awarded,
            teacher_remark=payload.teacher_remark,
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    submission = db.get(Submission, submission_id)
    return submission


@submissions_router.post("/{submission_id}/upload", response_model=SubmissionRead)
async def upload_submission_file(
    submission_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    if file.filename is None or "." not in file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a file with an extension")
    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in {"pdf", "png", "jpg", "jpeg"}:
        raise HTTPException(status_code=400, detail="Only PDF/PNG/JPG are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Namespace submission uploads so they don't collide with generated artifacts.
    store = get_artifact_store()
    saved_name = store.save(
        content_id=submission_id, extension=f"submission.{extension}", data=data
    )
    try:
        return submission_service.save_uploaded_file(
            db, user=user, submission_id=submission_id, relative_path=saved_name
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
