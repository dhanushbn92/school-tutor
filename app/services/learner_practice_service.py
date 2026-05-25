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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    LearnerLoginDay,
    LearnerPointsLedger,
    LearnerStamp,
    LearnerWeeklyGoal,
    PointsSource,
    StampKind,
    Submission,
)


DEFAULT_WEEKLY_TARGET = 4
WEEKLY_TARGET_MIN = 1
WEEKLY_TARGET_MAX = 7
RECENT_STAMPS_DEFAULT_LIMIT = 12

# Stage 1.5 — login streak grace policy. One missed day per ISO week
# is forgiven; a second miss in the same week breaks the streak.
# Chosen because younger kids will inevitably skip a day (sick, busy,
# parents-said-no) and a strict 0-tolerance counter is more
# discouraging than motivating.
STREAK_MISSES_ALLOWED_PER_WEEK = 1
# How far back to scan login-day rows when computing the current
# streak. Safety net: even the longest plausible streak shouldn't
# exceed this — if it does, we'll just under-count by a few days,
# never crash.
STREAK_LOOKBACK_DAYS = 400

# Stage 1.5 — points rewards. Tunable here without a migration; the
# ledger only stores the *event* kind, not the value at award time.
POINTS_PER_CORRECT_ANSWER = 1
POINTS_PERFECT_SCORE_BONUS = 5
POINTS_PRACTICE_DAY_BONUS = 2
POINTS_WEEKLY_GOAL_BONUS = 10

# Stage 1.5 — level tiers. Names are Sanskrit / age-of-Indian-archery
# themed to fit the platform's "Dhananjaya / Vidyārthi" brand. The
# top tier is open-ended so high-engagement learners don't plateau.
LEVEL_TIERS: list[dict[str, Any]] = [
    {"name": "Shishya", "min_points": 0, "blurb": "Student — just getting started."},
    {"name": "Vidyārthi", "min_points": 50, "blurb": "Knowledge-seeker."},
    {"name": "Ārya", "min_points": 200, "blurb": "Noble one of the craft."},
    {"name": "Ācārya", "min_points": 500, "blurb": "Master of the discipline."},
    {"name": "Mahā-Ācārya", "min_points": 1000, "blurb": "Great master."},
]

# How many weeks of history the dashboard heatmap shows. 12 ≈ a
# school term and matches the GitHub-style intuition learners are
# already used to.
HEATMAP_WEEKS = 12


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
class LevelInfo:
    """Current level + progress toward the next tier."""

    name: str
    blurb: str
    min_points: int
    next_name: str | None
    next_min_points: int | None
    points_into_level: int  # points earned within this tier
    points_to_next: int | None  # None for top tier (no "next")


@dataclass
class StreakInfo:
    current: int
    longest: int
    grace_used_this_week: int


@dataclass
class HeatmapCell:
    day: date
    practiced: bool


@dataclass
class WeeklyGoalProgress:
    weeks_met_total: int  # all-time WEEKLY_GOAL_MET stamp count
    weeks_met_run: int  # current consecutive run ending at the current/last completed week


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
    # Stage 1.5 additions:
    streak: StreakInfo
    points_total: int
    level: LevelInfo
    weekly_goal_progress: WeeklyGoalProgress
    heatmap: list[HeatmapCell]


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

    streak = compute_login_streak(db, user_id=user_id)
    points_total = compute_points_total(db, user_id=user_id)
    level = compute_level(points_total)
    weekly_goal_progress = compute_weekly_goal_progress(db, user_id=user_id)
    heatmap = compute_heatmap(db, user_id=user_id, weeks=HEATMAP_WEEKS)

    return PracticeSummary(
        week_start=week_start,
        week_end=week_end_inclusive,
        target_days=goal.target_days,
        practice_days_this_week=this_week_days,
        practice_days_count_this_week=len(this_week_days),
        practice_days_count_total=int(total_days),
        weekly_goal_met=len(this_week_days) >= goal.target_days,
        recent_stamps=list(recent_stamps),
        streak=streak,
        points_total=points_total,
        level=level,
        weekly_goal_progress=weekly_goal_progress,
        heatmap=heatmap,
    )


