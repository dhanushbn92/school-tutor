from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_learner,
    require_teacher_or_school_admin,
)
from app.db.session import get_db
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    AssessmentType,
    Submission,
)
from app.models.curriculum import AcademicYear, Book, Chapter, Subject
from app.models.mastery import CognitiveBucket
from app.models.question import QuestionDifficulty, QuestionType
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    User,
)
from app.schemas.assessment import AssessmentRead
from app.schemas.intervention import InterventionNoteRead
from app.schemas.school import SectionRead, StudentRead, TeacherSubjectsRead
from app.services import (
    analytics_service,
    assessment_service,
    intervention_service,
    learner_mistake_service,
    learner_practice_service,
    question_bank_service,
    school_service,
)
from app.services.question_bank_service import BankCoverageError


router = APIRouter(prefix="/me", tags=["me"])


@router.get("/sections", response_model=list[SectionRead])
def my_sections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sections = school_service.list_sections_for_user(db, user)
    return [school_service.enrich_section(db, s) for s in sections]


@router.get("/teacher-subjects", response_model=TeacherSubjectsRead)
def my_teacher_subjects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The current teacher's effective subject scope.

    Empty list with `is_explicit=False` is returned for non-teachers and
    teachers whose admin hasn't set explicit assignments AND who aren't a
    class teacher of any section. The frontend uses this to scope the Learn
    grid and the Content Library subject dropdown.
    """
    teacher = school_service.get_teacher_for_user(db, user)
    if teacher is None:
        return TeacherSubjectsRead(teacher_id=0, subject_ids=[], is_explicit=False)
    subject_ids, is_explicit = school_service.available_subject_ids_for_teacher(
        db, teacher
    )
    return TeacherSubjectsRead(
        teacher_id=teacher.id,
        subject_ids=subject_ids,
        is_explicit=is_explicit,
    )


@router.get("/students", response_model=list[StudentRead])
def my_students(
    section_id: int = Query(..., description="Section to list students of"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sections = school_service.list_sections_for_user(db, user)
    if section_id not in {s.id for s in sections}:
        raise HTTPException(status_code=403, detail="You cannot view this section's students")
    return school_service.list_students_in_section(db, section_id=section_id, user=user)


@router.get("/assessments", response_model=list[AssessmentRead])
def my_assessments(
    section_id: int | None = Query(default=None),
    chapter_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return assessment_service.list_assessments_for_user(
        db, user=user, section_id=section_id, chapter_id=chapter_id
    )


@router.get("/submissions")
def my_submissions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every submission the current user owns, summarised for list views.

    Used by the student Assessments / Detail pages to know whether a quiz is
    already done (and to link to the results view) without leaking other
    students' submissions.
    """
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        return []
    rows = list(
        db.scalars(
            select(Submission)
            .where(Submission.student_id == student.id)
            .order_by(Submission.id.desc())
        )
    )
    return [
        {
            "id": s.id,
            "assessment_id": s.assessment_id,
            "status": s.status.value,
            "submitted_at": s.submitted_at,
            "evaluated_at": s.evaluated_at,
            "total_awarded": s.total_awarded,
            "max_marks": s.max_marks,
        }
        for s in rows
    ]


@router.get("/intervention-notes", response_model=list[InterventionNoteRead])
def my_intervention_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return intervention_service.list_for_teacher(db, user=user)


# ---------- Quick-quiz (individual learner) ----------

class QuickQuizRequest(BaseModel):
    chapter_id: int | None = None
    chapter_ids: list[int] | None = Field(
        default=None,
        description="Cumulative quiz across multiple chapters of the same subject.",
    )
    topic_id: int | None = None
    question_count: int = Field(ge=1, le=30)
    kind: str = Field(
        default="mixed",
        description="One of 'mixed', 'subjective', 'objective'. Filters question types.",
    )
    difficulty_mix: dict[str, int] | None = None
    type_mix: dict[str, int] | None = None
    cognitive_mix: dict[str, int] | None = Field(
        default=None,
        description=(
            'Per-cognitive-bucket counts, e.g. {"FACTUAL": 3, "UNDERSTANDING": 4, "APPLICATION": 3}. '
            "Sums must equal question_count."
        ),
    )
    title: str | None = Field(default=None, max_length=200)
    # Optional time-bound quiz. None means untimed; an int means the
    # take-quiz UI will show a countdown banner and auto-submit when
    # the timer hits zero. Mirrors the same field on Assessment so the
    # student's quick quiz behaves like a teacher-assigned one.
    duration_minutes: int | None = Field(default=None, ge=1, le=180)


