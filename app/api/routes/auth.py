from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.boards import VALID_BOARDS, is_valid_board
from app.core.config import get_settings
from app.db.session import get_db
from app.models.curriculum import AcademicYear, SchoolClass
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    User,
    UserRole,
)
from app.schemas.auth import (
    IndividualSignupRequest,
    IndividualSignupResponse,
    SchoolSignupRequest,
    SchoolSignupResponse,
    TokenResponse,
    UserRead,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    # Tenant kill-switch: block login for any user belonging to a disabled
    # non-personal school. Mirrors the check in `get_current_user` so a
    # disabled school can't even mint fresh tokens.
    if user.school_id is not None:
        school = db.get(School, user.school_id)
        if school is not None and not school.is_personal and not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your school has been disabled by the platform team. Please contact support.",
            )

    settings = get_settings()
    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        school_id=user.school_id,
    )
    return TokenResponse(access_token=token, expires_in=settings.jwt_ttl_minutes * 60)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/signup-school", response_model=SchoolSignupResponse, status_code=201)
def signup_school(payload: SchoolSignupRequest, db: Session = Depends(get_db)):
    """Public onboarding: create a new school + its first school-admin user.

    No tenant scope (this IS how a school becomes a tenant). The admin is
    issued a JWT immediately so the SPA can drop them straight into their
    dashboard.
    """
    if not is_valid_board(payload.board):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown board {payload.board!r}. Allowed: {list(VALID_BOARDS)}.",
        )
    existing = db.scalar(select(User).where(User.email == payload.admin_email.lower()))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered.",
        )

    school = School(
        name=payload.school_name,
        board=payload.board,
        address=payload.address,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        is_personal=False,
    )
    db.add(school)
    db.flush()

    user = User(
        email=payload.admin_email.lower(),
        hashed_password=hash_password(payload.admin_password),
        role=UserRole.SCHOOL_ADMIN,
        full_name=payload.admin_full_name,
        school_id=school.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    settings = get_settings()
    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        school_id=user.school_id,
    )
    return SchoolSignupResponse(
        user=UserRead.model_validate(user),
        school_id=school.id,
        token=TokenResponse(access_token=token, expires_in=settings.jwt_ttl_minutes * 60),
    )


@router.post("/signup-individual", response_model=IndividualSignupResponse, status_code=201)
def signup_individual(payload: IndividualSignupRequest, db: Session = Depends(get_db)):
    """Public self-signup for an individual learner.

    Implementation: each individual gets a hidden personal `School` row
    (`is_personal=True`), a `Section`, a `Student` row mapped to the user,
    and an active `Enrollment`. This 'school of one' lets every assessment /
    submission / mastery code path keep working without parallel models.
    """
    if db.scalar(select(User).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered.",
        )

    klass = db.scalar(select(SchoolClass).where(SchoolClass.level == payload.class_level))
    if klass is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Class {payload.class_level} is not configured on the platform.",
        )

    if payload.academic_year_id is not None:
        year = db.get(AcademicYear, payload.academic_year_id)
        if year is None:
            raise HTTPException(status_code=400, detail="academic_year_id not found")
    else:
        year = db.scalar(select(AcademicYear).where(AcademicYear.is_current.is_(True)))
        if year is None:
            year = db.scalar(select(AcademicYear).order_by(AcademicYear.id.desc()))
        if year is None:
            raise HTTPException(
                status_code=500,
                detail="No academic year configured on the platform.",
            )

    # Personal school: name from the learner; flagged is_personal so the
    # frontend can hide school-mgmt UI for these tenants.
    school = School(
        name=f"{payload.full_name} (personal)",
        board="—",
        is_personal=True,
    )
    db.add(school)
    db.flush()

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.INDIVIDUAL_LEARNER,
        full_name=payload.full_name,
        school_id=school.id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    section = Section(
        school_id=school.id,
        class_id=klass.id,
        academic_year_id=year.id,
        name="solo",
        class_teacher_id=None,
    )
    db.add(section)
    db.flush()

    student = Student(
        user_id=user.id,
        school_id=school.id,
        full_name=payload.full_name,
        roll_number=None,
    )
    db.add(student)
    db.flush()

    db.add(
        Enrollment(
            student_id=student.id,
            section_id=section.id,
            academic_year_id=year.id,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    db.commit()
    db.refresh(user)

    settings = get_settings()
    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        school_id=user.school_id,
    )
    return IndividualSignupResponse(
        user=UserRead.model_validate(user),
        school_id=school.id,
        section_id=section.id,
        student_id=student.id,
        token=TokenResponse(access_token=token, expires_in=settings.jwt_ttl_minutes * 60),
    )