# ---------------------------------------------------------------------------
# Login streak — Stage 1.5
# ---------------------------------------------------------------------------


def record_login_day(db: Session, *, user_id: int) -> None:
    """Stamp today's date for this user. Idempotent (composite PK).

    Called from the auth dependency on every authenticated request,
    so it MUST be safe inside an existing request-scoped transaction.
    We don't commit here — the surrounding request commits (or
    doesn't) on its own schedule. On Postgres we use ON CONFLICT DO
    NOTHING in a single statement; on SQLite (tests) we wrap the
    insert in a SAVEPOINT so a duplicate doesn't poison the outer
    transaction. Any unexpected failure is swallowed — auth must
    never break because the streak ticker hiccuped.
    """
    today = _today_utc()
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            stmt = pg_insert(LearnerLoginDay).values(user_id=user_id, day=today)
            stmt = stmt.on_conflict_do_nothing(
                constraint="pk_learner_login_days"
            )
            db.execute(stmt)
        else:
            with db.begin_nested():
                db.add(LearnerLoginDay(user_id=user_id, day=today))
                db.flush()
    except IntegrityError:
        # SAVEPOINT already rolled back; the row already exists.
        pass
    except Exception:  # pragma: no cover — best-effort, never fail auth
        pass


def compute_login_streak(db: Session, *, user_id: int) -> StreakInfo:
    """Current streak with the "kinder" grace policy (one missed day
    per ISO week is forgiven), plus the all-time longest streak.

    Walks back day-by-day from today over the login-day set, tracking
    misses per ISO week. The streak ends when a second miss inside
    the same ISO week is encountered — the streak length is the
    number of *present* days walked before that break.
    """
    today = _today_utc()
    cutoff = today - timedelta(days=STREAK_LOOKBACK_DAYS)
    login_days: set[date] = set(
        db.scalars(
            select(LearnerLoginDay.day).where(
                LearnerLoginDay.user_id == user_id,
                LearnerLoginDay.day >= cutoff,
            )
        ).all()
    )

    current = _streak_from(login_days, anchor=today)
    longest = _longest_streak(login_days)
    grace_used = _grace_used_this_week(login_days, today=today)
    return StreakInfo(current=current.length, longest=longest, grace_used_this_week=grace_used)


@dataclass
class _StreakWalk:
    length: int


def _streak_from(login_days: set[date], *, anchor: date) -> _StreakWalk:
    """Count consecutive days walking back from `anchor`, allowing
    STREAK_MISSES_ALLOWED_PER_WEEK misses per ISO week."""
    length = 0
    misses_in_current_week = 0
    current_week = anchor.isocalendar()[:2]
    day = anchor
    # Walk back at most STREAK_LOOKBACK_DAYS days — beyond that any
    # streak is "long enough" for display.
    for _ in range(STREAK_LOOKBACK_DAYS):
        week_of_day = day.isocalendar()[:2]
        if week_of_day != current_week:
            current_week = week_of_day
            misses_in_current_week = 0
        if day in login_days:
            length += 1
        else:
            misses_in_current_week += 1
            if misses_in_current_week > STREAK_MISSES_ALLOWED_PER_WEEK:
                break
            # else: this miss is forgiven by the grace policy; keep going
            # without incrementing length.
        day = day - timedelta(days=1)
    return _StreakWalk(length=length)


def _longest_streak(login_days: set[date]) -> int:
    """Max streak length ever recorded under the same grace policy."""
    if not login_days:
        return 0
    # Anchor a walk at every login day and take the longest length;
    # plenty fast for hundreds of rows. We anchor at each day rather
    # than walking once globally because the per-week grace makes the
    # streak non-monotonic.
    return max(_streak_from(login_days, anchor=d).length for d in login_days)


def _grace_used_this_week(login_days: set[date], *, today: date) -> int:
    """How many grace misses have already been consumed in the
    current ISO week so the UI can render "1 of 1 used"."""
    week_start = _week_start_for(today)
    # Count missed days from Monday up to (not past) today.
    misses = 0
    d = week_start
    while d <= today:
        if d not in login_days:
            misses += 1
        d = d + timedelta(days=1)
    return min(misses, STREAK_MISSES_ALLOWED_PER_WEEK)


