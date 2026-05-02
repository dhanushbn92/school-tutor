from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    is_platform_admin,
    require_platform_admin,
)
from app.db.session import get_db
from app.models.curriculum import BloomLevel
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType
from app.models.school import User
from app.schemas.question import ApprovalRequest, QuestionRead, QuestionUpdate
from app.services import question_service


router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionRead])
def list_questions(
    class_level: int | None = Query(default=None, ge=1, le=12),
    subject_id: int | None = Query(default=None),
    board: str | None = Query(
        default=None,
        description="Filter by board (e.g. CBSE, NIOS). Case-insensitive.",
    ),
    chapter_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    outcome_id: int | None = Query(default=None),
    outcome_code: str | None = Query(default=None),
    type: QuestionType | None = Query(default=None),
    kind: Literal["objective", "subjective"] | None = Query(default=None),
    difficulty: QuestionDifficulty | None = Query(default=None),
    cognitive_level: BloomLevel | None = Query(default=None),
    status: QuestionStatus | None = Query(default=None),
    source_generated_content_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Browse the question bank.

    Non-platform users only ever see APPROVED questions; the catalog hides
    DRAFT/REJECTED rows from teachers and students.

    `kind="objective"` matches MCQ / True-False / Fill-blank.
    `kind="subjective"` matches Short / Long answer / Case-based.
    Pass `type=...` for an exact match (overrides `kind`).
    """
    effective_status = status
    if not is_platform_admin(user):
        effective_status = QuestionStatus.APPROVED

    return question_service.list_questions(
        db,
        class_level=class_level,
        subject_id=subject_id,
        board=board,
        chapter_id=chapter_id,
        topic_id=topic_id,
        outcome_id=outcome_id,
        outcome_code=outcome_code,
        type_=type,
        kind=kind,
        difficulty=difficulty,
        cognitive_level=cognitive_level,
        status=effective_status,
        source_generated_content_id=source_generated_content_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if not is_platform_admin(user) and q.status != QuestionStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.patch("/{question_id}", response_model=QuestionRead)
def patch_question(
    question_id: int,
    patch: QuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),  # noqa: ARG001
):
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        question_service.update_question(db, q, patch.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(q)
    return q


@router.post("/{question_id}/approve", response_model=QuestionRead)
def approve_question(
    question_id: int,
    body: ApprovalRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    question_service.approve_question(
        db, q, reviewer_id=user.id, notes=body.review_notes if body else None
    )
    db.commit()
    db.refresh(q)
    return q


@router.post("/{question_id}/reject", response_model=QuestionRead)
def reject_question(
    question_id: int,
    body: ApprovalRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    question_service.reject_question(
        db, q, reviewer_id=user.id, notes=body.review_notes if body else None
    )
    db.commit()
    db.refresh(q)
    return q
