"""Platform-admin tenant management surface.

Every endpoint here is gated by `require_platform_admin`. Schools and
individual learners are listed here so the platform team can view and
toggle their access. *Edits* to school details intentionally are not
exposed — that stays with the school admin. The only write here is the
activation toggle.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_platform_admin
from app.db.session import get_db
from app.models.school import User
from app.schemas.platform import (
    ActivationToggle,
    PlatformLearnerOverview,
    PlatformLearnerSummary,
    PlatformSchoolOverview,
    PlatformSchoolSummary,
)
from app.services import platform_service


router = APIRouter(prefix="/platform", tags=["platform"])


# ---------- Schools ----------


@router.get("/schools", response_model=list[PlatformSchoolSummary])
def list_schools(
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """All non-personal schools with student/teacher/section counts."""
    del user  # auth side-effect; value not used
    return platform_service.list_schools(db)


@router.get("/schools/{school_id}", response_model=PlatformSchoolOverview)
def get_school_overview(
    school_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    del user
    payload = platform_service.school_overview(db, school_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="School not found")
    return payload


@router.post(
    "/schools/{school_id}/activation",
    response_model=PlatformSchoolSummary,
)
def toggle_school_activation(
    school_id: int,
    body: ActivationToggle,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Enable or disable a school. Cascades to every user in that school
    via the auth dependency on the next request."""
    del user
    school = platform_service.set_school_active(
        db, school_id, is_active=body.is_active
    )
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    # Return the updated row in the same shape the list uses so the SPA
    # can patch its cache without an extra round-trip.
    schools = platform_service.list_schools(db)
    for row in schools:
        if row["id"] == school.id:
            return row
    # Defensive fallback — shouldn't happen because we just toggled it.
    raise HTTPException(status_code=500, detail="School row missing after toggle")


# ---------- Individual learners ----------


@router.get("/learners", response_model=list[PlatformLearnerSummary])
def list_learners(
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    del user
    return platform_service.list_learners(db)


@router.get("/learners/{user_id}", response_model=PlatformLearnerOverview)
def get_learner_overview(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    del user
    payload = platform_service.learner_overview(db, user_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return payload


@router.post(
    "/learners/{user_id}/activation",
    response_model=PlatformLearnerSummary,
)
def toggle_learner_activation(
    user_id: int,
    body: ActivationToggle,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Enable or disable an individual learner. Takes effect on their next
    request — `get_current_user` already checks `User.is_active`."""
    del user
    learner = platform_service.set_learner_active(
        db, user_id, is_active=body.is_active
    )
    if learner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found"
        )
    learners = platform_service.list_learners(db)
    for row in learners:
        if row["user_id"] == learner.id:
            return row
    raise HTTPException(status_code=500, detail="Learner row missing after toggle")
