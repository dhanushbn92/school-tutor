from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    AssessmentType,
)
from app.models.question import Question, QuestionStatus
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    Teacher,
    User,
    UserRole,
)


class AssessmentError(Exception):
    """Domain-level error for invalid assessment operations (surface as 4xx)."""


def create_assessment(
    db: Session,
    *,
    user: User,
    section_id: int,
    subject_id: int,
    chapter_id: int | None,
    assessment_type: AssessmentType,
    title: str,
    instructions: str | None,
    question_ids: list[int],
    marks_overrides: dict[int, int] | None = None,
    duration_minutes: int | None = None,
    due_at: datetime | None = None,
) -> Assessment:
    section = db.get(Section, section_id)
    if section is None:
        raise AssessmentError(f"Section {section_id} not found")
    if not _user_can_manage_section(db, user, section):
        raise AssessmentError("You cannot create assessments for this section")

    if not question_ids:
        raise AssessmentError("At least one question is required")

    questions = list(
        db.scalars(select(Question).where(Question.id.in_(question_ids)))
    )
    found_ids = {q.id for q in questions}
    missing = [qid for qid in question_ids if qid not in found_ids]
    if missing:
        raise AssessmentError(f"Questions not found: {missing}")

    not_approved = [q.id for q in questions if q.status != QuestionStatus.APPROVED]
    if not_approved:
        raise AssessmentError(
            f"Only APPROVED questions can be added to assessments. Offending ids: {not_approved}"
        )

    marks_overrides = marks_overrides or {}
    total = 0
    question_rows: list[AssessmentQuestion] = []
    questions_by_id = {q.id: q for q in questions}
    for order, qid in enumerate(question_ids, start=1):
        q = questions_by_id[qid]
        marks = marks_overrides.get(qid) or q.marks
        total += marks
        question_rows.append(
            AssessmentQuestion(
                question_id=qid, order=order, marks_override=marks_overrides.get(qid)
            )
        )

    assessment = Assessment(
        section_id=section_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        type=assessment_type,
        status=AssessmentStatus.DRAFT,
        title=title,
        instructions=instructions,
        total_marks=total,
        duration_minutes=duration_minutes,
        due_at=due_at,
        created_by_id=user.id,
    )
    assessment.questions = question_rows
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def publish_assessment(db: Session, *, user: User, assessment_id: int) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise AssessmentError(f"Assessment {assessment_id} not found")
    if not _user_can_manage_section_id(db, user, assessment.section_id):
        raise AssessmentError("You cannot publish this assessment")
    if assessment.status != AssessmentStatus.DRAFT:
        raise AssessmentError(f"Assessment is {assessment.status.value}, not DRAFT")
    assessment.status = AssessmentStatus.PUBLISHED
    assessment.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)
    return assessment


def close_assessment(db: Session, *, user: User, assessment_id: int) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise AssessmentError(f"Assessment {assessment_id} not found")
    if not _user_can_manage_section_id(db, user, assessment.section_id):
        raise AssessmentError("You cannot close this assessment")
    assessment.status = AssessmentStatus.CLOSED
    db.commit()
    db.refresh(assessment)
    return assessment


def list_assessments_for_user(
    db: Session,
    *,
    user: User,
    section_id: int | None = None,
    chapter_id: int | None = None,
) -> list[Assessment]:
    stmt: Select[tuple[Assessment]] = (
        select(Assessment)
        .options(joinedload(Assessment.questions))
        .order_by(Assessment.id.desc())
    )
    if section_id is not None:
        stmt = stmt.where(Assessment.section_id == section_id)
    if chapter_id is not None:
        # Chapter-scoped listing — used by the "Assessments" tab on the
        # chapter Learn page so the student sees only the tests for the
        # chapter they're studying. Cumulative tests that span multiple
        # chapters store the primary chapter_id, so they show on that
        # chapter's tab and not on others.
        stmt = stmt.where(Assessment.chapter_id == chapter_id)

    if user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id is None:
            return []
        stmt = stmt.join(Section, Section.id == Assessment.section_id).where(
            Section.school_id == user.school_id
        )
    elif user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is None:
            return []
        stmt = stmt.join(Section, Section.id == Assessment.section_id).where(
            Section.class_teacher_id == teacher.id
        )
    elif user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if student is None:
            return []
        section_ids = db.scalars(
            select(Enrollment.section_id).where(
                Enrollment.student_id == student.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        ).all()
        if not section_ids:
            return []
        stmt = stmt.where(
            Assessment.section_id.in_(section_ids),
            Assessment.status == AssessmentStatus.PUBLISHED,
        )
    else:
        # Unknown / platform_admin: nothing to see in any school's assessments.
        return []
    return list(db.scalars(stmt).unique())


def _user_can_manage_section(db: Session, user: User, section: Section) -> bool:
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == section.school_id:
        return True
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        return teacher is not None and section.class_teacher_id == teacher.id
    return False


def _user_can_manage_section_id(db: Session, user: User, section_id: int) -> bool:
    section = db.get(Section, section_id)
    return section is not None and _user_can_manage_section(db, user, section)
