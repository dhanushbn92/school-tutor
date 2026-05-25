"""Models for the child-centric "practice rhythm" feature set.

Stage 1 of `docs/child_centric_roadmap.md`:
  - LearnerWeeklyGoal: the per-week practice-days target each learner sets
    for themselves. Default is 4 days a week — chosen by feel, not pressure.
  - LearnerStamp: a small collectible earned for completing a quiz /
    worksheet attempt or hitting the weekly goal. Stamps are the visible
    reward layer; we deliberately avoid points / coins / currency-like
    mechanics for children.

Stage 2:
  - LearnerMistake: one row per (user, question) the learner got wrong
    on a graded attempt. Tracks consecutive_corrects so the row can be
    resolved (removed from the active list) after the learner gets it
    right twice in a row — a small barrier to prevent lucky guesses
    from prematurely retiring a question from the review pool.

All tables here are single-tenant per user with no curriculum FKs
beyond `users` (and `questions` for mistakes).
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
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


class LearnerMistake(Base):
    """A question the learner answered incorrectly on at least one
    graded attempt.

    Upserted on every submission: the first wrong answer creates the
    row; subsequent attempts (either via a fresh quiz containing the
    same question or via the dedicated `/me/mistakes/{q}/attempt`
    retry endpoint) either reset `consecutive_corrects` to 0 (wrong
    again) or increment it (right).

    A mistake is "resolved" once `consecutive_corrects >= 2` — the
    twice-right rule is a small guard against lucky guesses
    prematurely retiring a question from the review pool. Resolved
    rows stay in the DB for audit but are filtered out of the active
    list.

    Subjective questions never enter this table: they aren't
    auto-graded so there's no objective verdict to key off. Only
    `auto_graded=true` submission_answers contribute.
    """

    __tablename__ = "learner_mistakes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "question_id", name="uq_learner_mistake_user_question"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    first_wrong_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    consecutive_corrects: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# Stage 1.5 — login streak + points + levels
# ---------------------------------------------------------------------------


class LearnerLoginDay(Base):
    """One row per (user, day) the learner was authenticated on.

    The auth dependency upserts today's row on every authenticated
    request from a learner — cheap because the table has no other
    columns and the upsert is a no-op when the row already exists.

    Composite PK (user_id, day) means a duplicate write is a no-op at
    the DB level (we catch the IntegrityError and continue). This is
    the source-of-truth for the "login streak" counter and the
    consistency heatmap.
    """

    __tablename__ = "learner_login_days"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "day", name="pk_learner_login_days"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date] = mapped_column(Date)


class PointsSource(StrEnum):
    """What earned the points. New sources may be added freely.

    The numeric award is decided service-side, not stored as a per-
    enum constant, so we can tune rewards without a migration. The
    enum just names the *event*.
    """

    CORRECT_ANSWER = "CORRECT_ANSWER"
    PERFECT_SCORE_BONUS = "PERFECT_SCORE_BONUS"
    PRACTICE_DAY_BONUS = "PRACTICE_DAY_BONUS"
    WEEKLY_GOAL_BONUS = "WEEKLY_GOAL_BONUS"


class LearnerAudioPreferences(Base):
    """Per-learner read-aloud preferences (Stage 8).

    Lazily created — first GET /me/audio-preferences inserts a row
    with defaults (`autoplay_questions=False`, `preferred_voice_uri=None`).
    The actual TTS happens in the browser via SpeechSynthesis API;
    this table just remembers the learner's picks so they survive
    page reloads and follow them across devices.
    """

    __tablename__ = "learner_audio_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_learner_audio_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    autoplay_questions: Mapped[bool] = mapped_column(Boolean, default=False)
    # Free-form URI from SpeechSynthesisVoice.voiceURI. Null means
    # "use the browser default for the text's language".
    preferred_voice_uri: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerMascotState(Base):
    """Per-learner state for the Vidyārthi mascot companion (Stage 5).

    Lazily created — the first GET /me/mascot for a learner inserts a
    row with `enabled=True` and `current_outfit='default'`. Toggling
    visibility or equipping a new outfit updates the same row.

    `current_outfit` is a free-form string for forward-compatibility:
    new outfits can be shipped as a config change without a
    migration. Until the unlock pipeline ships in a follow-up, only
    "default" is a valid value.
    """

    __tablename__ = "learner_mascot_state"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_learner_mascot_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    current_outfit: Mapped[str] = mapped_column(String(40), default="default")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerPointsLedger(Base):
    """Append-only ledger of point awards.

    Each row carries the source kind + an optional source_id (e.g. a
    submission_id) so we can audit and dedupe. `dedupe_key` is a
    natural-key string for sources awarded at most once per (user,
    natural-key) — e.g. `"PERFECT_SCORE_BONUS:sub42"` — protected by
    a UNIQUE constraint so racy concurrent writes can't double-award.

    The "total points" displayed on the dashboard is a SUM over this
    table for the user. With ledger volume in the hundreds per
    learner, the sum is cheap; if it ever isn't we add a denormalised
    column. Until then, source-of-truth events win.
    """

    __tablename__ = "learner_points_ledger"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "dedupe_key", name="uq_points_ledger_user_dedupe"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_kind: Mapped[PointsSource] = mapped_column(String(40))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int] = mapped_column(Integer)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    dedupe_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