# ---------------------------------------------------------------------------
# Points + level — Stage 1.5
# ---------------------------------------------------------------------------


def compute_points_total(db: Session, *, user_id: int) -> int:
    """Sum of every ledger entry for this user. Cheap — hundreds of
    rows tops; with proper indexes this is a single index scan."""
    total = db.scalar(
        select(func.coalesce(func.sum(LearnerPointsLedger.points), 0)).where(
            LearnerPointsLedger.user_id == user_id
        )
    )
    return int(total or 0)


def compute_level(points: int) -> LevelInfo:
    """Pick the highest tier whose `min_points` ≤ `points` and pre-
    compute the bar metadata for the dashboard."""
    chosen_index = 0
    for i, tier in enumerate(LEVEL_TIERS):
        if points >= int(tier["min_points"]):
            chosen_index = i
    tier = LEVEL_TIERS[chosen_index]
    next_tier = LEVEL_TIERS[chosen_index + 1] if chosen_index + 1 < len(LEVEL_TIERS) else None
    points_into = points - int(tier["min_points"])
    if next_tier is not None:
        points_to_next = max(0, int(next_tier["min_points"]) - points)
    else:
        points_to_next = None
    return LevelInfo(
        name=str(tier["name"]),
        blurb=str(tier["blurb"]),
        min_points=int(tier["min_points"]),
        next_name=str(next_tier["name"]) if next_tier else None,
        next_min_points=int(next_tier["min_points"]) if next_tier else None,
        points_into_level=points_into,
        points_to_next=points_to_next,
    )


def _add_points_row(
    db: Session,
    *,
    user_id: int,
    source: PointsSource,
    points: int,
    source_id: int | None = None,
    dedupe_key: str | None = None,
) -> bool:
    """Insert one ledger row. Returns True on insert, False on dedupe
    (UNIQUE violation on `dedupe_key`). Caller is responsible for the
    surrounding transaction; we just flush, not commit."""
    if points <= 0:
        return False
    row = LearnerPointsLedger(
        user_id=user_id,
        source_kind=source,
        source_id=source_id,
        points=points,
        dedupe_key=dedupe_key,
    )
    try:
        db.add(row)
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


def award_points_for_submission(db: Session, submission: Submission) -> int:
    """Award points unlocked by this submission's auto-graded answers.

    Awards
      - +1 per CORRECT auto-graded answer (CORRECT_ANSWER)
      - +5 if total_awarded equals max_marks (PERFECT_SCORE_BONUS)
      - +2 once per (user, day) the first time any submission lands
        (PRACTICE_DAY_BONUS)
      - +10 once per (user, week) when the weekly target is hit
        (WEEKLY_GOAL_BONUS)

    Idempotent via `dedupe_key` UNIQUE on the ledger — re-running for
    the same submission is safe. Returns total points awarded.
    """
    from app.models import Student  # local import; avoid cycles

    student = db.get(Student, submission.student_id)
    if student is None:
        return 0
    user_id = student.user_id

    total_awarded = 0

    # 1. Per-answer points. Each answer dedupes on (user, submission, qid)
    # so re-running the awarder for the same submission is a no-op.
    correct_count = 0
    for sa in submission.answers:
        if not sa.auto_graded:
            continue
        if (
            sa.marks_awarded is not None
            and sa.max_marks > 0
            and sa.marks_awarded >= sa.max_marks
        ):
            ok = _add_points_row(
                db,
                user_id=user_id,
                source=PointsSource.CORRECT_ANSWER,
                points=POINTS_PER_CORRECT_ANSWER,
                source_id=submission.id,
                dedupe_key=f"CORRECT_ANSWER:sub{submission.id}:q{sa.question_id}",
            )
            if ok:
                correct_count += 1
    total_awarded += correct_count * POINTS_PER_CORRECT_ANSWER

    # 2. Perfect-score bonus.
    if (
        submission.total_awarded is not None
        and submission.max_marks
        and submission.total_awarded >= submission.max_marks
    ):
        if _add_points_row(
            db,
            user_id=user_id,
            source=PointsSource.PERFECT_SCORE_BONUS,
            points=POINTS_PERFECT_SCORE_BONUS,
            source_id=submission.id,
            dedupe_key=f"PERFECT_SCORE:sub{submission.id}",
        ):
            total_awarded += POINTS_PERFECT_SCORE_BONUS

    # 3. Practice-day bonus — first submission of the day (UTC).
    today = (submission.submitted_at or _now_utc()).astimezone(timezone.utc).date()
    if _add_points_row(
        db,
        user_id=user_id,
        source=PointsSource.PRACTICE_DAY_BONUS,
        points=POINTS_PRACTICE_DAY_BONUS,
        source_id=submission.id,
        dedupe_key=f"PRACTICE_DAY:{today.isoformat()}",
    ):
        total_awarded += POINTS_PRACTICE_DAY_BONUS

    # 4. Weekly-goal bonus — once per ISO week the target is hit.
    week_start = _week_start_for(today)
    goal = get_or_create_current_goal(db, user_id=user_id)
    days_in_week = _practice_days_in_range(
        db,
        user_id=user_id,
        start=week_start,
        end_exclusive=week_start + timedelta(days=7),
    )
    if len(days_in_week) >= goal.target_days:
        if _add_points_row(
            db,
            user_id=user_id,
            source=PointsSource.WEEKLY_GOAL_BONUS,
            points=POINTS_WEEKLY_GOAL_BONUS,
            source_id=submission.id,
            dedupe_key=f"WEEKLY_GOAL:{week_start.isoformat()}",
        ):
            total_awarded += POINTS_WEEKLY_GOAL_BONUS

    return total_awarded


