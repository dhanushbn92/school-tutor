"""Service for the "things I got wrong" feature (Stage 2 of the
child-centric roadmap).

What it does
- Maintains one LearnerMistake row per (user, question) the learner
  has answered incorrectly on a graded attempt.
- Tracks `consecutive_corrects`: every subsequent correct answer
  bumps it; any wrong answer resets it to 0. Rows with
  consecutive_corrects >= 2 are "resolved" and filtered out of the
  active list — small guard against lucky guesses retiring a
  question prematurely.
- Provides a single-question retry path so the learner can practise
  individual mistakes without taking a whole quiz; the retry does
  NOT create a Submission row (it's not a fresh attempt that should
  count toward mastery — it's revision practice).

Only auto-gradable question types contribute (MCQ / TRUE_FALSE /
FILL_BLANK). Subjective answers have no objective verdict so they're
silently skipped on the upsert path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Book,
    Chapter,
    LearnerMistake,
    Question,
    Submission,
    Subject,
)
from app.services.grading import auto_grade


RESOLVED_THRESHOLD = 2  # consecutive_corrects required to resolve a mistake

# Stage 9 — number of consecutive wrong retries before the UI offers
# a hint. Tuned to be encouraging rather than punitive: three honest
# tries before we step in, not one. Change here if it feels too
# eager or too slow in practice.
HINT_THRESHOLD = 3


def upsert_for_submission(db: Session, submission: Submission) -> None:
    """Walk the submission's auto-graded answers and update the
    learner's mistake rows. Idempotent; safe to call inside the
    post-commit stamp-awarding block in submission_service.

    Behaviour per answer:
      - Wrong   → upsert mistake row, reset consecutive_corrects to 0.
      - Right   → if a mistake row exists, increment consecutive_corrects.
                  If it doesn't, do nothing (a first-correct answer
                  isn't a "mistake").
      - Subjective (auto_graded=False) → skipped entirely.
    """
    from app.models import Student  # local import to dodge cycles

    student = db.get(Student, submission.student_id)
    if student is None:
        return
    user_id = student.user_id
    now = datetime.now(timezone.utc)

    for sa in submission.answers:
        if not sa.auto_graded:
            continue
        is_correct = (
            sa.marks_awarded is not None
            and sa.max_marks > 0
            and sa.marks_awarded >= sa.max_marks
        )
        existing = db.scalar(
            select(LearnerMistake).where(
                LearnerMistake.user_id == user_id,
                LearnerMistake.question_id == sa.question_id,
            )
        )
        if existing is None:
            # No history for this question. Only create a row if the
            # answer was wrong — a first-time correct doesn't belong
            # in the mistakes table.
            if not is_correct:
                db.add(
                    LearnerMistake(
                        user_id=user_id,
                        question_id=sa.question_id,
                        first_wrong_at=now,
                        last_attempted_at=now,
                        consecutive_corrects=0,
                        wrong_streak=1,
                    )
                )
        else:
            existing.last_attempted_at = now
            if is_correct:
                existing.consecutive_corrects += 1
                existing.wrong_streak = 0
            else:
                existing.consecutive_corrects = 0
                existing.wrong_streak = (existing.wrong_streak or 0) + 1


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

@dataclass
class MistakeListEntry:
    mistake: LearnerMistake
    question: Question
    chapter: Chapter | None
    subject: Subject | None


def list_active(
    db: Session,
    *,
    user_id: int,
    chapter_id: int | None = None,
    subject_id: int | None = None,
    limit: int = 100,
) -> list[MistakeListEntry]:
    """Active mistakes for the learner — rows below the resolved
    threshold. Pre-joined with question + chapter + subject so the
    UI can render rich cards in a single round-trip.

    Sorted by `last_attempted_at` desc so the freshest pain shows
    first; learners are most likely to want to retry what they just
    got wrong.
    """
    stmt = (
        select(LearnerMistake)
        .where(
            LearnerMistake.user_id == user_id,
            LearnerMistake.consecutive_corrects < RESOLVED_THRESHOLD,
        )
        .order_by(desc(LearnerMistake.last_attempted_at))
        .limit(limit)
    )
    mistakes = list(db.scalars(stmt).all())
    if not mistakes:
        return []

    # Bulk-fetch the questions + chapter/subject context in one go.
    question_ids = [m.question_id for m in mistakes]
    questions_by_id = {
        q.id: q
        for q in db.scalars(
            select(Question).where(Question.id.in_(question_ids))
        ).all()
    }
    chapter_ids = {q.chapter_id for q in questions_by_id.values() if q.chapter_id}
    chapters_by_id: dict[int, Chapter] = {}
    if chapter_ids:
        chapters_by_id = {
            c.id: c
            for c in db.scalars(
                select(Chapter).where(Chapter.id.in_(chapter_ids))
            ).all()
        }
    # Subject via book.subject_id; chapters know book_id.
    book_ids = {c.book_id for c in chapters_by_id.values() if c.book_id}
    subject_by_book: dict[int, Subject] = {}
    if book_ids:
        books = list(
            db.scalars(select(Book).where(Book.id.in_(book_ids))).all()
        )
        subject_ids = {b.subject_id for b in books if b.subject_id}
        subjects_by_id = {
            s.id: s
            for s in db.scalars(
                select(Subject).where(Subject.id.in_(subject_ids))
            ).all()
        }
        subject_by_book = {
            b.id: subjects_by_id[b.subject_id]
            for b in books
            if b.subject_id in subjects_by_id
        }

    entries: list[MistakeListEntry] = []
    for m in mistakes:
        q = questions_by_id.get(m.question_id)
        if q is None:
            # Question deleted out from under the mistake row — skip
            # silently and let the row stay (cleanup is a separate
            # housekeeping concern).
            continue
        chapter = chapters_by_id.get(q.chapter_id) if q.chapter_id else None
        if chapter_id is not None and (chapter is None or chapter.id != chapter_id):
            continue
        subject = (
            subject_by_book.get(chapter.book_id)
            if chapter and chapter.book_id
            else None
        )
        if subject_id is not None and (subject is None or subject.id != subject_id):
            continue
        entries.append(
            MistakeListEntry(
                mistake=m,
                question=q,
                chapter=chapter,
                subject=subject,
            )
        )
    return entries


def count_active(db: Session, *, user_id: int) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.count(LearnerMistake.id)).where(
                LearnerMistake.user_id == user_id,
                LearnerMistake.consecutive_corrects < RESOLVED_THRESHOLD,
            )
        )
        or 0
    )


# ---------------------------------------------------------------------------
# Single-question retry
# ---------------------------------------------------------------------------

@dataclass
class RetryResult:
    correct: bool
    correct_answer: str
    explanation: str | None
    consecutive_corrects: int
    resolved: bool
    # Stage 9 — wrong-side streak (reset to 0 on correct). The UI uses
    # this to decide when to surface a hint and when to celebrate
    # "success after struggle". `was_struggling` is set when the
    # retry was correct AFTER >= 2 wrong attempts in a row — the
    # frontend lights up a bigger celebration in that case.
    wrong_streak: int
    hint_available: bool
    was_struggling: bool


def record_retry_attempt(
    db: Session, *, user_id: int, question_id: int, answer_text: str | None
) -> RetryResult:
    """Grade a single retry attempt and update the LearnerMistake row.

    Returns the verdict + the correct answer + explanation so the
    front-end can render feedback inline. Does NOT create a
    Submission — this is revision practice, not a fresh attempt.

    Raises ValueError when the question is subjective or when there's
    no mistake row for this (user, question) pair (since a retry only
    makes sense for a known mistake).
    """
    question = db.get(Question, question_id)
    if question is None:
        raise ValueError("Question not found")

    mistake = db.scalar(
        select(LearnerMistake).where(
            LearnerMistake.user_id == user_id,
            LearnerMistake.question_id == question_id,
        )
    )
    if mistake is None:
        raise ValueError("This question is not in your mistakes list.")

    awarded, was_auto, _ = auto_grade(question, answer_text, max_marks=question.marks)
    if not was_auto:
        raise ValueError(
            "This question type doesn't support retry grading."
        )

    is_correct = awarded is not None and awarded >= question.marks
    now = datetime.now(timezone.utc)
    mistake.last_attempted_at = now
    # Snapshot the pre-update wrong-streak so the response can flag
    # "this was a success-after-struggle". `was_struggling` is True
    # only when this attempt was correct AND the learner had already
    # gotten the question wrong at least twice in a row before.
    prior_wrong_streak = mistake.wrong_streak or 0
    if is_correct:
        mistake.consecutive_corrects += 1
        mistake.wrong_streak = 0
    else:
        mistake.consecutive_corrects = 0
        mistake.wrong_streak = prior_wrong_streak + 1
    db.commit()

    # Stamp awarding (encouragement layer). Fire-and-forget: a stamp
    # bug must never poison the retry. We award MISTAKE_CLEARED +
    # TEN_MISTAKES_CLEARED in their own transaction.
    resolved = mistake.consecutive_corrects >= RESOLVED_THRESHOLD
    if resolved:
        try:
            from app.services import learner_practice_service

            learner_practice_service.award_mistake_stamps(
                db, user_id=user_id, resolved=True
            )
            db.commit()
        except Exception:  # pragma: no cover — best-effort
            db.rollback()

    return RetryResult(
        correct=is_correct,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        consecutive_corrects=mistake.consecutive_corrects,
        resolved=resolved,
        wrong_streak=mistake.wrong_streak,
        hint_available=mistake.wrong_streak >= HINT_THRESHOLD,
        was_struggling=is_correct and prior_wrong_streak >= 2,
    )


# ---------------------------------------------------------------------------
# Serialisation helper for the API layer
# ---------------------------------------------------------------------------

def entry_to_dict(entry: MistakeListEntry) -> dict[str, Any]:
    q = entry.question
    return {
        "question_id": q.id,
        "question_text": q.text,
        "question_type": q.type.value if hasattr(q.type, "value") else q.type,
        "options": (q.options or {}).get("choices") if q.options else None,
        "marks": q.marks,
        "difficulty": q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty,
        "outcome_code": q.outcome_code,
        "chapter_id": entry.chapter.id if entry.chapter else None,
        "chapter_title": entry.chapter.title if entry.chapter else None,
        "chapter_number": entry.chapter.chapter_number if entry.chapter else None,
        "subject_id": entry.subject.id if entry.subject else None,
        "subject_name": entry.subject.name if entry.subject else None,
        "first_wrong_at": entry.mistake.first_wrong_at,
        "last_attempted_at": entry.mistake.last_attempted_at,
        "consecutive_corrects": entry.mistake.consecutive_corrects,
        "wrong_streak": entry.mistake.wrong_streak or 0,
        "hint_available": (entry.mistake.wrong_streak or 0) >= HINT_THRESHOLD,
    }
