from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.curriculum import Book, Chapter, LearningOutcome, SchoolClass, Subject, Topic


def list_classes(db: Session) -> list[SchoolClass]:
    return list(db.scalars(select(SchoolClass).order_by(SchoolClass.level)))


def list_subjects(
    db: Session,
    class_level: int | None = None,
    board: str | None = None,
) -> list[Subject]:
    """List subjects, optionally narrowed by class level and/or board.

    The route uses `board` to scope CBSE schools to CBSE subjects, NIOS
    schools to NIOS subjects, etc. Platform admins pass no board (or a
    specific one) to browse across the whole catalogue.
    """
    stmt: Select[tuple[Subject]] = select(Subject).join(SchoolClass).order_by(SchoolClass.level, Subject.name)
    if class_level is not None:
        stmt = stmt.where(SchoolClass.level == class_level)
    if board is not None:
        stmt = stmt.where(Subject.board == board)
    return list(db.scalars(stmt))


def list_books(db: Session, subject_id: int, academic_year: str | None = None) -> list[Book]:
    stmt = select(Book).where(Book.subject_id == subject_id).order_by(Book.title)
    if academic_year:
        stmt = stmt.where(Book.academic_year == academic_year)
    return list(db.scalars(stmt))


def list_chapters(
    db: Session,
    *,
    class_level: int | None = None,
    subject_id: int | None = None,
    book_id: int | None = None,
    academic_year: str | None = None,
) -> list[Chapter]:
    stmt = select(Chapter).join(Book).join(Subject).join(SchoolClass).order_by(
        SchoolClass.level, Subject.name, Book.title, Chapter.chapter_number
    )
    if class_level is not None:
        stmt = stmt.where(SchoolClass.level == class_level)
    if subject_id is not None:
        stmt = stmt.where(Subject.id == subject_id)
    if book_id is not None:
        stmt = stmt.where(Book.id == book_id)
    if academic_year:
        stmt = stmt.where(Book.academic_year == academic_year)
    return list(db.scalars(stmt))


def get_chapter_detail(db: Session, chapter_id: int) -> Chapter | None:
    # Book → Subject is eager-loaded so the route can hand the subject's
    # id and name back as part of `ChapterDetailRead`. The Learn page uses
    # this to colour-theme the chapter hero by subject family.
    return db.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(
            selectinload(Chapter.sections),
            selectinload(Chapter.topics),
            joinedload(Chapter.book).joinedload(Book.subject),
        )
    )


def build_curriculum_context(db: Session, chapter_id: int, topic_id: int | None = None) -> dict | None:
    """Assemble the full context blob used for any content-generation request.

    Returns chapter full text plus all learning outcomes and topics for the chapter.
    When `topic_id` is supplied, the response narrows `outcomes` to that topic and
    records `topic.name` as the focus; `context_text` still returns the full chapter
    (the LLM is better at scoping internally than line-grep filtering was).

    All downstream generators (worksheet, quiz, lesson plan, ...) read from this one
    function. When RAG is introduced post-MVP, replace the body here; callers do not
    change.
    """
    chapter = db.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(
            joinedload(Chapter.book).joinedload(Book.subject).joinedload(Subject.school_class),
            selectinload(Chapter.topics),
            selectinload(Chapter.learning_outcomes),
        )
    )
    if chapter is None:
        return None

    focus_topic: Topic | None = None
    if topic_id is not None:
        focus_topic = next((t for t in chapter.topics if t.id == topic_id), None)

    outcomes = sorted(chapter.learning_outcomes, key=lambda lo: lo.code)
    if focus_topic is not None:
        scoped = [lo for lo in outcomes if lo.topic_id == focus_topic.id]
        if scoped:
            outcomes = scoped

    subject = chapter.book.subject
    return {
        "academic_year": chapter.book.academic_year,
        "class_level": subject.school_class.level,
        "subject": subject.name,
        "book": chapter.book.title,
        "chapter_id": chapter.id,
        "chapter_number": chapter.chapter_number,
        "chapter_title": chapter.title,
        "chapter_text": chapter.full_text,
        "context_text": chapter.full_text,
        "topic": focus_topic.name if focus_topic else None,
        "topics": [t.name for t in chapter.topics],
        "outcomes": [
            {
                "code": lo.code,
                "description": lo.description,
                "bloom_level": lo.bloom_level.value,
                "topic_id": lo.topic_id,
            }
            for lo in outcomes
        ],
        "source_url": chapter.source_url,
    }
