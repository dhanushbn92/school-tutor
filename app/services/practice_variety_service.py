"""Service for the practice-variety hub (Stage 7 of the
child-centric roadmap).

Three lightweight modes that complement the main quick-quiz flow:

  - Surprise me  → one random question, scoped to the learner's
                   syllabus. Inline reveal, no submission.
  - Flashcards   → N factual / REMEMBER-bucket questions for flip-
                   card practice. No grading; the UI just tracks
                   "got it" / "tricky" client-side for the current
                   session.
  - Speedrun     → 5-question burst with a tight timer. Reuses the
                   existing /me/quick-quiz endpoint with preset
                   params — no new endpoint is needed here.

This service supplies the read-only sampling for the first two.
Authorisation is handled at the endpoint layer with
`require_learner`; here we trust the user_id we're given.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Book,
    Chapter,
    Enrollment,
    EnrollmentStatus,
    Question,
    QuestionStatus,
    Section,
    SkillMastery,  # noqa: F401 (intentional import to register the model)
    Student,
    Subject,
    User,
)
from app.models.curriculum import BloomLevel, SchoolClass


@dataclass
class LearnerSyllabus:
    """The slice of the syllabus a learner can practice against.

    All three modes share the same scope rule: never sample a question
    that isn't in the learner's class+subject set. For individual
    learners that's a tiny scope (one personal section); for school
    students it widens with their enrolments.
    """

    class_level: int
    subject_ids: list[int]
    chapter_ids: list[int]


class PracticeVarietyError(Exception):
    """Domain-level error for the practice-variety pipeline."""


def resolve_syllabus(db: Session, *, user: User) -> LearnerSyllabus:
    """Find the learner's (class_level, subject_ids, chapter_ids).

    Picks the first active enrolment and uses that section's
    class_level. Subjects come from `Subject.class_id == section
    class_id`. Chapters come from each subject's books.

    Raises `PracticeVarietyError` if the learner has no active
    enrolment / no chapters available — the endpoint translates this
    into a friendly 400 so the UI can render an empty state.
    """
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise PracticeVarietyError(
            "We can't find a student profile for this account."
        )
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrollment is None:
        raise PracticeVarietyError(
            "You don't have an active enrolment yet. "
            "Contact your school admin or finish onboarding."
        )
    section = db.get(Section, enrollment.section_id)
    if section is None:
        raise PracticeVarietyError("Your enrolment is missing a section.")
    school_class = db.get(SchoolClass, section.class_id)
    if school_class is None:
        raise PracticeVarietyError("Your section is missing a class.")

    subjects = list(
        db.scalars(
            select(Subject).where(Subject.class_id == section.class_id)
        ).all()
    )
    subject_ids = [s.id for s in subjects]
    if not subject_ids:
        raise PracticeVarietyError(
            "No subjects are configured for your class yet."
        )

    chapters = list(
        db.scalars(
            select(Chapter).join(Book, Chapter.book_id == Book.id).where(
                Book.subject_id.in_(subject_ids)
            )
        ).all()
    )
    chapter_ids = [c.id for c in chapters]
    if not chapter_ids:
        raise PracticeVarietyError(
            "No chapters are available for your class yet."
        )

    return LearnerSyllabus(
        class_level=school_class.level,
        subject_ids=subject_ids,
        chapter_ids=chapter_ids,
    )


# ---------------------------------------------------------------------------
# Surprise me — one random question from the learner's syllabus
# ---------------------------------------------------------------------------


def pick_surprise(
    db: Session, *, user: User, rng: random.Random | None = None
) -> Question:
    """Return one APPROVED question from any of the learner's
    chapters. Uniform-random across the eligible pool.

    The "random" here is best-effort: we let the DB do the heavy
    lifting with ORDER BY RANDOM() + LIMIT 1. For Postgres this is
    fast enough at MVP volumes (thousands of rows, not millions); if
    the bank grows we'll switch to TABLESAMPLE or a precomputed
    `Question.random_bucket` column.
    """
    _ = rng  # placeholder for deterministic tests
    syllabus = resolve_syllabus(db, user=user)
    from sqlalchemy import func as _f

    question = db.scalar(
        select(Question)
        .where(
            Question.chapter_id.in_(syllabus.chapter_ids),
            Question.status == QuestionStatus.APPROVED,
        )
        .order_by(_f.random())
        .limit(1)
    )
    if question is None:
        raise PracticeVarietyError(
            "No approved questions in your syllabus yet — check back soon."
        )
    return question


# ---------------------------------------------------------------------------
# Flashcards — N factual / REMEMBER-bucket questions
# ---------------------------------------------------------------------------


def sample_flashcards(
    db: Session,
    *,
    user: User,
    count: int = 10,
    chapter_id: int | None = None,
) -> list[Question]:
    """N factual flip-card questions. Prefers `BloomLevel.REMEMBER`
    but falls back to UNDERSTAND if the REMEMBER pool is too small —
    practice surface should never empty-state on a small bank.

    `chapter_id`, if supplied, scopes to a single chapter (still
    enforced against the learner's syllabus). Without it, the whole
    syllabus is in play."""
    syllabus = resolve_syllabus(db, user=user)
    chapter_ids = syllabus.chapter_ids
    if chapter_id is not None:
        if chapter_id not in chapter_ids:
            raise PracticeVarietyError(
                "That chapter isn't part of your syllabus."
            )
        chapter_ids = [chapter_id]

    from sqlalchemy import func as _f

    def _query(bloom: BloomLevel | None) -> list[Question]:
        stmt = (
            select(Question)
            .where(
                Question.chapter_id.in_(chapter_ids),
                Question.status == QuestionStatus.APPROVED,
            )
            .order_by(_f.random())
            .limit(count)
        )
        if bloom is not None:
            stmt = stmt.where(Question.cognitive_level == bloom)
        return list(db.scalars(stmt).all())

    rows = _query(BloomLevel.REMEMBER)
    if len(rows) < count:
        # Top up from UNDERSTAND-bucket questions so the deck still
        # has `count` cards even on a thin chapter.
        extras = _query(BloomLevel.UNDERSTAND)
        seen = {q.id for q in rows}
        for q in extras:
            if q.id in seen:
                continue
            rows.append(q)
            if len(rows) >= count:
                break
    if not rows:
        raise PracticeVarietyError(
            "No flashcard-friendly questions available yet."
        )
    return rows[:count]


def question_to_card_dict(q: Question) -> dict:
    """Shape one question for the practice-variety endpoints. Mirrors
    `QuestionRead` but trims fields the UI doesn't need at this
    surface (no review_notes / created_by / status etc.)."""
    return {
        "id": q.id,
        "chapter_id": q.chapter_id,
        "type": q.type.value if hasattr(q.type, "value") else q.type,
        "difficulty": q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty,
        "cognitive_level": (
            q.cognitive_level.value
            if hasattr(q.cognitive_level, "value")
            else q.cognitive_level
        ),
        "text": q.text,
        "options": q.options or None,
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "marks": q.marks,
        "outcome_code": q.outcome_code,
    }
