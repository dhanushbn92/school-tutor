"""School-tenant management.

Every endpoint here is school-scoped via the caller's `user.school_id`.
Cross-tenant reads/writes are not possible: the routes always derive the
target school from the JWT, never from a path/query parameter.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_school_admin,
    require_teacher_or_school_admin,
)
from app.auth.security import hash_password
from app.db.session import get_db
from app.models.curriculum import AcademicYear, SchoolClass
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    Teacher,
    User,
    UserRole,
)
from app.schemas.school import (
    CreateEnrollmentRequest,
    CreateSectionRequest,
    EnrollmentRead,
    SchoolRead,
    SchoolUpdate,
    SectionRead,
    StudentRead,
    TeacherRead,
    TeacherSubjectsRead,
    TeacherSubjectsSet,
)
from app.services import school_service


router = APIRouter(tags=["schools"])


# ---------- /schools/me ----------

@router.get("/schools/me", response_model=SchoolRead)
def get_my_school(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.school_id is None:
        raise HTTPException(status_code=404, detail="You are not associated with a school")
    school = db.get(School, user.school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.patch("/schools/me", response_model=SchoolRead)
def patch_my_school(
    payload: SchoolUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school to update")
    school = db.get(School, user.school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    updates = payload.model_dump(exclude_unset=True)
    # Validate board if it's being changed. We import lazily to keep
    # this route file lean — the dependency is only relevant on this
    # one branch.
    if "board" in updates and updates["board"] is not None:
        from app.core.boards import VALID_BOARDS, is_valid_board
        if not is_valid_board(updates["board"]):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown board {updates['board']!r}. Allowed: {list(VALID_BOARDS)}.",
            )
    for field, value in updates.items():
        setattr(school, field, value)
    db.commit()
    db.refresh(school)
    return school


# ---------- /sections ----------

@router.post("/sections", response_model=SectionRead, status_code=201)
def create_section(
    payload: CreateSectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")

    klass = db.get(SchoolClass, payload.class_id)
    if klass is None:
        raise HTTPException(status_code=400, detail=f"class_id {payload.class_id} not found")
    try:
        school_service.assert_class_level_in_mvp_scope(klass.level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if db.get(AcademicYear, payload.academic_year_id) is None:
        raise HTTPException(status_code=400, detail="academic_year_id not found")

    if payload.class_teacher_id is not None:
        teacher = db.get(Teacher, payload.class_teacher_id)
        if teacher is None or teacher.school_id != user.school_id:
            raise HTTPException(
                status_code=400,
                detail="class_teacher_id does not belong to this school",
            )

    section = Section(
        school_id=user.school_id,
        class_id=payload.class_id,
        academic_year_id=payload.academic_year_id,
        name=payload.name,
        class_teacher_id=payload.class_teacher_id,
    )
    db.add(section)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A section with that class + year + name already exists in this school",
        ) from exc
    db.refresh(section)
    return school_service.enrich_section(db, section)


# ---------- /teachers ----------

class CreateTeacherRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    qualification: str | None = Field(default=None, max_length=200)


@router.post("/teachers", response_model=TeacherRead, status_code=201)
def create_teacher(
    payload: CreateTeacherRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")
    if db.scalar(select(User).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(status_code=409, detail="That email is already registered")

    teacher_user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.TEACHER,
        full_name=payload.full_name,
        school_id=user.school_id,
        is_active=True,
    )
    db.add(teacher_user)
    db.flush()
    teacher = Teacher(
        user_id=teacher_user.id,
        school_id=user.school_id,
        full_name=payload.full_name,
        qualification=payload.qualification,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/teachers", response_model=list[TeacherRead])
def list_teachers(
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    if user.school_id is None:
        return []
    return list(
        db.scalars(
            select(Teacher).where(Teacher.school_id == user.school_id).order_by(Teacher.full_name)
        )
    )


def _load_teacher_in_school(db: Session, *, teacher_id: int, school_id: int) -> Teacher:
    """Look up a teacher and assert they belong to the caller's school.

    Returning 404 (not 403) when the teacher exists in another tenant — we
    never want to confirm cross-tenant existence to the caller.
    """
    teacher = db.get(Teacher, teacher_id)
    if teacher is None or teacher.school_id != school_id:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.get(
    "/teachers/{teacher_id}/subjects",
    response_model=TeacherSubjectsRead,
)
def get_teacher_subjects(
    teacher_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")
    teacher = _load_teacher_in_school(db, teacher_id=teacher_id, school_id=user.school_id)
    subject_ids, is_explicit = school_service.available_subject_ids_for_teacher(db, teacher)
    return TeacherSubjectsRead(
        teacher_id=teacher.id,
        subject_ids=subject_ids,
        is_explicit=is_explicit,
    )


@router.put(
    "/teachers/{teacher_id}/subjects",
    response_model=TeacherSubjectsRead,
)
def set_teacher_subjects(
    teacher_id: int,
    payload: TeacherSubjectsSet,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    """Replace a teacher's full subject-assignment list.

    Pass `subject_ids: []` to clear all assignments and return the teacher
    to the implicit "all subjects of class-teacher classes" fallback.
    """
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")
    teacher = _load_teacher_in_school(db, teacher_id=teacher_id, school_id=user.school_id)
    try:
        school_service.set_teacher_subject_ids(
            db, teacher_id=teacher.id, subject_ids=payload.subject_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    subject_ids, is_explicit = school_service.available_subject_ids_for_teacher(db, teacher)
    return TeacherSubjectsRead(
        teacher_id=teacher.id,
        subject_ids=subject_ids,
        is_explicit=is_explicit,
    )


# ---------- /students ----------

class CreateStudentRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    roll_number: str | None = Field(default=None, max_length=40)
    dob: date | None = None
    gender: str | None = Field(default=None, max_length=1)
    guardian_name: str | None = Field(default=None, max_length=200)
    guardian_phone: str | None = Field(default=None, max_length=40)
    # Optional: also create a login account for the student.
    login_email: EmailStr | None = None
    login_password: str | None = Field(default=None, min_length=8, max_length=128)


@router.post("/students", response_model=StudentRead, status_code=201)
def create_student(
    payload: CreateStudentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")

    student_user_id: int | None = None
    if payload.login_email is not None:
        if payload.login_password is None:
            raise HTTPException(
                status_code=400,
                detail="login_password required when login_email is provided",
            )
        if db.scalar(select(User).where(User.email == payload.login_email.lower())) is not None:
            raise HTTPException(status_code=409, detail="That email is already registered")
        student_user = User(
            email=payload.login_email.lower(),
            hashed_password=hash_password(payload.login_password),
            role=UserRole.STUDENT,
            full_name=payload.full_name,
            school_id=user.school_id,
            is_active=True,
        )
        db.add(student_user)
        db.flush()
        student_user_id = student_user.id

    student = Student(
        user_id=student_user_id,
        school_id=user.school_id,
        full_name=payload.full_name,
        roll_number=payload.roll_number,
        dob=payload.dob,
        gender=payload.gender,
        guardian_name=payload.guardian_name,
        guardian_phone=payload.guardian_phone,
    )
    db.add(student)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A student with that roll number already exists in this school",
        ) from exc
    db.refresh(student)
    return student


@router.get("/students", response_model=list[StudentRead])
def list_students(
    section_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    if user.school_id is None:
        return []
    if section_id is not None:
        section = db.get(Section, section_id)
        if section is None or section.school_id != user.school_id:
            raise HTTPException(status_code=403, detail="Section is not in your school")
        return school_service.list_students_in_section(db, section_id=section_id, user=user)
    return list(
        db.scalars(
            select(Student)
            .where(Student.school_id == user.school_id)
            .order_by(Student.full_name)
        )
    )


# ---------- /enrollments ----------

@router.post("/enrollments", response_model=EnrollmentRead, status_code=201)
def create_enrollment(
    payload: CreateEnrollmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_school_admin),
):
    if user.school_id is None:
        raise HTTPException(status_code=400, detail="No school context")

    student = db.get(Student, payload.student_id)
    if student is None or student.school_id != user.school_id:
        raise HTTPException(status_code=400, detail="Student does not belong to this school")
    section = db.get(Section, payload.section_id)
    if section is None or section.school_id != user.school_id:
        raise HTTPException(status_code=400, detail="Section does not belong to this school")
    if db.get(AcademicYear, payload.academic_year_id) is None:
        raise HTTPException(status_code=400, detail="academic_year_id not found")

    enrollment = Enrollment(
        student_id=payload.student_id,
        section_id=payload.section_id,
        academic_year_id=payload.academic_year_id,
        status=EnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="That student is already enrolled in that section for that year",
        ) from exc
    db.refresh(enrollment)
    return enrollment


# ---------- /academic-years (public catalog) ----------

class AcademicYearRead(BaseModel):
    id: int
    name: str
    is_current: bool

    model_config = {"from_attributes": True}


@router.get("/academic-years", response_model=list[AcademicYearRead])
def list_academic_years(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),  # noqa: ARG001 — auth gate only
):
    return list(
        db.scalars(select(AcademicYear).order_by(AcademicYear.name.desc()))
    )
