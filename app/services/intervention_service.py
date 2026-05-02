from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intervention import InterventionNote
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    Teacher,
    User,
    UserRole,
)


class InterventionError(Exception):
    """Domain-level error for invalid intervention-note operations."""


def create_note(
    db: Session,
    *,
    user: User,
    student_id: int,
    note: str,
    chapter_id: int | None,
    topic_id: int | None,
) -> InterventionNote:
    if user.role != UserRole.TEACHER:
        raise InterventionError("Only teachers can file intervention notes")
    teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
    if teacher is None:
        raise InterventionError("No teacher profile for this user")

    student = db.get(Student, student_id)
    if student is None:
        raise InterventionError(f"Student {student_id} not found")
    if student.school_id != teacher.school_id:
        raise InterventionError("Student is in a different school")

    # Teacher must class-teach a section the student is enrolled in.
    teacher_sections = db.scalars(
        select(Section.id).where(Section.class_teacher_id == teacher.id)
    ).all()
    if not teacher_sections:
        raise InterventionError("Only class teachers can file intervention notes")

    enrolled_sections = db.scalars(
        select(Enrollment.section_id).where(
            Enrollment.student_id == student_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).all()
    if not set(enrolled_sections) & set(teacher_sections):
        raise InterventionError("Student is not in any of your sections")

    row = InterventionNote(
        student_id=student_id,
        teacher_id=teacher.id,
        chapter_id=chapter_id,
        topic_id=topic_id,
        note=note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_student(db: Session, *, user: User, student_id: int) -> list[InterventionNote]:
    student = db.get(Student, student_id)
    if student is None:
        return []

    if user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id != student.school_id:
            return []
    elif user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        if student.user_id != user.id:
            return []
    elif user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is None or teacher.school_id != student.school_id:
            return []
    else:
        # Platform admin and unknown roles have no business in tenant notes.
        return []

    return list(
        db.scalars(
            select(InterventionNote)
            .where(InterventionNote.student_id == student_id)
            .order_by(InterventionNote.created_at.desc())
        )
    )


def list_for_teacher(db: Session, *, user: User) -> list[InterventionNote]:
    if user.role != UserRole.TEACHER:
        return []
    teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
    if teacher is None:
        return []
    return list(
        db.scalars(
            select(InterventionNote)
            .where(InterventionNote.teacher_id == teacher.id)
            .order_by(InterventionNote.created_at.desc())
        )
    )
