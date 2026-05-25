"""Service layer for the learner practice-rhythm feature (Stage 1).

Reads:
  - `practice_summary(db, user_id)` — a single payload the dashboard
    consumes: this week's practice days, this week's goal, recent
    stamps. All derived; no caching.

Writes:
  - `award_stamps_for_submission(db, submission)` — call after a
    submission's grading lands. Inserts the QUIZ_COMPLETED stamp,
    plus PERFECT_SCORE / PRACTICE_DAY / WEEKLY_GOAL_MET when
    earned. PRACTICE_DAY and WEEKLY_GOAL_MET are deduplicated so
    repeated submissions on the same day / in the same week don't
    spam the stamp book.
  - `set_weekly_goal(db, user_id, target_days)` — upsert the goal
    for the current ISO week.

Time semantics:
  We use UTC throughout. ISO week starts Monday. Practice days are
  counted by the date portion of `submissions.submitted_at` in UTC.
  Per-tenant timezone support is a deliberate non-goal for v1 — the
  numbers are close enough for nudges.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    LearnerStamp,
    LearnerWeeklyGoal,
    StampKind,
    Submission,
)


DEFAULT_WEEKLY_TARGET = 4
WEEKLY_TARGET_MIN = 1
WEEKLY_TARGET_MAX = 7
RECENT_STAMPS_DEFAULT_LIMIT = 12


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> date:
    return _now_utc().date()


def _week_start_for(d: date) -> date:
    """Monday-of-ISO-week containing `d`. Pure helper, no DB hit."""
    return d - timedelta(days=d.weekday())


def _current_week_start() -> date:
    return _week_start_for(_today_utc())


# ---------------------------------------------------------------------------
# Goal — get / set
# ---------------------------------------------------------------------------

def get_or_create_current_goal(db: Session, *, user_id: int) -> LearnerWeeklyGoal:
    """Return the row for the current ISO week, creating it with the
    default target if it doesn't yet exist. The default is applied
    on demand rather than via a backfill, so existing users get the
    default the first time they hit the dashboard."""
    week_start = _current_week_start()
    row = db.scalar(
        select(LearnerWeeklyGoal).where(
            LearnerWeeklyGoal.user_id == user_id,
            LearnerWeeklyGoal.week_start == week_start,
        )
    )
    if row is not None:
        return row
    row = LearnerWeeklyGoal(
        user_id=user_id,
        week_start=week_start,
        target_days=DEFAULT_WEEKLY_TARGET,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_weekly_goal(
    db: Session, *, user_id: int, target_days: int
) -> LearnerWeeklyGoal:
    """Upsert the goal for the current week. Clamps target_days into
    the allowed [1, 7] range so callers don't need to validate."""
    target_days = max(WEEKLY_TARGET_MIN, min(WEEKLY_TARGET_MAX, target_days))
    row = get_or_create_current_goal(db, user_id=user_id)
    if row.target_days != target_days:
        row.target_days = target_days
        db.commit()
        db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Practice-days query
# ---------------------------------------------------------------------------

def _practice_days_in_range(
    db: Session, *, user_id: int, start: date, end_exclusive: date
) -> list[date]:
    """Distinct UTC dates on which the user has at least one submission
    in [start, end_exclusive). Returned sorted ascending so the
    dashboard can show a calendar strip without re-sorting.

    Returns an empty list for non-learners (no Student row), which is
    the safe default — practice days are a learner-only concept.
    """
    student_id = _student_id_for_user(db, user_id)
    if student_id is None:
        return []
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_exclusive, datetime.min.time(), tzinfo=timezone.utc)
    # Cast submitted_at to date; rely on the DB to do the bucketing
    # (single index scan, no per-row Python work).
    submitted_date = func.date(Submission.submitted_at)
    rows = db.scalars(
        select(distinct(submitted_date))
        .where(
            Submission.student_id == student_id,
            Submission.submitted_at.isnot(None),
            Submission.submitted_at >= start_dt,
            Submission.submitted_at < end_dt,
        )
        .order_by(submitted_date)
    ).all()
    return [r if isinstance(r, date) else date.fromisoformat(str(r)) for r in rows]


def _student_id_for_user(db: Session, user_id: int) -> int | None:
    """Lazy lookup so the practice-days query works for either a
    direct user FK or via the Student bridge — Submission stores
    `student_id`, not `user_id`. Returns None for non-learner users.
    """
    from app.models import Student  # local import to dodge cycles
    return db.scalar(select(Student.id).where(Student.user_id == user_id))


# ---------------------------------------------------------------------------
# Read-side: practice summary for the dashboard
# ---------------------------------------------------------------------------

@dataclass
class PracticeSummary:
    week_start: date
    week_end: date  # inclusive (Sunday)
    target_days: int
    practice_days_this_week: list[date]
    practice_days_count_this_week: int
    practice_days_count_total: int
    weekly_goal_met: bool
    recent_stamps: list[LearnerStamp]


def practice_summary(
    db: Session, *, user_id: int, recent_stamp_limit: int = RECENT_STAMPS_DEFAULT_LIMIT
) -> PracticeSummary:
    """Single payload powering the "Your practice" card. Bundled to
    keep the dashboard to one round-trip."""
    week_start = _current_week_start()
    week_end_exclusive = week_start + timedelta(days=7)
    week_end_inclusive = week_start + timedelta(days=6)

    goal = get_or_create_current_goal(db, user_id=user_id)
    this_week_days = _practice_days_in_range(
        db, user_id=user_id, start=week_start, end_exclusive=week_end_exclusive
    )
    # All-time practice-days count — cheap enough as a separate query;
    # the day-grouping uses the same index.
    submitted_date = func.date(Submission.submitted_at)
    student_id = _student_id_for_user(db, user_id)
    total_days = 0
    if student_id is not None:
        total_days = db.scalar(
            select(func.count(distinct(submitted_date)))
            .where(
                Submission.student_id == student_id,
                Submission.submitted_at.isnot(None),
            )
        ) or 0

    recent_stamps = db.scalars(
        select(LearnerStamp)
        .where(LearnerStamp.user_id == user_id)
        .order_by(desc(LearnerStamp.earned_at))
        .limit(recent_stamp_limit)
    ).all()

    return PracticeSummary(
        week_start=week_start,
        week_end=week_end_inclusive,
        target_days=goal.target_days,
        practice_days_this_week=this_week_days,
        practice_days_count_this_week=len(this_week_days),
        practice_days_count_total=int(total_days),
        weekly_goal_met=len(this_week_days) >= goal.target_days,
        recent_stamps=list(recent_stamps),
    )


