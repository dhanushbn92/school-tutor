"""Mastery tracking via exponentially-weighted moving average over question scores.

Mastery is stored per `(student, outcome, cognitive_bucket)`. EWMA update rule:

    mastery_new = alpha * observed + (1 - alpha) * mastery_old

where `observed = marks_awarded / max_marks` in [0, 1].

The cognitive bucket comes from rolling each question's 6-level Bloom value
(`question.cognitive_level`) up to FACTUAL/UNDERSTANDING/APPLICATION via
`app.services.cognitive.to_bucket`. A student can therefore have up to three
mastery rows per outcome — one per bucket the bank tested them on.

Updates fire when a `Submission` transitions into `EVALUATED`. Re-grading an
already-EVALUATED submission does NOT retrigger mastery updates — mastery drift
from grade-edits is a known MVP limitation; the `scripts.recompute_mastery`
script handles full rebuilds.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import Submission, SubmissionAnswer
from app.models.curriculum import Book, Chapter, LearningOutcome, SchoolClass, Subject
from app.models.mastery import CognitiveBucket, SkillMastery
from app.models.question import Question
from app.services.cognitive import to_bucket


EWMA_ALPHA = 0.3
CORRECT_THRESHOLD = 0.5


def apply_updates_for_submission(db: Session, submission: Submission) -> int:
    """EWMA-update one mastery row per (outcome, cognitive_bucket) touched.

    Multiple questions on the same (outcome, bucket) pair are aggregated into a
    single observation (`sum(marks) / sum(max)`) so each submission contributes
    exactly one EWMA update per pair — no path-dependent compounding across
    questions in the same test.

    Returns the number of (outcome, bucket) pairs touched. Caller commits.
    """
    answers = db.scalars(
        select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)
    ).all()

    per_pair: dict[tuple[int, CognitiveBucket], list[tuple[int, int]]] = {}
    for answer in answers:
        if answer.marks_awarded is None or answer.max_marks <= 0:
            continue
        question = db.get(Question, answer.question_id)
        if question is None or question.outcome_id is None:
            continue
        bucket = to_bucket(question.cognitive_level)
        per_pair.setdefault((question.outcome_id, bucket), []).append(
            (answer.marks_awarded, answer.max_marks)
        )

    for (outcome_id, bucket), entries in per_pair.items():
        awarded = sum(a for a, _ in entries)
        capacity = sum(m for _, m in entries)
        observed = max(0.0, min(1.0, awarded / capacity))
        _upsert_mastery(
            db,
            student_id=submission.student_id,
            outcome=db.get(LearningOutcome, outcome_id),
            bucket=bucket,
            observed=observed,
            occurred_at=submission.evaluated_at or submission.submitted_at,
        )
        db.flush()
    return len(per_pair)


def _upsert_mastery(
    db: Session,
    *,
    student_id: int,
    outcome: LearningOutcome | None,
    bucket: CognitiveBucket,
    observed: float,
    occurred_at: datetime | None,
) -> SkillMastery:
    if outcome is None:
        raise ValueError("outcome cannot be None when upserting mastery")

    row = db.scalar(
        select(SkillMastery).where(
            SkillMastery.student_id == student_id,
            SkillMastery.outcome_id == outcome.id,
            SkillMastery.cognitive_bucket == bucket,
        )
    )
    is_correct = observed >= CORRECT_THRESHOLD
    timestamp = occurred_at or datetime.now(timezone.utc)

    if row is None:
        row = SkillMastery(
            student_id=student_id,
            outcome_id=outcome.id,
            chapter_id=outcome.chapter_id,
            topic_id=outcome.topic_id,
            cognitive_bucket=bucket,
            mastery=observed,
            attempts=1,
            correct=1 if is_correct else 0,
            last_attempt_at=timestamp,
        )
        db.add(row)
        return row

    row.mastery = EWMA_ALPHA * observed + (1 - EWMA_ALPHA) * row.mastery
    row.attempts += 1
    if is_correct:
        row.correct += 1
    row.last_attempt_at = timestamp
    return row


def build_student_grid(
    db: Session,
    *,
    student_id: int,
    class_level: int,
    subject_id: int,
) -> dict:
    """Return a chapter -> outcome mastery grid for a student, ready for a heatmap.

    Includes every outcome the subject syllabus defines, with `mastery=null` for
    any the student has not yet attempted.
    """
    subject = db.get(Subject, subject_id)
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

    mastery_rows = db.scalars(
        select(SkillMastery).where(SkillMastery.student_id == student_id)
    ).all()
    mastery_by_outcome: dict[int, list[SkillMastery]] = {}
    for row in mastery_rows:
        mastery_by_outcome.setdefault(row.outcome_id, []).append(row)

    bucket_order = [
        CognitiveBucket.FACTUAL,
        CognitiveBucket.UNDERSTANDING,
        CognitiveBucket.APPLICATION,
    ]

    chapter_blocks: list[dict] = []
    total_outcomes = 0
    attempted = 0
    attempted_sum = 0.0
    bucket_totals: dict[str, dict[str, float | int]] = {
        b.value: {"sum": 0.0, "attempted": 0} for b in bucket_order
    }
    for chapter in chapters:
        outcomes_payload = []
        for outcome in sorted(chapter.learning_outcomes, key=lambda lo: lo.code):
            total_outcomes += 1
            rows = mastery_by_outcome.get(outcome.id, [])
            by_bucket = {row.cognitive_bucket: row for row in rows}

            buckets_payload: dict[str, dict | None] = {}
            for b in bucket_order:
                br = by_bucket.get(b)
                if br is None:
                    buckets_payload[b.value] = None
                else:
                    buckets_payload[b.value] = {
                        "mastery": round(br.mastery, 3),
                        "attempts": br.attempts,
                        "correct": br.correct,
                        "last_attempt_at": br.last_attempt_at.isoformat() if br.last_attempt_at else None,
                    }
                    bucket_totals[b.value]["sum"] += br.mastery
                    bucket_totals[b.value]["attempted"] += 1

            total_attempts = sum(br.attempts for br in rows)
            total_correct = sum(br.correct for br in rows)
            combined_mastery: float | None
            if rows and total_attempts > 0:
                combined_mastery = (
                    sum(br.mastery * br.attempts for br in rows) / total_attempts
                )
                attempted += 1
                attempted_sum += combined_mastery
            else:
                combined_mastery = None

            last_attempt = max(
                (br.last_attempt_at for br in rows if br.last_attempt_at),
                default=None,
            )
            outcomes_payload.append(
                {
                    "outcome_id": outcome.id,
                    "code": outcome.code,
                    "description": outcome.description,
                    "bloom_level": outcome.bloom_level.value,
                    "mastery": round(combined_mastery, 3) if combined_mastery is not None else None,
                    "attempts": total_attempts,
                    "correct": total_correct,
                    "last_attempt_at": last_attempt.isoformat() if last_attempt else None,
                    "buckets": buckets_payload,
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

    bucket_summary = {
        b: {
            "outcomes_attempted": int(bucket_totals[b]["attempted"]),
            "average_mastery": (
                round(bucket_totals[b]["sum"] / bucket_totals[b]["attempted"], 3)
                if bucket_totals[b]["attempted"]
                else None
            ),
        }
        for b in bucket_totals
    }

    return {
        "student_id": student_id,
        "class_level": class_level,
        "subject_id": subject_id,
        "subject": subject.name if subject else None,
        "chapters": chapter_blocks,
        "summary": {
            "outcomes_total": total_outcomes,
            "outcomes_attempted": attempted,
            "average_mastery": round(attempted_sum / attempted, 3) if attempted else None,
            "by_bucket": bucket_summary,
        },
    }
