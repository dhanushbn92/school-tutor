"""Models for the child-centric "practice rhythm" feature set.

Stage 1 of `docs/child_centric_roadmap.md`:
  - LearnerWeeklyGoal: the per-week practice-days target each learner sets
    for themselves. Default is 4 days a week — chosen by feel, not pressure.
  - LearnerStamp: a small collectible earned for completing a quiz /
    worksheet attempt or hitting the weekly goal. Stamps are the visible
    reward layer; we deliberately avoid points / coins / currency-like
    mechanics for children.

Both tables are tiny and single-tenant per user. No foreign keys to
anything beyond `users`, so they remain unaffected by curriculum
changes, school migrations, etc.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StampKind(StrEnum):
    """What earned the stamp. New kinds may be added freely — UI does an
    exhaustive `switch` on these so a missing branch falls through to a
    "generic stamp" rendering rather than crashing."""

    # Awarded once per submission that completes (any score).
    QUIZ_COMPLETED = "QUIZ_COMPLETED"
    # Awarded when the submission scores 100% of available marks.
    PERFECT_SCORE = "PERFECT_SCORE"
    # Awarded on the first submission of a calendar day (UTC). This is
    # the "practice day" marker that backs the weekly-goal ring.
    PRACTICE_DAY = "PRACTICE_DAY"
    # Awarded when the learner's practice-day count reaches their
    # weekly goal for the ISO week the submission landed in. Awarded
    # at most once per (user, week_start).
    WEEKLY_GOAL_MET = "WEEKLY_GOAL_MET"


class LearnerWeeklyGoal(Base):
    """The number of practice days a learner aims for in a given ISO week.

    Stored per (user_id, week_start) so a learner can re-tune the goal
    week by week. `week_start` is the Monday of the ISO week, kept in
    UTC. We compute "did they hit it?" by comparing the count of
    distinct practice days against `target_days` for the same week.

    Defaults to 4 days/week — the magic number we picked because (a) a
    five-day school week leaves a margin of error, and (b) it lets
    weekends be properly off without breaking the streak feel.
    """

    __tablename__ = "learner_weekly_goals"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "week_start", name="uq_learner_weekly_goal_user_week"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Monday of the ISO week the goal applies to (UTC).
    week_start: Mapped[date] = mapped_column(Date, index=True)
    target_days: Mapped[int] = mapped_column(Integer, default=4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerStamp(Base):
    """A collectible earned by a learner for completing a practice action.

    Stamps are immutable once earned (no undelete, no revoke). The
    `metadata` JSON column carries context per stamp kind — e.g. the
    assessment_id for a QUIZ_COMPLETED, the score breakdown for a
    PERFECT_SCORE, the week_start for a WEEKLY_GOAL_MET. UI renderers
    consume this lazily; older stamps with sparse metadata still
    render via the generic fallback.

    PRACTICE_DAY and WEEKLY_GOAL_MET stamps are unique per their
    natural key (user+day, user+week) — enforced at the service layer
    rather than via UNIQUE constraints because the natural keys live
    inside the metadata blob.
    """

    __tablename__ = "learner_stamps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[StampKind] = mapped_column(String(32), index=True)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # Free-form per-kind payload. See the StampKind docstring for the
    # shape per kind.
    stamp_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
