"""Classroom analytics.

Each function returns chart-ready payloads. Queries are deliberately simple —
a section is ~30 students, a subject is ~50 outcomes; we fetch rows and
aggregate in Python rather than doing big GROUP BYs. Clearer, testable, fine
for MVP scale.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
    Submission,
    SubmissionStatus,
)
from app.models.curriculum import Book, Chapter, LearningOutcome, SchoolClass, Subject, Topic
from app.models.mastery import CognitiveBucket, SkillMastery
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    Teacher,
    User,
    UserRole,
)


def section_performance(db: Session, *, section_id: int, assessment_id: int) -> dict:
    """Gradebook for one assessment: per-student score + summary stats."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or assessment.section_id != section_id:
        return {}

    student_ids = db.scalars(
        select(Enrollment.student_id).where(
            Enrollment.section_id == section_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).all()

    students = {
        s.id: s
        for s in db.scalars(select(Student).where(Student.id.in_(student_ids))).all()
    }
    submissions = {
        sub.student_id: sub
        for sub in db.scalars(
            select(Submission).where(
                Submission.assessment_id == assessment_id,
                Submission.student_id.in_(student_ids),
            )
        ).all()
    }

    rows: list[dict] = []
    scored = []
    for sid in sorted(student_ids):
        student = students.get(sid)
        sub = submissions.get(sid)
        entry = {
            "student_id": sid,
            "full_name": student.full_name if student else None,
            "roll_number": student.roll_number if student else None,
            "status": sub.status.value if sub else "NOT_SUBMITTED",
            "total_awarded": sub.total_awarded if sub else None,
            "max_marks": sub.max_marks if sub else assessment.total_marks,
            "submitted_at": sub.submitted_at.isoformat() if sub and sub.submitted_at else None,
            "evaluated_at": sub.evaluated_at.isoformat() if sub and sub.evaluated_at else None,
        }
        rows.append(entry)
        if sub and sub.total_awarded is not None:
            scored.append(sub.total_awarded)

    return {
        "section_id": section_id,
        "assessment_id": assessment_id,
        "assessment_title": assessment.title,
        "assessment_type": assessment.type.value,
        "assessment_status": assessment.status.value,
        "total_marks": assessment.total_marks,
        "summary": {
            "enrolled": len(student_ids),
            "submitted": sum(1 for r in rows if r["status"] != "NOT_SUBMITTED"),
            "evaluated": len(scored),
            "average": round(sum(scored) / len(scored), 2) if scored else None,
            "median": round(sorted(scored)[len(scored) // 2], 2) if scored else None,
            "high": max(scored) if scored else None,
            "low": min(scored) if scored else None,
        },
        "students": rows,
    }


def section_topic_averages(
    db: Session,
    *,
    section_id: int,
    class_level: int,
    subject_id: int,
) -> dict:
    """Class-level heatmap: average mastery per outcome across enrolled students."""
    student_ids = db.scalars(
        select(Enrollment.student_id).where(
            Enrollment.section_id == section_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).all()

    chapters = list(
        db.scalars(
            select(Chapter)
            .join(Book, Chapter.book_id == Book.id)
            .join(Subject, Book.subject_id == Subject.id)
            .join(SchoolClass, Subject.class_id == SchoolClass.id)
            .where(SchoolClass.level == class_level, Subject.id == subject_id)
            .order_by(Chapter.chapter_number)
            .options(selectinload(Chapter.learning_outcomes))
        )
    )

    all_outcome_ids = [lo.id for ch in chapters for lo in ch.learning_outcomes]

    mastery_rows = (
        db.scalars(
            select(SkillMastery).where(
                SkillMastery.student_id.in_(student_ids),
                SkillMastery.outcome_id.in_(all_outcome_ids),
            )
        ).all()
        if student_ids and all_outcome_ids
        else []
    )

    by_outcome: dict[int, list[float]] = {}
    for row in mastery_rows:
        by_outcome.setdefault(row.outcome_id, []).append(row.mastery)

    chapter_blocks: list[dict] = []
    for chapter in chapters:
        outcomes_payload = []
        for outcome in sorted(chapter.learning_outcomes, key=lambda lo: lo.code):
            values = by_outcome.get(outcome.id, [])
            outcomes_payload.append(
                {
                    "outcome_id": outcome.id,
                    "code": outcome.code,
                    "description": outcome.description,
                    "bloom_level": outcome.bloom_level.value,
                    "average_mastery": round(sum(values) / len(values), 3) if values else None,
                    "students_attempted": len(values),
                }
            )
        chapter_blocks.append(
            {
                "chapter_id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title,
                "outcomes": outcomes_payload,
            }
        )

    return {
        "section_id": section_id,
        "class_level": class_level,
        "subject_id": subject_id,
        "students_total": len(student_ids),
        "chapters": chapter_blocks,
    }


def section_weakest_topics(
    db: Session,
    *,
    section_id: int,
    class_level: int,
    subject_id: int,
    min_students_attempted: int = 1,
    limit: int = 5,
) -> dict:
    """Rank outcomes by lowest class average. Skips outcomes no one attempted."""
    grid = section_topic_averages(
        db, section_id=section_id, class_level=class_level, subject_id=subject_id
    )
    ranked: list[dict] = []
    for chapter in grid["chapters"]:
        for outcome in chapter["outcomes"]:
            if outcome["average_mastery"] is None:
                continue
            if outcome["students_attempted"] < min_students_attempted:
                continue
            ranked.append(
                {
                    "chapter_id": chapter["chapter_id"],
                    "chapter_number": chapter["chapter_number"],
                    "chapter_title": chapter["chapter_title"],
                    **outcome,
                }
            )
    ranked.sort(key=lambda o: (o["average_mastery"], -o["students_attempted"]))
    return {
        "section_id": section_id,
        "class_level": class_level,
        "subject_id": subject_id,
        "weakest": ranked[:limit],
    }


def student_trend(db: Session, *, student_id: int, subject_id: int) -> dict:
    """Time series of a student's evaluated scores for one subject."""
    pairs = db.execute(
        select(Submission, Assessment)
        .join(Assessment, Submission.assessment_id == Assessment.id)
        .where(
            Submission.student_id == student_id,
            Submission.status == SubmissionStatus.EVALUATED,
            Assessment.subject_id == subject_id,
        )
        .order_by(Submission.evaluated_at)
    ).all()

    series: list[dict] = []
    for sub, assessment in pairs:
        if sub.total_awarded is None or sub.max_marks == 0:
            continue
        series.append(
            {
                "assessment_id": assessment.id,
                "assessment_title": assessment.title,
                "assessment_type": assessment.type.value,
                "chapter_id": assessment.chapter_id,
                "date": (sub.evaluated_at or sub.submitted_at).isoformat() if (sub.evaluated_at or sub.submitted_at) else None,
                "score": sub.total_awarded,
                "max_marks": sub.max_marks,
                "percentage": round(100 * sub.total_awarded / sub.max_marks, 1),
            }
        )
    return {
        "student_id": student_id,
        "subject_id": subject_id,
        "series": series,
        "summary": {
            "tests_evaluated": len(series),
            "average_percentage": round(
                sum(s["percentage"] for s in series) / len(series), 1
            )
            if series
            else None,
        },
    }


def section_leaderboard(
    db: Session,
    *,
    section_id: int,
    subject_id: int | None = None,
) -> dict:
    """Per-student averages across all EVALUATED submissions in this section.

    Returns each student's average percentage and average mastery, sorted
    descending. Useful for class leaderboard + 'students who need help' views.
    """
    student_ids = list(
        db.scalars(
            select(Enrollment.student_id).where(
                Enrollment.section_id == section_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
    )
    students = {
        s.id: s
        for s in db.scalars(
            select(Student).where(Student.id.in_(student_ids))
        )
    }

    sub_stmt = (
        select(Submission, Assessment)
        .join(Assessment, Submission.assessment_id == Assessment.id)
        .where(
            Submission.student_id.in_(student_ids),
            Submission.status == SubmissionStatus.EVALUATED,
        )
    )
    if subject_id is not None:
        sub_stmt = sub_stmt.where(Assessment.subject_id == subject_id)

    per_student_scores: dict[int, list[float]] = {}
    for sub, assessment in db.execute(sub_stmt).all():
        if not sub.total_awarded or not sub.max_marks:
            continue
        pct = round(100 * sub.total_awarded / sub.max_marks, 1)
        per_student_scores.setdefault(sub.student_id, []).append(pct)

    mastery_stmt = select(SkillMastery).where(
        SkillMastery.student_id.in_(student_ids)
    )
    if subject_id is not None:
        mastery_stmt = (
            mastery_stmt
            .join(Chapter, SkillMastery.chapter_id == Chapter.id)
            .join(Book, Chapter.book_id == Book.id)
            .where(Book.subject_id == subject_id)
        )
    per_student_mastery: dict[int, list[float]] = {}
    for row in db.scalars(mastery_stmt):
        per_student_mastery.setdefault(row.student_id, []).append(row.mastery)

    rows: list[dict] = []
    for sid in student_ids:
        student = students.get(sid)
        if student is None:
            continue
        scores = per_student_scores.get(sid, [])
        masteries = per_student_mastery.get(sid, [])
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        avg_mastery = round(sum(masteries) / len(masteries), 3) if masteries else None
        rows.append({
            "student_id": sid,
            "full_name": student.full_name,
            "roll_number": student.roll_number,
            "tests_taken": len(scores),
            "average_percentage": avg_score,
            "average_mastery": avg_mastery,
        })
    rows.sort(
        key=lambda r: (
            -(r["average_percentage"] or -1),
            -(r["average_mastery"] or -1),
            r["full_name"] or "",
        )
    )
    return {
        "section_id": section_id,
        "subject_id": subject_id,
        "students": rows,
    }


# ---------- Class-wise weak topics with cognitive-bucket breakdown ----------


_BUCKET_KEYS: tuple[str, ...] = (
    CognitiveBucket.FACTUAL.value,
    CognitiveBucket.UNDERSTANDING.value,
    CognitiveBucket.APPLICATION.value,
)


def _accessible_student_ids_for_class(
    db: Session,
    *,
    user: User,
    class_level: int,
) -> list[int]:
    """Students in `class_level` the caller is allowed to aggregate over.

    - SCHOOL_ADMIN: all students enrolled in any section of this class at
      the admin's school.
    - TEACHER: students in sections where the teacher is class teacher AND
      whose class matches `class_level`.

    Other roles get [] — they're not supposed to see class-level analytics.
    """
    if user.role not in (UserRole.SCHOOL_ADMIN, UserRole.TEACHER):
        return []

    stmt = (
        select(Enrollment.student_id)
        .join(Section, Section.id == Enrollment.section_id)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .where(
            SchoolClass.level == class_level,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .distinct()
    )

    if user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id is None:
            return []
        stmt = stmt.where(Section.school_id == user.school_id)
    else:  # TEACHER
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        if teacher is None:
            return []
        stmt = stmt.where(Section.class_teacher_id == teacher.id)

    return list(db.scalars(stmt))


def class_weak_topics(
    db: Session,
    *,
    user: User,
    class_level: int,
    subject_id: int,
    limit: int = 8,
    min_attempts: int = 1,
) -> dict:
    """Topics with the lowest class-wide mastery, broken down by cognitive bucket.

    Aggregates `SkillMastery` rows across every student the caller can see
    (see `_accessible_student_ids_for_class`) for the given (class, subject).
    Each topic returns:

    - ``average_mastery`` — mean across all attempted (student, bucket) pairs
      for that topic. The "overall weakness" sort key.
    - ``buckets`` — for FACTUAL / UNDERSTANDING / APPLICATION, the average
      mastery and how many students attempted that bucket. Lets a teacher
      see whether the gap is recall, comprehension, or transfer.

    Topics with fewer than `min_attempts` student attempts are dropped — a
    single failing student would skew the ranking otherwise.
    """
    student_ids = _accessible_student_ids_for_class(
        db, user=user, class_level=class_level
    )
    if not student_ids:
        return {
            "class_level": class_level,
            "subject_id": subject_id,
            "students_total": 0,
            "topics": [],
        }

    # Topics under (class, subject). We pull the chapter context too so the
    # UI can render "Ch 4. Electricity → Magnetic effects" without a second
    # round-trip.
    topic_rows = list(
        db.execute(
            select(Topic, Chapter)
            .join(Chapter, Chapter.id == Topic.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .join(Subject, Subject.id == Book.subject_id)
            .join(SchoolClass, SchoolClass.id == Subject.class_id)
            .where(SchoolClass.level == class_level, Subject.id == subject_id)
            .order_by(Chapter.chapter_number, Topic.id)
        ).all()
    )
    if not topic_rows:
        return {
            "class_level": class_level,
            "subject_id": subject_id,
            "students_total": len(student_ids),
            "topics": [],
        }

    topic_ids = [t.id for t, _ in topic_rows]
    chapter_by_topic = {t.id: ch for t, ch in topic_rows}

    mastery_rows = list(
        db.scalars(
            select(SkillMastery).where(
                SkillMastery.student_id.in_(student_ids),
                SkillMastery.topic_id.in_(topic_ids),
            )
        )
    )

    # bucketed[topic_id][bucket_key] = list of (mastery, student_id)
    bucketed: dict[int, dict[str, list[tuple[float, int]]]] = {
        tid: {b: [] for b in _BUCKET_KEYS} for tid in topic_ids
    }
    for m in mastery_rows:
        if m.topic_id is None:
            continue
        bucket_key = m.cognitive_bucket.value
        bucketed[m.topic_id][bucket_key].append((m.mastery, m.student_id))

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 3) if vals else None

    payload: list[dict] = []
    for topic, _chapter in topic_rows:
        per_bucket = bucketed[topic.id]
        bucket_block = {}
        all_masteries: list[float] = []
        all_student_ids: set[int] = set()
        for bucket in _BUCKET_KEYS:
            entries = per_bucket[bucket]
            masteries = [m for m, _ in entries]
            students = {sid for _, sid in entries}
            bucket_block[bucket] = {
                "average_mastery": _avg(masteries),
                "students_attempted": len(students),
            }
            all_masteries.extend(masteries)
            all_student_ids.update(students)

        if len(all_student_ids) < min_attempts:
            continue
        if not all_masteries:
            continue

        chapter = chapter_by_topic[topic.id]
        payload.append(
            {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "chapter_id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title,
                "average_mastery": _avg(all_masteries),
                "students_attempted": len(all_student_ids),
                "buckets": bucket_block,
            }
        )

    payload.sort(
        key=lambda r: (
            r["average_mastery"] if r["average_mastery"] is not None else 1.0,
            -r["students_attempted"],
        )
    )

    return {
        "class_level": class_level,
        "subject_id": subject_id,
        "students_total": len(student_ids),
        "topics": payload[:limit],
    }
