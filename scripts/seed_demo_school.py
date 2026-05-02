"""Seed one demo school for Stage 2 end-to-end testing.

Creates (all upserts are idempotent on natural keys):
- School: Anaadi Demo School (CBSE)
- Users: 1 admin, 1 Science teacher, 10 students
- Teacher: Dr. Priya Sharma, class teacher of 6-A
- Sections: 6-A, 6-B (academic year 2026-27)
- Enrollments: all 10 students in 6-A

Dev-only passwords (DO NOT use in prod):
  admin@anaadi.demo          / admin123
  priya.sharma@anaadi.demo   / teacher123
  student01@anaadi.demo ...  / student123

Usage:
    .venv/Scripts/python.exe -m scripts.seed_demo_school
"""
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
    Teacher,
    User,
    UserRole,
)


SCHOOL_NAME = "Anaadi Demo School"
ACADEMIC_YEAR = "2026-27"

ADMIN_EMAIL = "admin@anaadi.demo"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Anaadi Demo Admin"

# Extra admin credentials. Append more dicts to add additional admins/principals.
EXTRA_ADMINS: list[dict[str, str]] = [
    {
        "email": "school.demo@anaadi.org",
        "password": "demo@123",
        "full_name": "Anaadi School Demo",
    },
]

TEACHER_EMAIL = "priya.sharma@anaadi.demo"
TEACHER_PASSWORD = "teacher123"
TEACHER_NAME = "Dr. Priya Sharma"
TEACHER_QUALIFICATION = "M.Sc. Zoology, B.Ed."

STUDENT_NAMES = [
    "Aarav Mehta",
    "Ananya Iyer",
    "Aryan Khan",
    "Diya Patel",
    "Ishaan Reddy",
    "Kabir Singh",
    "Meera Joshi",
    "Nikhil Rao",
    "Riya Banerjee",
    "Saanvi Nair",
]
STUDENT_PASSWORD = "student123"


def _upsert_user(db, *, email: str, password: str, role: UserRole, full_name: str, school_id: int | None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            full_name=full_name,
            school_id=school_id,
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.role = role
        user.full_name = full_name
        user.school_id = school_id
        if not user.hashed_password:
            user.hashed_password = hash_password(password)
    return user


def main() -> None:
    with SessionLocal() as db:
        school = db.scalar(select(School).where(School.name == SCHOOL_NAME))
        if school is None:
            school = School(name=SCHOOL_NAME, board="CBSE", contact_email="info@anaadi.demo")
            db.add(school)
            db.flush()

        academic_year = db.scalar(select(AcademicYear).where(AcademicYear.name == ACADEMIC_YEAR))
        if academic_year is None:
            academic_year = AcademicYear(name=ACADEMIC_YEAR, is_current=True)
            db.add(academic_year)
            db.flush()

        class_6 = db.scalar(select(SchoolClass).where(SchoolClass.level == 6))
        if class_6 is None:
            class_6 = SchoolClass(level=6, display_name="Class 6")
            db.add(class_6)
            db.flush()

        for extra in EXTRA_ADMINS:
            _upsert_user(
                db,
                email=extra["email"],
                password=extra["password"],
                role=UserRole.ADMIN,
                full_name=extra["full_name"],
                school_id=school.id,
            )

        admin = _upsert_user(
            db,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            role=UserRole.ADMIN,
            full_name=ADMIN_NAME,
            school_id=school.id,
        )

        teacher_user = _upsert_user(
            db,
            email=TEACHER_EMAIL,
            password=TEACHER_PASSWORD,
            role=UserRole.TEACHER,
            full_name=TEACHER_NAME,
            school_id=school.id,
        )
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == teacher_user.id))
        if teacher is None:
            teacher = Teacher(
                user_id=teacher_user.id,
                school_id=school.id,
                full_name=TEACHER_NAME,
                qualification=TEACHER_QUALIFICATION,
            )
            db.add(teacher)
            db.flush()
        else:
            teacher.full_name = TEACHER_NAME
            teacher.qualification = TEACHER_QUALIFICATION

        section_a = _upsert_section(
            db,
            school_id=school.id,
            class_id=class_6.id,
            academic_year_id=academic_year.id,
            name="A",
            class_teacher_id=teacher.id,
        )
        section_b = _upsert_section(
            db,
            school_id=school.id,
            class_id=class_6.id,
            academic_year_id=academic_year.id,
            name="B",
            class_teacher_id=None,
        )

        for index, full_name in enumerate(STUDENT_NAMES, start=1):
            email = f"student{index:02d}@anaadi.demo"
            roll_number = f"6A-{index:02d}"
            student_user = _upsert_user(
                db,
                email=email,
                password=STUDENT_PASSWORD,
                role=UserRole.STUDENT,
                full_name=full_name,
                school_id=school.id,
            )
            student = db.scalar(select(Student).where(Student.user_id == student_user.id))
            if student is None:
                student = Student(
                    user_id=student_user.id,
                    school_id=school.id,
                    full_name=full_name,
                    roll_number=roll_number,
                )
                db.add(student)
                db.flush()
            else:
                student.full_name = full_name
                student.roll_number = roll_number

            existing = db.scalar(
                select(Enrollment).where(
                    Enrollment.student_id == student.id,
                    Enrollment.section_id == section_a.id,
                    Enrollment.academic_year_id == academic_year.id,
                )
            )
            if existing is None:
                db.add(
                    Enrollment(
                        student_id=student.id,
                        section_id=section_a.id,
                        academic_year_id=academic_year.id,
                        status=EnrollmentStatus.ACTIVE,
                    )
                )

        db.commit()
        print(f"school={school.id}  section_6A={section_a.id}  section_6B={section_b.id}  teacher={teacher.id}")
        print(f"admin   : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        for extra in EXTRA_ADMINS:
            print(f"admin   : {extra['email']} / {extra['password']}")
        print(f"teacher : {TEACHER_EMAIL} / {TEACHER_PASSWORD}")
        print(f"students: student01@anaadi.demo ... student10@anaadi.demo / {STUDENT_PASSWORD}")


def _upsert_section(
    db,
    *,
    school_id: int,
    class_id: int,
    academic_year_id: int,
    name: str,
    class_teacher_id: int | None,
) -> Section:
    section = db.scalar(
        select(Section).where(
            Section.school_id == school_id,
            Section.class_id == class_id,
            Section.academic_year_id == academic_year_id,
            Section.name == name,
        )
    )
    if section is None:
        section = Section(
            school_id=school_id,
            class_id=class_id,
            academic_year_id=academic_year_id,
            name=name,
            class_teacher_id=class_teacher_id,
        )
        db.add(section)
        db.flush()
    else:
        section.class_teacher_id = class_teacher_id
    return section


if __name__ == "__main__":
    main()
