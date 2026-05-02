from typing import Literal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.curriculum import BloomLevel, Book, Chapter, LearningOutcome, SchoolClass, Subject
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType


# `kind` is a coarse rollup of QuestionType for the question-bank filter UI.
# Objective types are auto-gradable (single right answer); subjective types
# require a rubric / LLM grading.
QuestionKind = Literal["objective", "subjective"]
_OBJECTIVE_TYPES: set[QuestionType] = {
    QuestionType.MCQ,
    QuestionType.TRUE_FALSE,
    QuestionType.FILL_BLANK,
}
_SUBJECTIVE_TYPES: set[QuestionType] = {
    QuestionType.SHORT_ANSWER,
    QuestionType.LONG_ANSWER,
    QuestionType.CASE_BASED,
}


def types_for_kind(kind: QuestionKind | None) -> list[QuestionType] | None:
    """Translate a coarse kind label into the underlying QuestionType set."""
    if kind == "objective":
        return list(_OBJECTIVE_TYPES)
    if kind == "subjective":
        return list(_SUBJECTIVE_TYPES)
    return None


def list_questions(
    db: Session,
    *,
    class_level: int | None = None,
    subject_id: int | None = None,
    board: str | None = None,
    chapter_id: int | None = None,
    topic_id: int | None = None,
    outcome_id: int | None = None,
    outcome_code: str | None = None,
    type_: QuestionType | None = None,
    kind: QuestionKind | None = None,
    difficulty: QuestionDifficulty | None = None,
    cognitive_level: BloomLevel | None = None,
    status: QuestionStatus | None = None,
    source_generated_content_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Question]:
    """Browse the question bank.

    `class_level` / `subject_id` / `board` / `kind` are coarse filters meant
    for the platform-team curation UI. They join through
    Chapter -> Book -> Subject -> SchoolClass and translate to the underlying
    type set respectively. `board` is matched case-insensitively on
    `Subject.board` (e.g. "CBSE", "NIOS").
    """
    stmt: Select[tuple[Question]] = select(Question).order_by(Question.id.desc())

    needs_curriculum_join = (
        class_level is not None or subject_id is not None or board is not None
    )
    if needs_curriculum_join:
        # Join through the curriculum chain so we can scope on
        # class / subject / board.
        stmt = (
            stmt.join(Chapter, Chapter.id == Question.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .join(Subject, Subject.id == Book.subject_id)
        )
        if class_level is not None:
            stmt = stmt.join(SchoolClass, SchoolClass.id == Subject.class_id).where(
                SchoolClass.level == class_level
            )
        if subject_id is not None:
            stmt = stmt.where(Subject.id == subject_id)
        if board is not None:
            # Case-insensitive: clients commonly pass "nios" or "NIOS".
            stmt = stmt.where(Subject.board.ilike(board))

    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if outcome_id is not None:
        stmt = stmt.where(Question.outcome_id == outcome_id)
    if outcome_code is not None:
        stmt = stmt.where(Question.outcome_code == outcome_code)
    if type_ is not None:
        stmt = stmt.where(Question.type == type_)
    elif kind is not None:
        # `kind` is a softer filter than `type_`; if both are passed,
        # the explicit type wins.
        kind_types = types_for_kind(kind)
        if kind_types:
            stmt = stmt.where(Question.type.in_(kind_types))
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    if cognitive_level is not None:
        stmt = stmt.where(Question.cognitive_level == cognitive_level)
    if status is not None:
        stmt = stmt.where(Question.status == status)
    if source_generated_content_id is not None:
        stmt = stmt.where(Question.source_generated_content_id == source_generated_content_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def update_question(db: Session, question: Question, patch: dict) -> Question:
    """Apply a partial update to a Question. Caller commits."""
    for field, value in patch.items():
        if value is None:
            continue
        setattr(question, field, value)

    if "outcome_id" in patch and patch["outcome_id"] is not None:
        outcome = db.get(LearningOutcome, patch["outcome_id"])
        if outcome is not None and outcome.chapter_id != question.chapter_id:
            raise ValueError(
                "outcome_id belongs to a different chapter than the question"
            )
        if outcome is not None:
            question.outcome_code = outcome.code

    return question


def approve_question(db: Session, question: Question, *, reviewer_id: int, notes: str | None) -> Question:
    question.status = QuestionStatus.APPROVED
    question.reviewed_by_id = reviewer_id
    if notes is not None:
        question.review_notes = notes
    return question


def reject_question(db: Session, question: Question, *, reviewer_id: int, notes: str | None) -> Question:
    question.status = QuestionStatus.REJECTED
    question.reviewed_by_id = reviewer_id
    if notes is not None:
        question.review_notes = notes
    return question
