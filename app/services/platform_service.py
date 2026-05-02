"""Platform-admin tenant queries.

These are aggregation reads for the Tenants surface — listing every
non-personal school with its counts, listing every individual learner,
and assembling the per-tenant "overview" payloads. Everything here is
called only from `app.api.routes.platform`, all of which is gated by
`require_platform_admin`.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, Submission, SubmissionStatus
from app.models.curriculum import AcademicYear, Chapter, SchoolClass
from app.models.mastery import SkillMastery
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


# ---------- Schools ----------


def list_schools(db: Session) -> list[dict]:
    """All non-personal schools with student/teacher/section counts."""
    schools = list(
        db.scalars(
            select(School)
            .where(School.is_personal.is_(False))
            .order_by(School.created_at.desc(), School.id.desc())
        )
    )
    if not schools:
        return []
    school_ids = [s.id for s in schools]

    student_counts = dict(
        db.execute(
            select(Student.school_id, func.count(Student.id))
            .where(Student.school_id.in_(school_ids))
            .group_by(Student.school_id)
        ).all()
    )
    teacher_counts = dict(
        db.execute(
            select(Teacher.school_id, func.count(Teacher.id))
            .where(Teacher.school_id.in_(school_ids))
            .group_by(Teacher.school_id)
        ).all()
    )
    section_counts = dict(
        db.execute(
            select(Section.school_id, func.count(Section.id))
            .where(Section.school_id.in_(school_ids))
            .group_by(Section.school_id)
        ).all()
    )

    return [
        {
            "id": s.id,
            "name": s.name,
            "board": s.board,
            "brand_name": s.brand_name,
            "is_active": s.is_active,
            "student_count": student_counts.get(s.id, 0),
            "teacher_count": teacher_counts.get(s.id, 0),
            "section_count": section_counts.get(s.id, 0),
            "created_at": s.created_at,
        }
        for s in schools
    ]


def school_overview(db: Session, school_id: int) -> dict | None:
    """Full read payload for one school: profile + sections + teachers + students.

    Returns None if the school doesn't exist; the route turns that into 404.
    Personal schools are excluded — those belong to the learners listing.
    """
    school = db.get(School, school_id)
    if school is None or school.is_personal:
        return None

    sections = list(
        db.scalars(
            select(Section)
            .where(Section.school_id == school_id)
            .order_by(Section.class_id, Section.name)
        )
    )
    section_ids = [s.id for s in sections]
    class_levels = {
        c.id: c
        for c in db.scalars(
            select(SchoolClass).where(
                SchoolClass.id.in_({s.class_id for s in sections})
            )
        )
    }
    academic_years = {
        y.id: y
        for y in db.scalars(
            select(AcademicYear).where(
                AcademicYear.id.in_({s.academic_year_id for s in sections})
            )
        )
    }

    teachers = list(
        db.scalars(
            select(Teacher)
            .where(Teacher.school_id == school_id)
            .order_by(Teacher.full_name)
        )
    )
    teacher_users = {
        u.id: u
        for u in db.scalars(
            select(User).where(User.id.in_({t.user_id for t in teachers}))
        )
    }
    sections_per_teacher: dict[int, int] = defaultdict(int)
    for sec in sections:
        if sec.class_teacher_id is not None:
            sections_per_teacher[sec.class_teacher_id] += 1

    students = list(
        db.scalars(
            select(Student)
            .where(Student.school_id == school_id)
            .order_by(Student.full_name)
        )
    )
    student_users = {
        u.id: u
        for u in db.scalars(
            select(User).where(
                User.id.in_({s.user_id for s in students if s.user_id is not None})
            )
        )
    }
    enrollments = (
        list(
            db.scalars(
                select(Enrollment).where(
                    Enrollment.section_id.in_(section_ids),
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
        )
        if section_ids
        else []
    )
    section_for_student: dict[int, Section] = {}
    students_per_section: dict[int, int] = defaultdict(int)
    section_by_id = {s.id: s for s in sections}
    for e in enrollments:
        section = section_by_id.get(e.section_id)
        if section is None:
            continue
        students_per_section[e.section_id] += 1
        section_for_student.setdefault(e.student_id, section)

    section_payload: list[dict] = []
    for sec in sections:
        cls = class_levels.get(sec.class_id)
        year = academic_years.get(sec.academic_year_id)
        teacher_name = next(
            (
                t.full_name
                for t in teachers
                if t.id == sec.class_teacher_id
            ),
            None,
        )
        section_payload.append(
            {
                "id": sec.id,
                "name": sec.name,
                "class_level": cls.level if cls else None,
                "class_display_name": cls.display_name if cls else None,
                "academic_year": year.name if year else None,
                "class_teacher_name": teacher_name,
                "student_count": students_per_section.get(sec.id, 0),
            }
        )

    teacher_payload: list[dict] = []
    for t in teachers:
        u = teacher_users.get(t.user_id)
        teacher_payload.append(
            {
                "id": t.id,
                "full_name": t.full_name,
                "email": u.email if u else "",
                "qualification": t.qualification,
                "sections_count": sections_per_teacher.get(t.id, 0),
                "is_active": bool(u.is_active) if u is not None else False,
            }
        )

    student_payload: list[dict] = []
    for st in students:
        sec = section_for_student.get(st.id)
        cls = class_levels.get(sec.class_id) if sec is not None else None
        u = student_users.get(st.user_id) if st.user_id is not None else None
        student_payload.append(
            {
                "id": st.id,
                "full_name": st.full_name,
                "roll_number": st.roll_number,
                "section_name": sec.name if sec else None,
                "class_level": cls.level if cls else None,
                "has_login": u is not None,
                "is_active": bool(u.is_active) if u is not None else False,
            }
        )

    return {
        "id": school.id,
        "name": school.name,
        "board": school.board,
        "address": school.address,
        "contact_email": school.contact_email,
        "contact_phone": school.contact_phone,
        "brand_name": school.brand_name,
        "is_active": school.is_active,
        "is_personal": school.is_personal,
        "created_at": school.created_at,
        "student_count": len(students),
        "teacher_count": len(teachers),
        "section_count": len(sections),
        "sections": section_payload,
        "teachers": teacher_payload,
        "students": student_payload,
    }


def set_school_active(db: Session, school_id: int, *, is_active: bool) -> School | None:
    school = db.get(School, school_id)
    if school is None or school.is_personal:
        return None
    school.is_active = is_active
    db.commit()
    db.refresh(school)
    return school


# ---------- Individual learners ----------


def list_learners(db: Session) -> list[dict]:
    """All `individual_learner` users with their basic activity stats."""
    users = list(
        db.scalars(
            select(User)
            .where(User.role == UserRole.INDIVIDUAL_LEARNER)
            .order_by(User.created_at.desc())
        )
    )
    if not users:
        return []
    user_ids = [u.id for u in users]

    students = list(
        db.scalars(
            select(Student).where(Student.user_id.in_(user_ids))
        )
    )
    student_by_user = {s.user_id: s for s in students if s.user_id is not None}
    student_ids = [s.id for s in students]

    enrollments = (
        list(
            db.scalars(
                select(Enrollment).where(
                    Enrollment.student_id.in_(student_ids),
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
        )
        if student_ids
        else []
    )
    section_ids = {e.section_id for e in enrollments}
    sections = {
        s.id: s
        for s in db.scalars(
            select(Section).where(Section.id.in_(section_ids))
        )
    }
    classes = {
        c.id: c
        for c in db.scalars(
            select(SchoolClass).where(
                SchoolClass.id.in_({s.class_id for s in sections.values()})
            )
        )
    }
    section_for_student: dict[int, Section] = {}
    for e in enrollments:
        sec = sections.get(e.section_id)
        if sec is not None:
            section_for_student.setdefault(e.student_id, sec)

    submissions = (
        list(
            db.scalars(
                select(Submission)
                .where(
                    Submission.student_id.in_(student_ids),
                    Submission.status == SubmissionStatus.EVALUATED,
                )
            )
        )
        if student_ids
        else []
    )
    submissions_by_student: dict[int, list[Submission]] = defaultdict(list)
    for sub in submissions:
        submissions_by_student[sub.student_id].append(sub)

    payload: list[dict] = []
    for u in users:
        student = student_by_user.get(u.id)
        section = section_for_student.get(student.id) if student else None
        cls = classes.get(section.class_id) if section else None

        subs = submissions_by_student.get(student.id, []) if student else []
        valid_pct = [
            (s.total_awarded / s.max_marks) * 100
            for s in subs
            if s.total_awarded is not None and s.max_marks
        ]
        avg_pct = round(sum(valid_pct) / len(valid_pct), 1) if valid_pct else None

        payload.append(
            {
                "user_id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "is_active": u.is_active,
                "class_level": cls.level if cls else None,
                "signup_date": u.created_at,
                "submissions_count": len(subs),
                "average_percentage": avg_pct,
            }
        )
    return payload


def learner_overview(db: Session, user_id: int) -> dict | None:
    """Detailed view for one individual learner."""
    user = db.scalar(
        select(User).where(
            User.id == user_id, User.role == UserRole.INDIVIDUAL_LEARNER
        )
    )
    if user is None:
        return None

    student = db.scalar(select(Student).where(Student.user_id == user.id))
    section: Section | None = None
    cls: SchoolClass | None = None
    submissions: list[Submission] = []
    if student is not None:
        enrollment = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        if enrollment is not None:
            section = db.get(Section, enrollment.section_id)
            if section is not None:
                cls = db.get(SchoolClass, section.class_id)
        submissions = list(
            db.scalars(
                select(Submission)
                .where(
                    Submission.student_id == student.id,
                    Submission.status == SubmissionStatus.EVALUATED,
                )
                .order_by(Submission.evaluated_at.desc())
            )
        )

    valid_pct = [
        (s.total_awarded / s.max_marks) * 100
        for s in submissions
        if s.total_awarded is not None and s.max_marks
    ]
    avg_pct = round(sum(valid_pct) / len(valid_pct), 1) if valid_pct else None

    last_activity: datetime | None = None
    for s in submissions:
        cand = s.evaluated_at or s.submitted_at
        if cand is not None and (last_activity is None or cand > last_activity):
            last_activity = cand

    masteries = (
        list(
            db.scalars(
                select(SkillMastery).where(SkillMastery.student_id == student.id)
            )
        )
        if student is not None
        else []
    )
    avg_mastery = (
        round(sum(m.mastery for m in masteries) / len(masteries), 3)
        if masteries
        else None
    )

    # Top 5 most recent submissions, with the assessment + chapter context the
    # UI needs to render readable rows.
    recent = submissions[:5]
    assessment_ids = {s.assessment_id for s in recent}
    assessments = {
        a.id: a
        for a in db.scalars(
            select(Assessment).where(Assessment.id.in_(assessment_ids))
        )
    }
    chapter_ids = {a.chapter_id for a in assessments.values() if a.chapter_id}
    chapters = {
        c.id: c
        for c in db.scalars(select(Chapter).where(Chapter.id.in_(chapter_ids)))
    }
    recent_payload: list[dict] = []
    for s in recent:
        a = assessments.get(s.assessment_id)
        ch = chapters.get(a.chapter_id) if a and a.chapter_id else None
        pct = (
            round(100 * s.total_awarded / s.max_marks, 1)
            if s.total_awarded is not None and s.max_marks
            else None
        )
        recent_payload.append(
            {
                "submission_id": s.id,
                "assessment_id": s.assessment_id,
                "assessment_title": a.title if a else "(removed)",
                "chapter_id": ch.id if ch else None,
                "chapter_title": ch.title if ch else None,
                "score": s.total_awarded,
                "max_marks": s.max_marks,
                "percentage": pct,
                "submitted_at": s.submitted_at,
                "evaluated_at": s.evaluated_at,
                "status": s.status.value,
            }
        )

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "signup_date": user.created_at,
        "last_login_at": None,  # not tracked yet; placeholder kept for future
        "class_level": cls.level if cls else None,
        "class_display_name": cls.display_name if cls else None,
        "school_id": user.school_id or 0,
        "submissions_count": len(submissions),
        "average_percentage": avg_pct,
        "last_activity_at": last_activity,
        "average_mastery": avg_mastery,
        "recent_submissions": recent_payload,
    }


def set_learner_active(db: Session, user_id: int, *, is_active: bool) -> User | None:
    user = db.scalar(
        select(User).where(
            User.id == user_id, User.role == UserRole.INDIVIDUAL_LEARNER
        )
    )
    if user is None:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
