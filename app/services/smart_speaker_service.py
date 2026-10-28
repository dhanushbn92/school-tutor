"""Business logic for the smart-speaker / voice integration API.

This module is the bridge between a voice device and the existing platform. It
reuses the platform's own building blocks rather than reimplementing them:

* progress  -> ``mastery_service.build_student_grid`` (per-outcome mastery),
               rolled up here into speakable per-subject / per-chapter summaries.
* summaries -> ``GeneratedContent`` rows (CHAPTER_SUMMARY, APPROVED).
* tests     -> ``question_bank_service.sample_questions`` + a PUBLISHED
               ``Assessment`` (exactly the quick-quiz pattern in ``me.py``),
               graded turn-by-turn with ``grading.auto_grade`` for the instant
               spoken verdict, then persisted once at the end via
               ``submission_service.create_submission`` so the attempt feeds the
               real mastery / streak / points pipeline.
* know-more -> ``explain_service.get_or_generate`` (the cached DEEPER / ANALOGY
               / EXAMPLE tiers already used by the web "Tell me more" chain).

Turn-by-turn test state is stateless: the ordered question list, the cursor and
the answers gathered so far are carried in a signed session JWT (same secret /
issuer as the app's access tokens, distinguished by a ``scope`` claim) that the
device replays on each ``tests/answer`` call. No new tables, no migration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import AuthError, create_access_token, decode_token
from app.core.config import get_settings
from app.models import ExplanationTier
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    AssessmentType,
    Submission,
)
from app.models.curriculum import Book, Chapter, SchoolClass, Subject
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.question import Question, QuestionType
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    User,
    UserRole,
)
from app.schemas.smart_speaker import (
    AnswerResponse,
    ChapterListItem,
    ChapterProgress,
    ChapterSummaryResponse,
    ExplainMoreResponse,
    ProgressResponse,
    SpeakerQuestion,
    SpeakerSubject,
    StartTestResponse,
    SubjectListResponse,
    SubjectProgress,
    TestResult,
)
from app.services import question_bank_service
from app.services.explain_service import ExplainError, get_or_generate
from app.services.grading import auto_grade
from app.services.question_bank_service import BankCoverageError
from app.services.submission_service import SubmissionError, create_submission


# A chapter counts as "mastered" for the speaker rollup when the learner's
# average mastery across the outcomes they've attempted clears this floor and
# they've attempted most of the chapter's outcomes. Mirrors the web app's
# _MASTERY_FLOOR / _CHAPTER_MASTERED_RATIO used in parent insights.
_MASTERY_FLOOR = 0.75
_MASTERED_RATIO = 0.8

# Only auto-gradable types get sampled into a voice test, so every spoken
# answer can be given an immediate correct/incorrect verdict.
_VOICE_TEST_TYPES = [QuestionType.MCQ, QuestionType.TRUE_FALSE, QuestionType.FILL_BLANK]

# Marks a JWT as a turn-by-turn test session rather than an access token.
_SESSION_SCOPE = "speaker_test"

logger = logging.getLogger(__name__)

_TIER_BY_KIND = {
    "example": ExplanationTier.EXAMPLE,
    "analogy": ExplanationTier.ANALOGY,
    "deeper": ExplanationTier.DEEPER,
}


class SpeakerError(Exception):
    """Domain error surfaced by the API layer as an HTTP response.

    Carries an explicit ``status_code`` and an optional ``extra`` dict of
    structured hints (available subjects, bank gaps, ...) for the device.
    """

    def __init__(self, message: str, *, status_code: int = 400, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


# --------------------------------------------------------------------------- #
# Learner / subject resolution
# --------------------------------------------------------------------------- #
def _resolve_learner(db: Session, user: User) -> tuple[Student, Section, int]:
    """Return (student, active section, class level) or raise SpeakerError."""
    if user.role not in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        raise SpeakerError(
            "This account is not a learner account, so it has no study progress.",
            status_code=403,
        )
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise SpeakerError("No learner profile is set up for this account.", status_code=400)
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrollment is None:
        raise SpeakerError("No active class enrolment was found for this learner.", status_code=400)
    section = db.get(Section, enrollment.section_id)
    if section is None:
        raise SpeakerError("Your class section is missing.", status_code=400)
    school_class = db.get(SchoolClass, section.class_id)
    if school_class is None:
        raise SpeakerError("Your class is not configured.", status_code=400)
    return student, section, school_class.level


def _subjects_for_class(db: Session, section: Section) -> list[Subject]:
    """The class's subjects, limited to the learner's school board.

    A class (e.g. class 12) is shared between boards, so without the board
    filter a NIOS learner would also be offered CBSE subjects of the same name.
    """
    stmt = select(Subject).where(Subject.class_id == section.class_id)
    school = db.get(School, section.school_id)
    if school is not None and school.board:
        stmt = stmt.where(Subject.board == school.board)
    return list(db.scalars(stmt.order_by(Subject.name)))


def _resolve_subject(db: Session, section: Section, ref: str) -> Subject:
    """Resolve a subject by numeric id or by (case-insensitive) name."""
    ref = (ref or "").strip()
    subjects = _subjects_for_class(db, section)
    if not subjects:
        raise SpeakerError("Your class has no subjects configured yet.", status_code=404)

    if ref.isdigit():
        sid = int(ref)
        for s in subjects:
            if s.id == sid:
                return s

    low = ref.lower()
    for s in subjects:
        if s.name.lower() == low:
            return s
    partial = [s for s in subjects if low and low in s.name.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise SpeakerError(
            f"I couldn't find the subject '{ref}' in your class.",
            status_code=404,
            extra={"available_subjects": [s.name for s in subjects]},
        )
    raise SpeakerError(
        f"'{ref}' matches more than one subject. Please say which one.",
        status_code=400,
        extra={"matches": [s.name for s in partial]},
    )


# --------------------------------------------------------------------------- #
# Subjects list
# --------------------------------------------------------------------------- #
def list_subjects(db: Session, user: User) -> SubjectListResponse:
    _student, section, class_level = _resolve_learner(db, user)
    subjects = _subjects_for_class(db, section)
    items = [
        SpeakerSubject(subject_id=s.id, name=s.name, board=s.board, language=s.language)
        for s in subjects
    ]
    if items:
        names = _join_and([s.name for s in items])
        spoken = f"You are studying {len(items)} subjects: {names}."
    else:
        spoken = "You don't have any subjects set up yet."
    return SubjectListResponse(class_level=class_level, subjects=items, spoken=spoken)


# --------------------------------------------------------------------------- #
# Progress
# --------------------------------------------------------------------------- #
def _chapter_status(outcomes: list[dict]) -> tuple[str, int, int | None, int, int, list[float]]:
    """Classify one chapter block from build_student_grid outcomes.

    Returns (status, percent_complete, average_score_0_100, outcomes_total,
    outcomes_attempted, attempted_mastery_values).
    """
    total = len(outcomes)
    attempted_vals = [
        o["mastery"]
        for o in outcomes
        if o.get("attempts", 0) > 0 and o.get("mastery") is not None
    ]
    n_attempted = len(attempted_vals)
    avg = sum(attempted_vals) / n_attempted if n_attempted else None
    if n_attempted == 0:
        status = "not_started"
    elif avg is not None and avg >= _MASTERY_FLOOR and total and (n_attempted / total) >= _MASTERED_RATIO:
        status = "mastered"
    else:
        status = "in_progress"
    percent = round(100 * n_attempted / total) if total else 0
    avg_score = round(100 * avg) if avg is not None else None
    return status, percent, avg_score, total, n_attempted, attempted_vals


def _summarise_subject(
    subject_id: int,
    subject_name: str,
    chapter_blocks: list[dict],
    *,
    include_chapters: bool,
) -> SubjectProgress:
    mastered = in_progress = not_started = 0
    outcomes_total = outcomes_attempted = 0
    mastery_vals: list[float] = []
    ch_list: list[ChapterProgress] = []

    for cb in chapter_blocks:
        status, percent, avg_score, total, n_att, vals = _chapter_status(cb.get("outcomes", []))
        outcomes_total += total
        outcomes_attempted += n_att
        mastery_vals.extend(vals)
        if status == "mastered":
            mastered += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            not_started += 1
        if include_chapters:
            ch_list.append(
                ChapterProgress(
                    chapter_id=cb["chapter_id"],
                    chapter_number=cb["chapter_number"],
                    title=cb["chapter_title"],
                    status=status,
                    percent_complete=percent,
                    average_score=avg_score,
                )
            )

    overall_avg = round(100 * sum(mastery_vals) / len(mastery_vals)) if mastery_vals else None
    chapters_total = len(chapter_blocks)
    spoken = _subject_spoken(
        subject_name, chapters_total, mastered, in_progress, not_started, overall_avg
    )
    return SubjectProgress(
        subject_id=subject_id,
        subject=subject_name,
        chapters_total=chapters_total,
        chapters_mastered=mastered,
        chapters_in_progress=in_progress,
        chapters_not_started=not_started,
        outcomes_total=outcomes_total,
        outcomes_attempted=outcomes_attempted,
        average_score=overall_avg,
        chapters=ch_list,
        spoken=spoken,
    )


def all_progress(db: Session, user: User) -> ProgressResponse:
    from app.services import mastery_service

    student, _section, class_level = _resolve_learner(db, user)
    grid = mastery_service.build_student_grid(
        db, student_id=student.id, class_level=class_level, subject_id=None
    )
    # Group the whole-class chapter blocks back into their subjects.
    by_subject: dict[int, tuple[str, list[dict]]] = {}
    for cb in grid.get("chapters", []):
        sid = cb.get("subject_id")
        name = cb.get("subject_name") or "Subject"
        by_subject.setdefault(sid, (name, []))[1].append(cb)

    subjects = [
        _summarise_subject(sid, name, blocks, include_chapters=False)
        for sid, (name, blocks) in sorted(by_subject.items(), key=lambda kv: kv[1][0].lower())
    ]

    if not subjects:
        spoken = "I don't have any progress to report yet."
    else:
        bits = []
        for sp in subjects:
            if sp.average_score is None:
                bits.append(f"{sp.subject}: not started")
            else:
                bits.append(
                    f"{sp.subject}: {sp.chapters_mastered} of {sp.chapters_total} chapters mastered"
                )
        spoken = "Here is your progress. " + ". ".join(bits) + ". Ask about a subject for more detail."
    return ProgressResponse(class_level=class_level, subjects=subjects, spoken=spoken)


def subject_progress(db: Session, user: User, subject_ref: str) -> SubjectProgress:
    from app.services import mastery_service

    student, section, class_level = _resolve_learner(db, user)
    subject = _resolve_subject(db, section, subject_ref)
    grid = mastery_service.build_student_grid(
        db, student_id=student.id, class_level=class_level, subject_id=subject.id
    )
    return _summarise_subject(
        subject.id, subject.name, grid.get("chapters", []), include_chapters=True
    )


# --------------------------------------------------------------------------- #
# Chapter summaries
# --------------------------------------------------------------------------- #
def _subject_chapters(db: Session, subject: Subject) -> list[Chapter]:
    return list(
        db.scalars(
            select(Chapter)
            .join(Book, Chapter.book_id == Book.id)
            .where(Book.subject_id == subject.id)
            .order_by(Chapter.chapter_number)
        )
    )


def _approved_summary(db: Session, chapter_id: int) -> GeneratedContent | None:
    return db.scalar(
        select(GeneratedContent)
        .where(
            GeneratedContent.chapter_id == chapter_id,
            GeneratedContent.content_type == GeneratedContentType.CHAPTER_SUMMARY,
            GeneratedContent.status == GeneratedContentStatus.APPROVED,
        )
        .order_by(GeneratedContent.id.desc())
    )


def chapter_summary(
    db: Session,
    user: User,
    *,
    subject_ref: str,
    chapter_id: int | None = None,
    chapter_number: int | None = None,
) -> ChapterSummaryResponse:
    _student, section, _class_level = _resolve_learner(db, user)
    subject = _resolve_subject(db, section, subject_ref)
    chapters = _subject_chapters(db, subject)
    if not chapters:
        raise SpeakerError(f"{subject.name} has no chapters yet.", status_code=404)

    target: Chapter | None = None
    if chapter_id is not None:
        target = next((c for c in chapters if c.id == chapter_id), None)
        if target is None:
            raise SpeakerError("That chapter is not part of this subject.", status_code=404)
    elif chapter_number is not None:
        target = next((c for c in chapters if c.chapter_number == chapter_number), None)
        if target is None:
            raise SpeakerError(
                f"{subject.name} has no chapter number {chapter_number}.", status_code=404
            )

    if target is None:
        # No chapter chosen — offer the list so the speaker can ask which one.
        ids = [c.id for c in chapters]
        with_summary = set(
            db.scalars(
                select(GeneratedContent.chapter_id).where(
                    GeneratedContent.chapter_id.in_(ids),
                    GeneratedContent.content_type == GeneratedContentType.CHAPTER_SUMMARY,
                    GeneratedContent.status == GeneratedContentStatus.APPROVED,
                )
            )
        )
        items = [
            ChapterListItem(
                chapter_id=c.id,
                chapter_number=c.chapter_number,
                title=c.title,
                has_summary=c.id in with_summary,
            )
            for c in chapters
        ]
        spoken = (
            f"{subject.name} has {len(items)} chapters. "
            "Which chapter would you like a summary of? For example, say 'chapter 1'."
        )
        return ChapterSummaryResponse(
            subject_id=subject.id, subject=subject.name, chapters=items, spoken=spoken
        )

    gc = _approved_summary(db, target.id)
    if gc is None:
        raise SpeakerError(
            f"There's no summary available yet for chapter {target.chapter_number}, {target.title}.",
            status_code=404,
        )

    summary_text, key_points = _summary_payload(gc)
    spoken_parts = [f"Summary of chapter {target.chapter_number}, {target.title}."]
    if summary_text:
        spoken_parts.append(summary_text)
    if key_points:
        spoken_parts.append("Key points: " + _numbered(key_points))
    spoken = " ".join(spoken_parts)
    return ChapterSummaryResponse(
        subject_id=subject.id,
        subject=subject.name,
        chapter_id=target.id,
        chapter_number=target.chapter_number,
        title=target.title,
        summary_text=summary_text,
        key_points=key_points,
        spoken=spoken,
    )


def _summary_payload(gc: GeneratedContent) -> tuple[str | None, list[str]]:
    """Pull speakable text + key points out of a CHAPTER_SUMMARY row."""
    data = gc.output_json or {}
    intro = (data.get("intro") or "").strip() or None
    takeaways = [str(t).strip() for t in (data.get("key_takeaways") or []) if str(t).strip()]

    if intro is None:
        # Fall back to the first section's bullets, then to output_text.
        sections = data.get("sections") or []
        if sections:
            first = sections[0]
            bullets = [str(b).strip() for b in (first.get("bullets") or []) if str(b).strip()]
            if bullets:
                intro = " ".join(bullets)
        if intro is None and gc.output_text:
            intro = gc.output_text.strip() or None
    return intro, takeaways


# --------------------------------------------------------------------------- #
# Turn-by-turn tests
# --------------------------------------------------------------------------- #
def start_test(
    db: Session,
    user: User,
    *,
    subject_ref: str,
    chapter_id: int | None,
    chapter_number: int | None,
    question_count: int,
) -> StartTestResponse:
    student, section, _class_level = _resolve_learner(db, user)
    subject = _resolve_subject(db, section, subject_ref)

    chapter: Chapter | None = None
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None or db.get(Book, chapter.book_id) is None:
            raise SpeakerError("That chapter was not found.", status_code=404)
        book = db.get(Book, chapter.book_id)
        if book.subject_id != subject.id:
            raise SpeakerError("That chapter is not part of this subject.", status_code=400)
    elif chapter_number is not None:
        chapter = next(
            (c for c in _subject_chapters(db, subject) if c.chapter_number == chapter_number),
            None,
        )
        if chapter is None:
            raise SpeakerError(
                f"{subject.name} has no chapter number {chapter_number}.", status_code=404
            )
    else:
        raise SpeakerError(
            "Please say which chapter to test on, for example 'chapter 1'.", status_code=400
        )

    try:
        sampled = question_bank_service.sample_questions(
            db,
            chapter_id=chapter.id,
            count=question_count,
            allowed_types=_VOICE_TEST_TYPES,
        )
    except BankCoverageError as exc:
        raise SpeakerError(
            "There aren't enough practice questions for that chapter yet.",
            status_code=409,
            extra={"gaps": exc.gaps},
        ) from exc
    except ValueError as exc:
        raise SpeakerError(str(exc), status_code=400) from exc

    if not sampled:
        raise SpeakerError("No questions are available for that chapter yet.", status_code=409)

    now = datetime.now(timezone.utc)
    total_marks = sum(q.marks for q in sampled)
    assessment = Assessment(
        section_id=section.id,
        subject_id=subject.id,
        chapter_id=chapter.id,
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        title=f"Voice quiz · Ch {chapter.chapter_number} {chapter.title}",
        instructions="Voice practice quiz.",
        total_marks=total_marks,
        published_at=now,
        created_by_id=user.id,
    )
    for order, q in enumerate(sampled, start=1):
        assessment.questions.append(
            AssessmentQuestion(question_id=q.id, order=order, marks_override=None)
        )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    qids = [q.id for q in sampled]
    token = _encode_session(user, assessment_id=assessment.id, qids=qids, cursor=0, answers={})
    first = _speaker_question(sampled[0], number=1, total=len(qids))
    spoken = (
        f"Starting a {len(qids)}-question quiz on {subject.name}, "
        f"chapter {chapter.chapter_number}, {chapter.title}. {first.spoken}"
    )
    return StartTestResponse(
        session_token=token,
        assessment_id=assessment.id,
        subject=subject.name,
        chapter_title=chapter.title,
        total_questions=len(qids),
        question=first,
        spoken=spoken,
    )


def answer(db: Session, user: User, *, session_token: str, answer_text: str) -> AnswerResponse:
    claims = _decode_session(user, session_token)
    tid = int(claims["tid"])
    qids: list[int] = [int(q) for q in claims.get("qs", [])]
    cursor = int(claims.get("cur", 0))
    answers: dict[str, str] = dict(claims.get("ans", {}))

    if cursor >= len(qids):
        raise SpeakerError("This test is already finished. Start a new one to continue.", status_code=409)

    # The session lives in a replayable token, so the server remembers the one
    # fact that matters: a completed test (a stored submission) cannot be
    # replayed to re-score or to farm points.
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is not None and db.scalar(
        select(Submission.id).where(
            Submission.assessment_id == tid, Submission.student_id == student.id
        )
    ):
        raise SpeakerError("This test is already finished. Start a new one to continue.", status_code=409)

    current_id = qids[cursor]
    question = db.get(Question, current_id)
    if question is None:  # pragma: no cover — question retired mid-session
        raise SpeakerError("That question is no longer available.", status_code=410)

    spoken_answer = (answer_text or "").strip()
    graded_answer = _coerce_choice_answer(question, spoken_answer)
    awarded, _auto, _ = auto_grade(question, graded_answer, question.marks)
    # Only auto-gradable question types are ever sampled into a voice test.
    is_correct = (awarded or 0) > 0
    verdict = "correct" if is_correct else "incorrect"

    answers[str(current_id)] = spoken_answer
    new_cursor = cursor + 1
    finished = new_cursor >= len(qids)

    # Compose the spoken verdict for this question.
    if is_correct:
        verdict_spoken = "Correct!"
    else:
        verdict_spoken = f"Not quite. The correct answer is {question.correct_answer}."
    if question.explanation:
        verdict_spoken += f" {question.explanation.strip()}"
    if not is_correct:
        verdict_spoken += " Say 'tell me more' for another example."

    next_question: SpeakerQuestion | None = None
    result: TestResult | None = None
    new_token = _encode_session(user, assessment_id=tid, qids=qids, cursor=new_cursor, answers=answers)

    if finished:
        result = _finalise(db, user, assessment_id=tid, qids=qids, answers=answers)
        spoken = (
            f"{verdict_spoken} That was the last question. You scored "
            f"{result.score} out of {result.max_score}, {result.correct_count} correct "
            f"out of {result.total_questions}. Well done!"
        )
    else:
        nxt = db.get(Question, qids[new_cursor])
        next_question = _speaker_question(nxt, number=new_cursor + 1, total=len(qids))
        spoken = f"{verdict_spoken} {next_question.spoken}"

    return AnswerResponse(
        question_number=cursor + 1,
        question_id=current_id,
        is_correct=is_correct,
        verdict=verdict,
        your_answer=spoken_answer,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        can_explain_more=True,
        finished=finished,
        next_question=next_question,
        result=result,
        session_token=new_token,
        spoken=spoken,
    )


def _finalise(
    db: Session, user: User, *, assessment_id: int, qids: list[int], answers: dict[str, str]
) -> TestResult:
    """Persist the completed attempt (best-effort) and compute the result.

    The score is computed locally from the collected answers so a failure to
    persist (e.g. a transient DB issue) still lets the device report a result.
    Persistence feeds the real mastery / streak / points pipeline.
    """
    score = 0
    max_score = 0
    correct = 0
    for qid in qids:
        q = db.get(Question, qid)
        if q is None:
            continue
        raw = answers.get(str(qid))
        graded = _coerce_choice_answer(q, raw)
        awarded, auto, _ = auto_grade(q, graded, q.marks)
        max_score += q.marks
        if auto:
            score += awarded or 0
            if (awarded or 0) > 0:
                correct += 1

    try:
        create_submission(
            db,
            user=user,
            assessment_id=assessment_id,
            answers={int(k): _coerce_choice_answer(db.get(Question, int(k)), v) for k, v in answers.items()},
        )
    except SubmissionError:
        # The spoken result is still valid; only the progress write was skipped.
        db.rollback()
    except Exception:  # noqa: BLE001 - best-effort: never lose the spoken result
        logger.exception("Could not persist the voice quiz attempt for assessment %s", assessment_id)
        db.rollback()

    percent = round(100 * score / max_score) if max_score else 0
    return TestResult(
        score=score,
        max_score=max_score,
        correct_count=correct,
        total_questions=len(qids),
        percent=percent,
    )


# --------------------------------------------------------------------------- #
# Know more / more examples
# --------------------------------------------------------------------------- #
def explain_more(
    db: Session,
    user: User,
    *,
    session_token: str | None,
    question_id: int | None,
    kind: str,
) -> ExplainMoreResponse:
    tier = _TIER_BY_KIND.get((kind or "").lower())
    if tier is None:
        raise SpeakerError(
            "Say 'example', 'analogy', or 'deeper' to hear more.", status_code=400
        )

    qid = question_id
    if session_token:
        claims = _decode_session(user, session_token)
        qids = [int(q) for q in claims.get("qs", [])]
        cursor = int(claims.get("cur", 0))
        if cursor < 1:
            raise SpeakerError(
                "Answer a question first, then I can tell you more about it.", status_code=400
            )
        # The just-answered question is one before the cursor.
        if qids:
            qid = qids[min(cursor - 1, len(qids) - 1)]
    if qid is None:
        raise SpeakerError(
            "I don't know which question you mean. Provide a session or a question id.",
            status_code=400,
        )

    try:
        row = get_or_generate(db, question_id=qid, tier=tier, user=user)
    except ExplainError as exc:
        raise SpeakerError(str(exc), status_code=503) from exc

    text = (row.text or "").strip()
    return ExplainMoreResponse(question_id=qid, kind=tier.value, text=text, spoken=text)


# --------------------------------------------------------------------------- #
# Session token (stateless test state)
# --------------------------------------------------------------------------- #
def _encode_session(
    user: User, *, assessment_id: int, qids: list[int], cursor: int, answers: dict[str, str]
) -> str:
    settings = get_settings()
    return create_access_token(
        subject=user.id,
        role=user.role.value,
        school_id=user.school_id,
        extra_claims={
            "scope": _SESSION_SCOPE,
            "tid": assessment_id,
            "qs": qids,
            "cur": cursor,
            "ans": answers,
        },
        ttl_minutes=settings.smart_speaker_session_ttl_minutes,
    )


def _decode_session(user: User, token: str) -> dict:
    try:
        claims = decode_token(token)
    except AuthError as exc:
        raise SpeakerError(
            "Your test session has expired. Please start a new test.", status_code=401
        ) from exc
    if claims.get("scope") != _SESSION_SCOPE:
        raise SpeakerError("That is not a valid test session.", status_code=400)
    if str(claims.get("sub")) != str(user.id):
        raise SpeakerError("This test session belongs to a different user.", status_code=403)
    return claims


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _speaker_question(q: Question, *, number: int, total: int) -> SpeakerQuestion:
    options: list[str] | None = None
    options_spoken: list[str] | None = None
    has_options = False
    letters = "ABCDEFGH"

    if q.type == QuestionType.MCQ:
        choices = [str(c) for c in ((q.options or {}).get("choices") or [])]
        if choices:
            has_options = True
            options = choices
            options_spoken = [f"{letters[i]}. {c}" for i, c in enumerate(choices) if i < len(letters)]
        hint = "Say the letter or the full option."
    elif q.type == QuestionType.TRUE_FALSE:
        has_options = True
        options = ["True", "False"]
        options_spoken = ["A. True", "B. False"]
        hint = "Say True or False."
    elif q.type == QuestionType.FILL_BLANK:
        hint = "Say the word or phrase that fills the blank."
    else:
        hint = "Say your answer."

    parts = [f"Question {number} of {total}.", q.text.strip()]
    if options_spoken:
        parts.append("Your options are: " + "; ".join(options_spoken) + ".")
    parts.append(hint)
    return SpeakerQuestion(
        question_number=number,
        total_questions=total,
        question_id=q.id,
        question_type=q.type.value,
        text=q.text.strip(),
        has_options=has_options,
        options=options,
        options_spoken=options_spoken,
        answer_hint=hint,
        spoken=" ".join(parts),
    )


def _coerce_choice_answer(q: Question | None, answer_text: str | None) -> str | None:
    """Map a spoken option letter ("B") to the option's text for grading.

    Grading compares against the stored option string, so a bare letter must be
    translated first. This covers MCQ and True/False (read out as "A. True;
    B. False"). A spoken full option is left untouched (it already matches), as
    is every other answer.
    """
    if q is None or q.type not in (QuestionType.MCQ, QuestionType.TRUE_FALSE) or not answer_text:
        return answer_text
    if q.type == QuestionType.TRUE_FALSE:
        choices = ["True", "False"]
    else:
        choices = [str(c) for c in ((q.options or {}).get("choices") or [])]
    if not choices:
        return answer_text
    token = answer_text.strip().lower().lstrip("(").rstrip(").").strip()
    letters = "abcdefgh"
    if len(token) == 1 and token in letters:
        idx = letters.index(token)
        if idx < len(choices):
            return choices[idx]
    return answer_text


def _numbered(items: list[str]) -> str:
    return " ".join(f"{i}. {t}" for i, t in enumerate(items, start=1))


def _join_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _subject_spoken(
    subject: str,
    chapters_total: int,
    mastered: int,
    in_progress: int,
    not_started: int,
    average_score: int | None,
) -> str:
    if average_score is None:
        return (
            f"In {subject}, you haven't practised any questions yet, "
            f"so there's no score to report. There are {chapters_total} chapters to explore."
        )
    return (
        f"In {subject}, you have mastered {mastered} of {chapters_total} chapters, "
        f"are practising {in_progress}, and have {not_started} still to start. "
        f"Your average score across what you've practised is {average_score} percent."
    )