# ---------------------------------------------------------------------------
# Heatmap + weekly-goal-met progress — Stage 1.5
# ---------------------------------------------------------------------------


def compute_heatmap(
    db: Session, *, user_id: int, weeks: int = HEATMAP_WEEKS
) -> list[HeatmapCell]:
    """One cell per day for the last `weeks` ISO weeks ending in the
    current week. Day 0 of the returned list is the Monday `weeks - 1`
    weeks ago; day -1 is today. The frontend lays them out as a
    7-row × weeks-column grid."""
    week_start = _current_week_start()
    start = week_start - timedelta(weeks=weeks - 1)
    end_exclusive = week_start + timedelta(days=7)
    practice_days = set(
        _practice_days_in_range(
            db, user_id=user_id, start=start, end_exclusive=end_exclusive
        )
    )
    cells: list[HeatmapCell] = []
    d = start
    while d < end_exclusive:
        cells.append(HeatmapCell(day=d, practiced=d in practice_days))
        d = d + timedelta(days=1)
    return cells


def compute_weekly_goal_progress(
    db: Session, *, user_id: int
) -> WeeklyGoalProgress:
    """Aggregate the WEEKLY_GOAL_MET stamps into:
      - all-time count
      - current consecutive-week run ending in the current or most
        recently completed week.

    Implementation: pull the set of week_start dates from the
    WEEKLY_GOAL_MET stamps' metadata, then walk back week-by-week
    from the current week to count the consecutive run.
    """
    rows = db.scalars(
        select(LearnerStamp.stamp_metadata).where(
            LearnerStamp.user_id == user_id,
            LearnerStamp.kind == StampKind.WEEKLY_GOAL_MET,
        )
    ).all()
    week_starts: set[date] = set()
    for m in rows:
        if not m:
            continue
        ws = m.get("week_start") if isinstance(m, dict) else None
        if isinstance(ws, str):
            try:
                week_starts.add(date.fromisoformat(ws))
            except ValueError:  # pragma: no cover — defensive
                pass

    total = len(week_starts)

    # Walk back from the current week. We count the current week if
    # it's already hit; otherwise we start the run at the previous
    # completed week — this avoids penalising a learner mid-week who
    # hasn't yet hit the target.
    current_week = _current_week_start()
    run = 0
    cursor = current_week
    if cursor not in week_starts:
        cursor = cursor - timedelta(days=7)
    while cursor in week_starts:
        run += 1
        cursor = cursor - timedelta(days=7)

    return WeeklyGoalProgress(weeks_met_total=total, weeks_met_run=run)


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
