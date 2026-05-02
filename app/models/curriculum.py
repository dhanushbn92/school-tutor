from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BloomLevel(StrEnum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    is_current: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolClass(Base):
    __tablename__ = "school_classes"
    __table_args__ = (UniqueConstraint("level", name="uq_school_classes_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[int] = mapped_column(Integer, index=True)
    display_name: Mapped[str] = mapped_column(String(40))

    subjects: Mapped[list["Subject"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"
    # board is part of the uniqueness key so CBSE Mathematics and NIOS
    # Mathematics can coexist in the same Class 10. See migration
    # 20260430_0022 for the schema change.
    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "name",
            "language",
            "board",
            name="uq_subjects_class_name_lang_board",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    language: Mapped[str] = mapped_column(String(20), default="en")
    # Syllabus board the subject belongs to. Defaults to "CBSE" because
    # that's the only board the platform supported until this column was
    # introduced. Validated at the API layer against `app.constants.boards.VALID_BOARDS`.
    board: Mapped[str] = mapped_column(
        String(20), default="CBSE", server_default="CBSE", nullable=False, index=True
    )

    school_class: Mapped[SchoolClass] = relationship(back_populates="subjects")
    books: Mapped[list["Book"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (UniqueConstraint("subject_id", "ncert_code", "academic_year", name="uq_books_subject_code_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    ncert_code: Mapped[str] = mapped_column(String(20), index=True)
    academic_year: Mapped[str] = mapped_column(String(20), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)

    subject: Mapped[Subject] = relationship(back_populates="books")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "chapter_number", name="uq_chapters_book_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    full_text: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    book: Mapped[Book] = relationship(back_populates="chapters")
    sections: Mapped[list["ChapterSection"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")
    topics: Mapped[list["Topic"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")
    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class ChapterSection(Base):
    __tablename__ = "chapter_sections"
    __table_args__ = (UniqueConstraint("chapter_id", "section_number", name="uq_chapter_sections_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    section_number: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300))
    section_text: Mapped[str] = mapped_column(Text, default="")
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)

    chapter: Mapped[Chapter] = relationship(back_populates="sections")


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("chapter_id", "name", name="uq_topics_chapter_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Topic-specific slice of the chapter text, extracted by LLM. Used as the
    # context for topic-scoped AI tutor sessions so we don't have to send the
    # whole chapter when the student wants to focus on one topic.
    full_text: Mapped[str | None] = mapped_column(Text)

    chapter: Mapped[Chapter] = relationship(back_populates="topics")
    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"
    __table_args__ = (UniqueConstraint("chapter_id", "code", name="uq_learning_outcomes_chapter_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[BloomLevel] = mapped_column(Enum(BloomLevel), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="learning_outcomes")
    topic: Mapped[Topic | None] = relationship(back_populates="learning_outcomes")

