"""Create two NIOS individual-learner test accounts: one for Class 10 and
one for Class 12.

The public signup endpoint caps class_level at 10 (MVP constraint), so
this helper creates the rows directly via the ORM. Each student gets:
  - a personal School (is_personal=True) with board='NIOS'
  - a User row, role=INDIVIDUAL_LEARNER
  - a Section linked to the appropriate SchoolClass
  - a Student row mapped to the user
  - an active Enrollment

Idempotent: re-running prints the existing IDs without creating duplicates.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.create_nios_test_students
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionLocal
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


@dataclass
class StudentSpec:
    email: str
    password: str
    full_name: str
    class_level: int


SPECS: list[StudentSpec] = [
    StudentSpec(
        email="nios10.student@anaadi.org",
        password="Welcome1!",
        full_name="NIOS Class 10 Student",
        class_level=10,
    ),
    StudentSpec(
        email="nios12.student@anaadi.org",
        password="Welcome1!",
        full_name="NIOS Class 12 Student",
        class_level=12,
    ),
]


def _resolve_academic_year(db) -> AcademicYear:
    year = db.scalar(select(AcademicYear).where(AcademicYear.is_current.is_(True)))
    if year is None:
        year = db.scalar(select(AcademicYear).order_by(AcademicYear.id.desc()))
    if year is None:
        raise SystemExit(
            "No AcademicYear row exists. Scaffold the platform first."
        )
    return year


def _create_one(db, spec: StudentSpec) -> dict:
    klass = db.scalar(select(SchoolClass).where(SchoolClass.level == spec.class_level))
    if klass is None:
        raise SystemExit(
            f"No SchoolClass row for level={spec.class_level}. Scaffold it first."
        )

    existing = db.scalar(select(User).where(User.email == spec.email.lower()))
    if existing is not None:
        return {
            "email": existing.email,
            "user_id": existing.id,
            "school_id": existing.school_id,
            "status": "already_exists",
        }

    year = _resolve_academic_year(db)

    school = School(
        name=f"{spec.full_name} (personal)",
        board="NIOS",  # critical — drives which Subject rows the learner sees
        is_personal=True,
    )
    db.add(school)
    db.flush()

    user = User(
        email=spec.email.lower(),
        hashed_password=hash_password(spec.password),
        role=UserRole.INDIVIDUAL_LEARNER,
        full_name=spec.full_name,
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
        full_name=spec.full_name,
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
    db.flush()

    return {
        "email": user.email,
        "user_id": user.id,
        "school_id": school.id,
        "section_id": section.id,
        "student_id": student.id,
        "class_level": spec.class_level,
        "status": "created",
    }


def main() -> None:
    db = SessionLocal()
    try:
        for spec in SPECS:
            result = _create_one(db, spec)
            db.commit()
            print(
                f"[{result['status']}] {result['email']:<35} "
                f"user_id={result['user_id']} school_id={result['school_id']}"
                + (f" class={spec.class_level} (login password: {spec.password})"
                   if result["status"] == "created" else "")
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