def list_stamps(
    db: Session, *, user_id: int, limit: int = 200
) -> list[LearnerStamp]:
    """Full-history stamp listing for the /me/stamps collection page."""
    return list(
        db.scalars(
            select(LearnerStamp)
            .where(LearnerStamp.user_id == user_id)
            .order_by(desc(LearnerStamp.earned_at))
            .limit(limit)
        ).all()
    )


# ---------------------------------------------------------------------------
# Write-side: stamp awarding
# ---------------------------------------------------------------------------

def award_stamps_for_submission(db: Session, submission: Submission) -> list[LearnerStamp]:
    """Award the stamps unlocked by this submission. Idempotent for the
    natural-key stamps (PRACTICE_DAY, WEEKLY_GOAL_MET).

    Called after the submission row has been graded (so total_awarded
    is populated). Caller should commit the outer transaction; we
    flush but don't commit so the awarding stays atomic with the
    submission itself.

    Returns the newly-created stamps so the caller can decide whether
    to surface a toast / "+1 day" celebration.
    """
    from app.models import Student  # local import; avoid cycles

    # Translate student_id back to user_id — stamps live per user, not
    # per student record, so a school student migrating to a different
    # section keeps their stamp book.
    student = db.get(Student, submission.student_id)
    if student is None:
        return []
    user_id = student.user_id

    awarded: list[LearnerStamp] = []

    # 1. QUIZ_COMPLETED — every submission that lands earns one.
    quiz_stamp = LearnerStamp(
        user_id=user_id,
        kind=StampKind.QUIZ_COMPLETED,
        stamp_metadata={
            "assessment_id": submission.assessment_id,
            "submission_id": submission.id,
            "total_awarded": submission.total_awarded,
            "max_marks": submission.max_marks,
        },
    )
    db.add(quiz_stamp)
    awarded.append(quiz_stamp)

    # 2. PERFECT_SCORE — full marks (only on auto-gradable submissions).
    if (
        submission.total_awarded is not None
        and submission.max_marks
        and submission.total_awarded >= submission.max_marks
    ):
        perfect = LearnerStamp(
            user_id=user_id,
            kind=StampKind.PERFECT_SCORE,
            stamp_metadata={
                "assessment_id": submission.assessment_id,
                "submission_id": submission.id,
                "marks": submission.total_awarded,
            },
        )
        db.add(perfect)
        awarded.append(perfect)

    # 3. PRACTICE_DAY — first submission of the day (UTC). Deduplicated
    # by checking whether an existing stamp already covers today.
    today = (submission.submitted_at or _now_utc()).astimezone(timezone.utc).date()
    today_already = db.scalar(
        select(func.count(LearnerStamp.id)).where(
            LearnerStamp.user_id == user_id,
            LearnerStamp.kind == StampKind.PRACTICE_DAY,
            func.date(LearnerStamp.earned_at) == today,
        )
    )
    if not today_already:
        day_stamp = LearnerStamp(
            user_id=user_id,
            kind=StampKind.PRACTICE_DAY,
            stamp_metadata={"date": today.isoformat()},
        )
        db.add(day_stamp)
        awarded.append(day_stamp)

    # 4. WEEKLY_GOAL_MET — when the practice-day count reaches the
    # goal target for the current week. Awarded at most once per week.
    week_start = _week_start_for(today)
    week_already = db.scalar(
        select(func.count(LearnerStamp.id)).where(
            LearnerStamp.user_id == user_id,
            LearnerStamp.kind == StampKind.WEEKLY_GOAL_MET,
            # Match on metadata's week_start string for portable JSON
            # comparison. Counts are low; full-table scan is fine.
            LearnerStamp.stamp_metadata["week_start"].astext == week_start.isoformat(),
        )
    )
    if not week_already:
        # Recompute the days count using the freshly-flushed stamp.
        db.flush()
        goal = get_or_create_current_goal(db, user_id=user_id)
        days_in_week = _practice_days_in_range(
            db,
            user_id=user_id,
            start=week_start,
            end_exclusive=week_start + timedelta(days=7),
        )
        if len(days_in_week) >= goal.target_days:
            week_stamp = LearnerStamp(
                user_id=user_id,
                kind=StampKind.WEEKLY_GOAL_MET,
                stamp_metadata={
                    "week_start": week_start.isoformat(),
                    "target_days": goal.target_days,
                    "days_achieved": len(days_in_week),
                },
            )
            db.add(week_stamp)
            awarded.append(week_stamp)

    db.flush()
    return awarded


# ---------------------------------------------------------------------------
# Stamp shape helper for API serialisation
# ---------------------------------------------------------------------------

def stamp_to_dict(stamp: LearnerStamp) -> dict[str, Any]:
    return {
        "id": stamp.id,
        "kind": stamp.kind.value if hasattr(stamp.kind, "value") else stamp.kind,
        "earned_at": stamp.earned_at,
        "metadata": stamp.stamp_metadata or {},
    }
