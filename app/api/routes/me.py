from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_learner,
    require_parent,
    require_teacher_or_school_admin,
)
from app.db.session import get_db
from app.models import LearnerAudioPreferences, LearnerMascotState
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
    parent_encouragement_service,
    parent_link_service,
    practice_variety_service,
    question_bank_service,
    school_service,
)
from app.services.parent_encouragement_service import EncouragementError
from app.services.parent_link_service import ParentLinkError
from app.services.practice_variety_service import PracticeVarietyError
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


# ---------- Vidyārthi mascot — Stage 5 of the child-centric roadmap ----------
#
# Per-learner mascot state: enabled + current outfit. The frontend
# uses `enabled` to decide whether to render the companion at all,
# and `current_outfit` to pick the SVG variant. Lazily created on
# first GET so existing learners don't need a backfill.


# Valid outfit identifiers. Forward-compatible — adding "monsoon-kurta"
# is a one-line edit + new SVG variant, no migration. Until the
# unlock pipeline ships in a follow-up, only "default" is allowed.
_VALID_OUTFITS: set[str] = {"default"}


class MascotUpdate(BaseModel):
    enabled: bool | None = None
    current_outfit: str | None = Field(default=None, max_length=40)


def _serialize_mascot(state: LearnerMascotState) -> dict:
    return {
        "enabled": state.enabled,
        "current_outfit": state.current_outfit,
        "available_outfits": sorted(_VALID_OUTFITS),
    }


