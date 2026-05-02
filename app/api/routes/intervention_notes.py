from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_teacher
from app.db.session import get_db
from app.models.school import User
from app.schemas.intervention import CreateInterventionNoteRequest, InterventionNoteRead
from app.services import intervention_service
from app.services.intervention_service import InterventionError


router = APIRouter(prefix="/intervention-notes", tags=["intervention-notes"])


@router.post("", response_model=InterventionNoteRead, status_code=201)
def create_intervention_note(
    payload: CreateInterventionNoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    try:
        return intervention_service.create_note(
            db,
            user=user,
            student_id=payload.student_id,
            note=payload.note,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
        )
    except InterventionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/students/{student_id}", response_model=list[InterventionNoteRead])
def list_notes_for_student(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return intervention_service.list_for_student(db, user=user, student_id=student_id)
