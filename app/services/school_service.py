from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.curriculum import AcademicYear, SchoolClass, Subject
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    Teacher,
    TeacherSubjectAssignment,
    User,
    UserRole,
)


MVP_CLASS_LEVELS: set[int] = {6, 7, 8, 9, 10}


def assert_class_level_in_mvp_scope(level: int) -> None:
    if level not in MVP_CLASS_LEVELS:
        raise ValueError(
            f"Class level {level} is outside the MVP scope (supported: {sorted(MVP_CLASS_LEVELS)})"
        )


def list_sections_for_user(db: Session, user: User) -> list[Section]:
    stmt = (
        select(Section)
        .options(joinedload(Section.class_teacher))
        .order_by(Section.class_id, Section.name)
    )
    if user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id is None:
            return []
        stmt = stmt.where(Section.school_id == user.school_id)
    elif user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is None:
            return []
        stmt = stmt.where(Section.class_teacher_id == teacher.id)
    elif user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if student is None:
            return []
        stmt = stmt.join(Enrollment, Enrollment.section_id == Section.id).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    else:
        return []
    return list(db.scalars(stmt))


def list_students_in_section(
    db: Session,
    *,
    section_id: int,
    user: User,
) -> list[Student]:
    section = db.get(Section, section_id)
    if section is None:
        return []
    if not _user_can_view_section(db, user, section):
        return []
    stmt = (
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(
            Enrollment.section_id == section_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .order_by(Student.roll_number.is_(None), Student.roll_number, Student.full_name)
    )
    return list(db.scalars(stmt))


def _user_can_view_section(db: Session, user: User, section: Section) -> bool:
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == section.school_id:
        return True
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is not None and section.class_teacher_id == teacher.id:
            return True
    if user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if student is None:
            return False
        enrolled = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.section_id == section.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        return enrolled is not None
    return False


def enrich_section(db: Session, section: Section) -> dict:
    school_class = db.get(SchoolClass, section.class_id)
    academic_year = db.get(AcademicYear, section.academic_year_id)
    return {
        "id": section.id,
        "school_id": section.school_id,
        "class_id": section.class_id,
        "academic_year_id": section.academic_year_id,
        "name": section.name,
        "class_teacher_id": section.class_teacher_id,
        "class_level": school_class.level if school_class else None,
        "class_display_name": school_class.display_name if school_class else None,
        "academic_year": academic_year.name if academic_year else None,
    }


# ---------- Teacher subject assignments ----------


def get_teacher_for_user(db: Session, user: User) -> Teacher | None:
    """Look up the Teacher row backing this User account, if any."""
    if user.role != UserRole.TEACHER:
        return None
    return db.scalar(select(Teacher).where(Teacher.user_id == user.id))


def list_teacher_subject_ids(db: Session, teacher_id: int) -> list[int]:
    """Explicit subject_ids assigned to this teacher (may be empty)."""
    rows = db.scalars(
        select(TeacherSubjectAssignment.subject_id).where(
            TeacherSubjectAssignment.teacher_id == teacher_id
        )
    )
    return list(rows)


def set_teacher_subject_ids(
    db: Session, *, teacher_id: int, subject_ids: list[int]
) -> list[int]:
    """Replace this teacher's full assignment list. Returns the new list.

    Idempotent: pass the desired set of subject_ids each time. Subjects not
    in the new set are deleted; new ones are inserted. Empty list clears
    all assignments and puts the teacher back into the fallback "all
    subjects of class-teacher classes" mode.
    """
    desired = set(subject_ids)

    # Validate that all requested subjects exist (avoid silently-orphaned rows).
    if desired:
        found = set(
            db.scalars(select(Subject.id).where(Subject.id.in_(desired))).all()
        )
        missing = desired - found
        if missing:
            raise ValueError(f"Unknown subject ids: {sorted(missing)}")

    current = set(list_teacher_subject_ids(db, teacher_id))
    to_remove = current - desired
    to_add = desired - current

    if to_remove:
        db.execute(
            delete(TeacherSubjectAssignment).where(
                TeacherSubjectAssignment.teacher_id == teacher_id,
                TeacherSubjectAssignment.subject_id.in_(to_remove),
            )
        )
    for sid in to_add:
        db.add(TeacherSubjectAssignment(teacher_id=teacher_id, subject_id=sid))
    db.commit()
    return sorted(desired)


def available_subject_ids_for_teacher(
    db: Session, teacher: Teacher
) -> tuple[list[int], bool]:
    """Subjects this teacher is allowed to view content for.

    Strict scoping: only explicit `TeacherSubjectAssignment` rows count.
    A teacher with no assignments sees no subjects and the UI surfaces an
    empty state telling them to ask their school admin to assign subjects.
    The class-teacher relationship (`Section.class_teacher_id`) is for
    homeroom administration of students — it does not grant content
    visibility on its own.

    Returns ``(subject_ids, is_explicit)``:

    - ``is_explicit=True`` — the school admin has set explicit assignments,
      and this is exactly that list.
    - ``is_explicit=False`` — no assignments configured; the list is empty.
    """
    explicit = list_teacher_subject_ids(db, teacher.id)
    return sorted(explicit), bool(explicit)
