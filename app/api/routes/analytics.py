from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_teacher_or_school_admin,
)
from app.db.session import get_db
from app.models.school import Enrollment, EnrollmentStatus, Section, Student, Teacher, User, UserRole
from app.services import analytics_service, mastery_service


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/students/{student_id}/mastery")
def student_mastery_grid(
    student_id: int,
    class_level: int = Query(..., ge=1, le=12),
    # subject_id is optional — omit it to get the whole-syllabus
    # view (every subject in the class, chapters grouped by
    # subject). The learner dashboard's syllabus map + the
    # strongest / best-place tiles call without it; the existing
    # per-subject views (Topic mastery map with the subject picker)
    # pass it through.
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if not _can_view_student(db, user, student):
        raise HTTPException(status_code=403, detail="You cannot view this student's mastery")
    return mastery_service.build_student_grid(
        db, student_id=student_id, class_level=class_level, subject_id=subject_id
    )


@router.get("/sections/{section_id}/performance")
def section_performance(
    section_id: int,
    assessment_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _can_view_section(db, user, section_id):
        raise HTTPException(status_code=403, detail="You cannot view this section")
    payload = analytics_service.section_performance(
        db, section_id=section_id, assessment_id=assessment_id
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Assessment not found for this section")
    return payload


@router.get("/sections/{section_id}/topic-averages")
def section_topic_averages(
    section_id: int,
    class_level: int = Query(..., ge=1, le=12),
    subject_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _can_view_section(db, user, section_id):
        raise HTTPException(status_code=403, detail="You cannot view this section")
    return analytics_service.section_topic_averages(
        db, section_id=section_id, class_level=class_level, subject_id=subject_id
    )


@router.get("/sections/{section_id}/weakest-topics")
def section_weakest_topics(
    section_id: int,
    class_level: int = Query(..., ge=1, le=12),
    subject_id: int = Query(...),
    min_students_attempted: int = Query(default=1, ge=1),
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _can_view_section(db, user, section_id):
        raise HTTPException(status_code=403, detail="You cannot view this section")
    return analytics_service.section_weakest_topics(
        db,
        section_id=section_id,
        class_level=class_level,
        subject_id=subject_id,
        min_students_attempted=min_students_attempted,
        limit=limit,
    )


@router.get("/class-weak-topics")
def class_weak_topics(
    class_level: int = Query(..., ge=1, le=12),
    subject_id: int = Query(...),
    limit: int = Query(default=8, ge=1, le=30),
    min_attempts: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_school_admin),
):
    """Weakest topics for a (class, subject), broken down by cognitive bucket.

    Aggregates across every section the caller can see:
    - School admin: all sections of this class in their school.
    - Teacher: sections they're class teacher of.

    Each topic returns an overall average mastery and a per-bucket
    (FACTUAL / UNDERSTANDING / APPLICATION) breakdown, so the teacher can
    tell whether students are missing recall, comprehension, or transfer.
    """
    return analytics_service.class_weak_topics(
        db,
        user=user,
        class_level=class_level,
        subject_id=subject_id,
        limit=limit,
        min_attempts=min_attempts,
    )


@router.get("/sections/{section_id}/leaderboard")
def section_leaderboard(
    section_id: int,
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _can_view_section(db, user, section_id):
        raise HTTPException(status_code=403, detail="You cannot view this section")
    return analytics_service.section_leaderboard(
        db, section_id=section_id, subject_id=subject_id
    )


@router.get("/students/{student_id}/trend")
def student_trend(
    student_id: int,
    # subject_id is optional — omit it to get the learner's full
    # cross-subject quiz history. The dashboard score-trend widget
    # passes no subject_id so a multi-subject learner sees their
    # entire practice arc; per-subject deep-dives still pass it.
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if not _can_view_student(db, user, student):
        raise HTTPException(status_code=403, detail="You cannot view this student's trend")
    return analytics_service.student_trend(db, student_id=student_id, subject_id=subject_id)


def _can_view_section(db: Session, user: User, section_id: int) -> bool:
    section = db.get(Section, section_id)
    if section is None:
        return False
    if user.role == UserRole.SCHOOL_ADMIN:
        return user.school_id == section.school_id
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        return teacher is not None and section.class_teacher_id == teacher.id
    if user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if student is None:
            return False
        enrolled = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.section_id == section_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        return enrolled is not None
    return False


def _can_view_student(db: Session, user: User, student: Student) -> bool:
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == student.school_id:
        return True
    if user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        return student.user_id == user.id
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is None:
            return False
        # Teacher can view a student if they class-teach a section the student is enrolled in.
        enrolled_sections = db.scalars(
            select(Enrollment.section_id).where(
                Enrollment.student_id == student.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        ).all()
        if not enrolled_sections:
            return False
        teacher_sections = db.scalars(
            select(Section.id).where(
                Section.class_teacher_id == teacher.id,
                Section.id.in_(enrolled_sections),
            )
        ).all()
        return len(teacher_sections) > 0
    return False
