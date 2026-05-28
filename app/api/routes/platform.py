"""Platform-admin tenant management surface.

Every endpoint here is gated by `require_platform_admin`. Schools and
individual learners are listed here so the platform team can view and
toggle their access. *Edits* to school details intentionally are not
exposed — that stays with the school admin. The only write here is the
activation toggle.
"""
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import require_platform_admin
from app.db.session import get_db
from app.models.school import User
from app.schemas.content_bundle import ContentBundle
from app.schemas.platform import (
    ActivationToggle,
    PlatformLearnerOverview,
    PlatformLearnerSummary,
    PlatformSchoolOverview,
    PlatformSchoolSummary,
)
from app.services import platform_service
from app.services.content_bundle_service import (
    ContentBundleError,
    ingest_bundle,
)


logger = logging.getLogger(__name__)


# Max bundle size — JSON is small, but cap to prevent abuse.
_BUNDLE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


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


# ---------- Content bundle upload ----------


@router.post("/content-bundle/ingest")
async def ingest_content_bundle(
    file: UploadFile = File(..., description="A v1.0 content-bundle JSON file."),
    dry_run: bool = Form(default=False, description="If true, validate and resolve the chapter without writing to the DB."),
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    """Upload a content-bundle JSON for a chapter.

    See `app/schemas/content_bundle.py` for the format and
    `scripts/content_bundle_examples/README.md` for an authoring guide.

    Behaviour:
      - Returns 200 + an `IngestReport`-shaped JSON on success.
      - Returns 422 with a structured `{"detail": ..., "validation_errors": [...]}`
        when the JSON doesn't match the bundle schema.
      - Returns 400 when the curriculum coordinates don't resolve
        (e.g. chapter not scaffolded yet).
      - `dry_run=true` runs the schema validation and chapter lookup,
        and reports what WOULD be loaded, without touching the DB.
    """
    # 1. Read and size-cap.
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(raw) > _BUNDLE_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Bundle too large; limit is {_BUNDLE_MAX_BYTES // (1024 * 1024)} MB.",
        )

    # 2. Parse JSON.
    try:
        payload = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8.")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"File is not valid JSON: line {exc.lineno} col {exc.colno}: {exc.msg}",
        )

    # 3. Validate against the bundle schema.
    try:
        bundle = ContentBundle.model_validate(payload)
    except ValidationError as exc:
        # Surface every field-level error so the UI can show them inline.
        errors = []
        for err in exc.errors():
            errors.append({
                "field": ".".join(str(p) for p in err.get("loc", [])),
                "message": err.get("msg", "invalid"),
                "type": err.get("type", "value_error"),
            })
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Bundle failed schema validation.",
                "errors": errors,
            },
        )

    # 4. Dry-run path: don't touch the DB.
    if dry_run:
        return {
            "dry_run": True,
            "curriculum": bundle.curriculum.model_dump(),
            "would_load": {
                "chapter_text": bundle.chapter_text is not None,
                "topics": len(bundle.topics),
                "outcomes": len(bundle.learning_outcomes),
                "questions": len(bundle.questions),
                "chapter_summary": bundle.chapter_summary is not None,
                "lesson_plan": bundle.lesson_plan is not None,
                "worksheet": bundle.worksheet is not None,
                "ppt": bundle.ppt is not None,
                "diagram": bundle.diagram is not None,
                "simulation": bundle.simulation is not None,
            },
        }

    # 5. Real ingest.
    try:
        report = ingest_bundle(db, bundle, created_by_id=user.id)
        db.commit()
    except ContentBundleError as exc:
        db.rollback()
        # Domain error (chapter not found etc.) — 400 with the readable message.
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:  # pragma: no cover — defensive
        db.rollback()
        logger.exception("content-bundle ingest failed unexpectedly")
        raise HTTPException(status_code=500, detail="Bundle ingest failed; see server logs.")

    return {
        "dry_run": False,
        "report": report.as_dict(),
    }