@router.get("/mascot")
def get_my_mascot(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    state = db.scalar(
        select(LearnerMascotState).where(LearnerMascotState.user_id == user.id)
    )
    if state is None:
        # Lazy-create on first read so existing learners get the
        # default state without a backfill migration. Default to
        # enabled — the mascot is opt-out, not opt-in.
        state = LearnerMascotState(
            user_id=user.id, enabled=True, current_outfit="default"
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return _serialize_mascot(state)


@router.patch("/mascot")
def update_my_mascot(
    payload: MascotUpdate,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    if payload.current_outfit is not None and payload.current_outfit not in _VALID_OUTFITS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown outfit {payload.current_outfit!r}. "
            f"Valid: {sorted(_VALID_OUTFITS)}.",
        )
    state = db.scalar(
        select(LearnerMascotState).where(LearnerMascotState.user_id == user.id)
    )
    if state is None:
        state = LearnerMascotState(
            user_id=user.id, enabled=True, current_outfit="default"
        )
        db.add(state)
        db.flush()
    if payload.enabled is not None:
        state.enabled = payload.enabled
    if payload.current_outfit is not None:
        state.current_outfit = payload.current_outfit
    db.commit()
    db.refresh(state)
    return _serialize_mascot(state)


# ---------- Parent ↔ child links — Stage 6 of child-centric roadmap ----------
#
# Two surfaces:
#   - Learner side: generate invite codes, list linked parents, revoke
#     a link, read received encouragements, dismiss them.
#   - Parent side: list children, read each child's weekly summary,
#     send encouragement, audit what they've sent.
#
# The link itself is created during parent signup (POST /auth/signup-parent),
# which atomically consumes the invite code + creates the User + the
# link in one transaction. There's no separate "approve" step here.


class EncouragementSendPayload(BaseModel):
    message: str = Field(min_length=1, max_length=280)


# ----- Learner-side -----


@router.post("/parent-invite-codes", status_code=201)
def create_parent_invite_code(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Generate a fresh single-use invite code for a parent. The
    learner gives this code to whichever parent / guardian they want
    to link. 7-day TTL."""
    try:
        invite = parent_link_service.generate_invite_code(
            db, student_user_id=user.id
        )
    except ParentLinkError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "code": invite.code,
        "expires_at": invite.expires_at,
    }


@router.get("/parent-invite-codes")
def list_my_parent_invite_codes(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Active (unused, unexpired) invite codes the learner has
    generated. Used for the "show me the code I made earlier" UI."""
    rows = parent_link_service.list_invite_codes(
        db, student_user_id=user.id, only_active=True
    )
    return [
        {
            "code": r.code,
            "expires_at": r.expires_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/parents")
def list_my_parents(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Currently-linked parent / guardian accounts."""
    parents = parent_link_service.list_parents(db, student_user_id=user.id)
    return [
        {
            "user_id": p.id,
            "full_name": p.full_name,
            "email": p.email,
        }
        for p in parents
    ]


@router.delete("/parents/{parent_user_id}", status_code=204)
def revoke_my_parent(
    parent_user_id: int,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Soft-delete the link. The parent loses access immediately."""
    try:
        parent_link_service.revoke_link(
            db,
            student_user_id=user.id,
            parent_user_id=parent_user_id,
        )
    except ParentLinkError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/encouragements")
def list_my_encouragements(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Undismissed parent notes the learner sees on their dashboard."""
    rows = parent_encouragement_service.list_for_learner(
        db, student_user_id=user.id, only_undismissed=True, limit=10
    )
    return [parent_encouragement_service.to_dict(r) for r in rows]


@router.post("/encouragements/{encouragement_id}/dismiss", status_code=204)
def dismiss_my_encouragement(
    encouragement_id: int,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Hide one note off the dashboard. The row stays in the DB so
    the parent's audit view still shows it."""
    try:
        parent_encouragement_service.dismiss(
            db, encouragement_id=encouragement_id, student_user_id=user.id
        )
    except EncouragementError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ----- Parent-side -----


@router.get("/children")
def list_my_children(
    user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """Children the parent currently has an APPROVED link to."""
    kids = parent_link_service.list_children(db, parent_user_id=user.id)
    return [parent_link_service.child_to_dict(c) for c in kids]


@router.get("/children/{child_user_id}/weekly-summary")
def child_weekly_summary(
    child_user_id: int,
    user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """Encouraging-view weekly summary of a single child.

    Includes the same shape as the learner's own practice-summary —
    deliberately. The Stage 6 design is "open the window to parents
    but only the encouraging view, not surveillance": this endpoint
    is gated so the parent sees PRACTICE rhythm + STAMPS + STREAK +
    POINTS but never the mistake detail (which lives on a separate
    endpoint that parents simply don't have access to)."""
    try:
        parent_link_service.assert_link_active(
            db,
            parent_user_id=user.id,
            student_user_id=child_user_id,
        )
    except ParentLinkError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    summary = learner_practice_service.practice_summary(
        db, user_id=child_user_id
    )
    child = db.get(User, child_user_id)
    # Stage 6 enrichment — strengths / growing-in / chapter rollup /
    # stamps tally. Empty dict when the child has no mastery data
    # yet (the frontend renders an encouraging empty state).
    insights = parent_link_service.compute_child_insights(
        db, child_user_id=child_user_id
    )
    return {
        "child": {
            "user_id": child.id if child else child_user_id,
            "full_name": child.full_name if child else "",
        },
        "week_start": summary.week_start.isoformat(),
        "week_end": summary.week_end.isoformat(),
        "target_days": summary.target_days,
        "practice_days_this_week": [
            d.isoformat() for d in summary.practice_days_this_week
        ],
        "practice_days_count_this_week": summary.practice_days_count_this_week,
        "practice_days_count_total": summary.practice_days_count_total,
        "weekly_goal_met": summary.weekly_goal_met,
        "streak": {
            "current": summary.streak.current,
            "longest": summary.streak.longest,
            # The grace counter helps a parent understand why a streak
            # didn't break after a missed day — surfaces the kinder
            # policy rather than hiding it.
            "grace_used_this_week": summary.streak.grace_used_this_week,
            "grace_allowed_per_week": learner_practice_service.STREAK_MISSES_ALLOWED_PER_WEEK,
        },
        "points_total": summary.points_total,
        # Full level info (including progress toward the next tier)
        # so the parent dashboard can render a progress bar.
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
        "recent_stamps": [
            learner_practice_service.stamp_to_dict(s)
            for s in summary.recent_stamps[:6]
        ],
        # 12-week practice heatmap — same data the child sees on
        # their own dashboard. Honest, encouraging, no surveillance.
        "heatmap": [
            {"day": cell.day.isoformat(), "practiced": cell.practiced}
            for cell in summary.heatmap
        ],
        # Stage 6 enrichment payload (empty dict if no mastery yet).
        "subject_name": insights.get("subject_name"),
        "class_level": insights.get("class_level"),
        "chapter_rollup": insights.get(
            "chapter_rollup", {"mastered": 0, "in_practice": 0, "to_explore": 0}
        ),
        "strengths": insights.get("strengths", []),
        "growing_in": insights.get("growing_in", []),
        "stamps_by_kind": insights.get("stamps_by_kind", {}),
    }


@router.post("/children/{child_user_id}/encouragement", status_code=201)
def send_child_encouragement(
    child_user_id: int,
    payload: EncouragementSendPayload,
    user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """Send a short well-done note to a child. The note lands on the
    child's dashboard until they dismiss it."""
    try:
        row = parent_encouragement_service.send(
            db,
            parent_user_id=user.id,
            student_user_id=child_user_id,
            message=payload.message,
        )
    except EncouragementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return parent_encouragement_service.to_dict(row)


@router.get("/children/{child_user_id}/encouragements")
def list_sent_encouragements(
    child_user_id: int,
    user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """What the parent has sent to one child — audit view."""
    try:
        parent_link_service.assert_link_active(
            db,
            parent_user_id=user.id,
            student_user_id=child_user_id,
        )
    except ParentLinkError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    rows = parent_encouragement_service.list_sent_by_parent(
        db,
        parent_user_id=user.id,
        child_user_id=child_user_id,
        limit=50,
    )
    return [parent_encouragement_service.to_dict(r) for r in rows]


# ---- end of Stage 6 endpoints ----


# ---------- Practice variety hub — Stage 7 of child-centric roadmap ----------
#
# Three lightweight modes that complement the existing quick-quiz
# flow. Speedrun reuses /me/quick-quiz directly from the frontend
# (no new endpoint needed); only Surprise me and Flashcards need
# fresh server-side sampling.


@router.get("/practice/surprise")
def get_practice_surprise(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """One random APPROVED question from the learner's syllabus.
    Inline-rendered on the practice hub; no submission, no grading."""
    try:
        q = practice_variety_service.pick_surprise(db, user=user)
    except PracticeVarietyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return practice_variety_service.question_to_card_dict(q)


# ---------- Audio preferences — Stage 8 of child-centric roadmap ----------
#
# Per-learner read-aloud settings. The actual TTS runs in the browser
# (window.speechSynthesis) so the backend is just a key-value store
# that survives reloads + follows the learner across devices.


class AudioPreferencesUpdate(BaseModel):
    autoplay_questions: bool | None = None
    preferred_voice_uri: str | None = Field(default=None, max_length=200)


def _serialize_audio(prefs: LearnerAudioPreferences) -> dict:
    return {
        "autoplay_questions": prefs.autoplay_questions,
        "preferred_voice_uri": prefs.preferred_voice_uri,
    }


@router.get("/audio-preferences")
def get_my_audio_preferences(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Read-aloud preferences for the current learner. Lazy-created
    on first read so existing accounts don't need a backfill."""
    prefs = db.scalar(
        select(LearnerAudioPreferences).where(
            LearnerAudioPreferences.user_id == user.id
        )
    )
    if prefs is None:
        prefs = LearnerAudioPreferences(
            user_id=user.id,
            autoplay_questions=False,
            preferred_voice_uri=None,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return _serialize_audio(prefs)


@router.patch("/audio-preferences")
def update_my_audio_preferences(
    payload: AudioPreferencesUpdate,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """Toggle autoplay or pick a different voice. Either field may
    be omitted (or sent as null) to leave it unchanged. Sending
    `preferred_voice_uri: null` explicitly resets to the browser
    default — distinguishing this from "field absent" is impossible
    with this PATCH shape, but in practice the frontend either picks
    a voice or clears it, never partial."""
    prefs = db.scalar(
        select(LearnerAudioPreferences).where(
            LearnerAudioPreferences.user_id == user.id
        )
    )
    if prefs is None:
        prefs = LearnerAudioPreferences(
            user_id=user.id,
            autoplay_questions=False,
            preferred_voice_uri=None,
        )
        db.add(prefs)
        db.flush()
    if payload.autoplay_questions is not None:
        prefs.autoplay_questions = payload.autoplay_questions
    if payload.preferred_voice_uri is not None:
        # Empty string = "reset to default". Non-empty = pick that voice.
        prefs.preferred_voice_uri = payload.preferred_voice_uri or None
    db.commit()
    db.refresh(prefs)
    return _serialize_audio(prefs)


@router.get("/practice/flashcards")
def get_practice_flashcards(
    chapter_id: int | None = Query(default=None),
    count: int = Query(default=10, ge=1, le=30),
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    """N factual / REMEMBER-bucket questions for flip-card practice.
    Optional `chapter_id` scopes to a single chapter (still validated
    against the learner's syllabus)."""
    try:
        qs = practice_variety_service.sample_flashcards(
            db, user=user, count=count, chapter_id=chapter_id
        )
    except PracticeVarietyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [practice_variety_service.question_to_card_dict(q) for q in qs]
