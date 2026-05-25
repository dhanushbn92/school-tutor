from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    Submission,
    SubmissionAnswer,
    SubmissionStatus,
)
from app.models.question import Question
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    Section,
    Student,
    Teacher,
    User,
    UserRole,
)
from app.services import learner_practice_service, mastery_service
from app.services.grading import auto_grade


class SubmissionError(Exception):
    """Domain-level error for invalid submission operations."""


def create_submission(
    db: Session,
    *,
    user: User,
    assessment_id: int,
    answers: dict[int, str],
) -> Submission:
    """Student submits answers. Auto-grades where possible.

    `answers` is a `{question_id: answer_text}` map. Questions not in the map
    get a blank answer (0 marks for auto-gradable types).
    """
    if user.role not in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        raise SubmissionError("Only students or individual learners can submit assessments")
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise SubmissionError("No student record for this user")

    assessment = db.scalar(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(joinedload(Assessment.questions).joinedload(AssessmentQuestion.question))
    )
    if assessment is None:
        raise SubmissionError(f"Assessment {assessment_id} not found")
    if assessment.status != AssessmentStatus.PUBLISHED:
        raise SubmissionError(f"Assessment is {assessment.status.value}, not PUBLISHED")

    enrolled = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.section_id == assessment.section_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrolled is None:
        raise SubmissionError("You are not enrolled in this assessment's section")

    existing = db.scalar(
        select(Submission).where(
            Submission.assessment_id == assessment.id,
            Submission.student_id == student.id,
        )
    )
    if existing is not None:
        if user.role == UserRole.INDIVIDUAL_LEARNER:
            # Self-learners can retake their own quizzes — wipe the old
            # submission and start fresh. Mastery already absorbed the prior
            # observation; the new attempt will EWMA on top of it.
            db.delete(existing)
            db.flush()
        else:
            raise SubmissionError("You have already submitted this assessment")

    now = datetime.now(timezone.utc)
    is_late = assessment.due_at is not None and now > assessment.due_at

    submission = Submission(
        assessment_id=assessment.id,
        student_id=student.id,
        status=SubmissionStatus.SUBMITTED,
        submitted_at=now,
        max_marks=assessment.total_marks,
    )
    db.add(submission)
    db.flush()

    # Subjective questions (SHORT_ANSWER / LONG_ANSWER / CASE_BASED) are no
    # longer auto-graded — the keyword/rubric grader was retired because the
    # results were unreliable. Those answers come back as
    # (marks_awarded=None, auto_graded=False) and the frontend shows them
    # next to the answer key for student self-evaluation. AI grading will
    # replace this stub later.
    auto_graded_total = 0
    for aq in assessment.questions:
        question: Question = aq.question
        effective_marks = aq.marks_override or question.marks
        raw_answer = answers.get(question.id)

        awarded, auto, grading_details = auto_grade(
            question, raw_answer, max_marks=effective_marks
        )
        db.add(
            SubmissionAnswer(
                submission_id=submission.id,
                question_id=question.id,
                answer_text=raw_answer,
                marks_awarded=awarded,
                max_marks=effective_marks,
                auto_graded=auto,
                grading_details=grading_details,
            )
        )
        if auto:
            auto_graded_total += awarded or 0

    if is_late:
        submission.status = SubmissionStatus.LATE
    else:
        # The submission is "evaluated" once objective questions are scored.
        # Subjective answers stay marks_awarded=None and don't contribute to
        # total_awarded — mastery_service.apply_updates_for_submission also
        # skips None scores, so subjective answers won't pollute mastery.
        submission.status = SubmissionStatus.EVALUATED
        submission.total_awarded = auto_graded_total
        submission.evaluated_at = now
        db.flush()
        mastery_service.apply_updates_for_submission(db, submission)

    db.commit()
    db.refresh(submission)

    # Award practice stamps in a SEPARATE transaction after the
    # submission has already committed (child-centric roadmap, Stage 1).
    # Doing this post-commit means any stamp-awarding bug can never
    # poison the submission itself — a stamp failure costs a stamp,
    # never a quiz attempt. If the stamp write fails the user sees
    # their score; the worst case is a missing +1 on their stamp book.
    try:
        learner_practice_service.award_stamps_for_submission(db, submission)
        db.commit()
    except Exception:  # pragma: no cover — best-effort
        db.rollback()
        # Intentionally swallowed. The submission is safe.

    return submission


def grade_answer(
    db: Session,
    *,
    user: User,
    submission_id: int,
    question_id: int,
    marks_awarded: int,
    teacher_remark: str | None = None,
) -> SubmissionAnswer:
    """Teacher records marks for a single (submission, question)."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError(f"Submission {submission_id} not found")
    if not _user_can_grade_submission(db, user, submission):
        raise SubmissionError("You cannot grade this submission")

    answer = db.scalar(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == submission_id,
            SubmissionAnswer.question_id == question_id,
        )
    )
    if answer is None:
        raise SubmissionError(f"Answer for question {question_id} not found on this submission")
    if marks_awarded < 0 or marks_awarded > answer.max_marks:
        raise SubmissionError(
            f"marks_awarded must be between 0 and {answer.max_marks} (got {marks_awarded})"
        )

    answer.marks_awarded = marks_awarded
    answer.auto_graded = False
    if teacher_remark is not None:
        answer.teacher_remark = teacher_remark

    _refresh_submission_totals(db, submission)
    db.commit()
    db.refresh(answer)
    return answer


def save_uploaded_file(
    db: Session,
    *,
    user: User,
    submission_id: int,
    relative_path: str,
) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError(f"Submission {submission_id} not found")
    if not _user_can_grade_submission(db, user, submission):
        raise SubmissionError("You cannot attach files to this submission")
    submission.uploaded_file_url = relative_path
    db.commit()
    db.refresh(submission)
    return submission


def list_submissions_for_assessment(
    db: Session, *, user: User, assessment_id: int
) -> list[Submission]:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        return []
    if not _user_can_grade_submission_section(db, user, assessment.section_id):
        return []
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.assessment_id == assessment_id)
            .order_by(Submission.id)
        )
    )


def _refresh_submission_totals(db: Session, submission: Submission) -> None:
    """Recompute total_awarded after a teacher grade_answer call.

    Subjective answers that are still in self-eval (marks_awarded=None) don't
    block the submission from being EVALUATED — they're just excluded from the
    total. Once a teacher does eventually grade them (or AI grading lands and
    backfills), the total is bumped up.
    """
    was_evaluated = submission.status == SubmissionStatus.EVALUATED
    answers = db.scalars(
        select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)
    ).all()

    submission.total_awarded = sum(a.marks_awarded for a in answers if a.marks_awarded is not None)
    submission.status = SubmissionStatus.EVALUATED
    submission.evaluated_at = datetime.now(timezone.utc)

    if not was_evaluated:
        db.flush()
        mastery_service.apply_updates_for_submission(db, submission)


def _user_can_grade_submission(db: Session, user: User, submission: Submission) -> bool:
    assessment = db.get(Assessment, submission.assessment_id)
    if assessment is None:
        return False
    return _user_can_grade_submission_section(db, user, assessment.section_id)


def _user_can_grade_submission_section(db: Session, user: User, section_id: int) -> bool:
    section = db.get(Section, section_id)
    if section is None:
        return False
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == section.school_id:
        return True
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
        return teacher is not None and section.class_teacher_id == teacher.id
    return False