@router.post("/quick-quiz", response_model=AssessmentRead, status_code=201)
def quick_quiz(
    payload: QuickQuizRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    """Sample-and-publish in one shot — works for both individual learners
    and school students.

    Resolves the learner's section + subject (personal section for individuals,
    enrolled section for school students), samples APPROVED questions from the
    bank, creates an Assessment in PUBLISHED state, and returns it ready for
    the take-quiz UI to load.
    """
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise HTTPException(status_code=400, detail="No student profile for this user")

    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrollment is None:
        raise HTTPException(
            status_code=400,
            detail="No active enrollment found. Please contact support.",
        )
    section = db.get(Section, enrollment.section_id)
    if section is None:
        raise HTTPException(status_code=400, detail="Personal section is missing")

    if payload.chapter_id is None and not payload.chapter_ids:
        raise HTTPException(
            status_code=400,
            detail="Provide chapter_id (single) or chapter_ids (cumulative).",
        )
    if payload.chapter_id is not None and payload.chapter_ids:
        raise HTTPException(
            status_code=400,
            detail="Pass chapter_id OR chapter_ids, not both.",
        )

    primary_chapter_id = payload.chapter_id or (payload.chapter_ids or [0])[0]
    chapter = db.get(Chapter, primary_chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    book = db.get(Book, chapter.book_id)
    subject = db.get(Subject, book.subject_id) if book else None
    if subject is None:
        raise HTTPException(status_code=500, detail="Chapter not mapped to a subject")
    if subject.class_id != section.class_id:
        raise HTTPException(
            status_code=400,
            detail="Chapter belongs to a different class than your enrolment.",
        )
    # If cumulative, validate every supplied chapter shares the same subject.
    if payload.chapter_ids:
        for cid in payload.chapter_ids:
            ch = db.get(Chapter, cid)
            if ch is None:
                raise HTTPException(status_code=404, detail=f"Chapter {cid} not found")
            ch_book = db.get(Book, ch.book_id)
            if ch_book is None or ch_book.subject_id != subject.id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Chapter {cid} is not part of subject {subject.name}.",
                )

    diff_mix: dict[QuestionDifficulty, int] | None = None
    if payload.difficulty_mix is not None:
        try:
            diff_mix = {
                QuestionDifficulty(k.upper()): v for k, v in payload.difficulty_mix.items()
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Bad difficulty: {exc}") from exc
    type_mix: dict[QuestionType, int] | None = None
    if payload.type_mix is not None:
        try:
            type_mix = {QuestionType(k.upper()): v for k, v in payload.type_mix.items()}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Bad type: {exc}") from exc
    cognitive_mix: dict[CognitiveBucket, int] | None = None
    if payload.cognitive_mix is not None:
        try:
            cognitive_mix = {
                CognitiveBucket(k.upper()): v for k, v in payload.cognitive_mix.items()
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Bad cognitive bucket: {exc}") from exc

    # `kind` lets the simplified student UI pick a subjective-only or
    # objective-only test without exposing the full type_mix machinery.
    allowed_types: list[QuestionType] | None = None
    kind = (payload.kind or "mixed").lower()
    if kind == "subjective":
        allowed_types = [QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER]
    elif kind == "objective":
        allowed_types = [
            QuestionType.MCQ,
            QuestionType.TRUE_FALSE,
            QuestionType.FILL_BLANK,
        ]
    elif kind != "mixed":
        raise HTTPException(
            status_code=400,
            detail=f"Bad kind: {kind!r}. Expected 'mixed', 'subjective', or 'objective'.",
        )

    try:
        sampled = question_bank_service.sample_questions(
            db,
            chapter_id=payload.chapter_id,
            chapter_ids=payload.chapter_ids,
            topic_id=payload.topic_id,
            count=payload.question_count,
            difficulty_mix=diff_mix,
            type_mix=type_mix,
            cognitive_mix=cognitive_mix,
            allowed_types=allowed_types,
        )
    except BankCoverageError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "gaps": exc.gaps},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.chapter_ids:
        title = payload.title or f"Cumulative quiz · {len(payload.chapter_ids)} chapters"
    else:
        title = payload.title or f"Quiz · Ch {chapter.chapter_number} {chapter.title}"
    total = sum(q.marks for q in sampled)
    assessment = Assessment(
        section_id=section.id,
        subject_id=subject.id,
        chapter_id=chapter.id,
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        title=title,
        instructions="Self-paced practice quiz.",
        total_marks=total,
        # Optional time-bound quiz. The take-quiz UI shows a
        # countdown banner + auto-submits at zero when this is set.
        duration_minutes=payload.duration_minutes,
        published_at=datetime.now(timezone.utc),
        created_by_id=user.id,
    )
    for order, q in enumerate(sampled, start=1):
        assessment.questions.append(
            AssessmentQuestion(question_id=q.id, order=order, marks_override=None)
        )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


# Silence "imported but unused" — these are referenced via service modules.
_ = (Book, AcademicYear)


# ---------- Practice rhythm — Stage 1 of the child-centric roadmap ----------
#
# Three endpoints feed the "Your practice" card on the learner dashboard and
# the upcoming stamp-book page:
#   GET  /me/practice-summary     — week progress + recent stamps in one go
#   PUT  /me/practice-summary/goal — learner-set weekly target (1..7 days)
#   GET  /me/stamps               — full stamp history for the collection view
# Learner role gating is enforced via require_learner.


class WeeklyGoalUpdate(BaseModel):
    target_days: int = Field(ge=1, le=7)


@router.get("/practice-summary")
def get_practice_summary(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    summary = learner_practice_service.practice_summary(db, user_id=user.id)
    return {
        "week_start": summary.week_start.isoformat(),
        "week_end": summary.week_end.isoformat(),
        "target_days": summary.target_days,
        "practice_days_this_week": [d.isoformat() for d in summary.practice_days_this_week],
        "practice_days_count_this_week": summary.practice_days_count_this_week,
        "practice_days_count_total": summary.practice_days_count_total,
        "weekly_goal_met": summary.weekly_goal_met,
        "recent_stamps": [
            learner_practice_service.stamp_to_dict(s) for s in summary.recent_stamps
        ],
        # Stage 1.5 additions
        "streak": {
            "current": summary.streak.current,
            "longest": summary.streak.longest,
            "grace_used_this_week": summary.streak.grace_used_this_week,
            "grace_allowed_per_week": learner_practice_service.STREAK_MISSES_ALLOWED_PER_WEEK,
        },
        "points_total": summary.points_total,
        "level": {
            "name": summary.level.name,
            "blurb": summary.level.blurb,
            "min_points": summary.level.min_points,
            "next_name": summary.level.next_name,
            "next_min_points": summary.level.next_min_points,
            "points_into_level": summary.level.points_into_level,
            "points_to_next": summary.level.points_to_next,
        },
        "weekly_goal_progress": {
            "weeks_met_total": summary.weekly_goal_progress.weeks_met_total,
            "weeks_met_run": summary.weekly_goal_progress.weeks_met_run,
        },
        "heatmap": [
            {"day": cell.day.isoformat(), "practiced": cell.practiced}
            for cell in summary.heatmap
        ],
    }


@router.put("/practice-summary/goal")
def update_practice_goal(
    payload: WeeklyGoalUpdate,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    goal = learner_practice_service.set_weekly_goal(
        db, user_id=user.id, target_days=payload.target_days
    )
    return {
        "week_start": goal.week_start.isoformat(),
        "target_days": goal.target_days,
    }


@router.get("/stamps")
def list_my_stamps(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
):
    stamps = learner_practice_service.list_stamps(db, user_id=user.id, limit=limit)
    return [learner_practice_service.stamp_to_dict(s) for s in stamps]


# ---------- Mistake review — Stage 2 of the child-centric roadmap ----------
#
# Two endpoints feed the "Things I got wrong" page:
#   GET  /me/mistakes                       — paginated active mistakes
#   POST /me/mistakes/{question_id}/attempt — single-question retry
# Resolved rows (consecutive_corrects >= 2) are filtered out server-side.


class MistakeAttempt(BaseModel):
    answer_text: str | None = Field(default=None, max_length=4000)


@router.get("/mistakes")
def list_my_mistakes(
    chapter_id: int | None = Query(default=None),
    subject_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    entries = learner_mistake_service.list_active(
        db,
        user_id=user.id,
        chapter_id=chapter_id,
        subject_id=subject_id,
        limit=limit,
    )
    return {
        "total_active": learner_mistake_service.count_active(db, user_id=user.id),
        "items": [learner_mistake_service.entry_to_dict(e) for e in entries],
    }


@router.post("/mistakes/{question_id}/attempt")
def retry_my_mistake(
    question_id: int,
    payload: MistakeAttempt,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    try:
        result = learner_mistake_service.record_retry_attempt(
            db,
            user_id=user.id,
            question_id=question_id,
            answer_text=payload.answer_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "correct": result.correct,
        "correct_answer": result.correct_answer,
        "explanation": result.explanation,
        "consecutive_corrects": result.consecutive_corrects,
        "resolved": result.resolved,
    }
