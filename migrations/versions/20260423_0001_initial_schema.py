"""initial schema

Revision ID: 20260423_0001
Revises: None
Create Date: 2026-04-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260423_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


content_type_enum = sa.Enum(
    "WORKSHEET",
    "QUIZ",
    "HALF_YEARLY_EXAM",
    "PPT",
    "DIAGRAM",
    "SIMULATION",
    "LESSON_PLAN",
    name="generatedcontenttype",
)
status_enum = sa.Enum("PENDING", "READY", "FAILED", name="generatedcontentstatus")


def upgrade() -> None:
    op.create_table(
        "academic_years",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_academic_years_name"), "academic_years", ["name"], unique=True)

    op.create_table(
        "school_classes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level", name="uq_school_classes_level"),
    )
    op.create_index(op.f("ix_school_classes_level"), "school_classes", ["level"], unique=False)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "name", "language", name="uq_subjects_class_name_language"),
    )
    op.create_index(op.f("ix_subjects_class_id"), "subjects", ["class_id"], unique=False)
    op.create_index(op.f("ix_subjects_name"), "subjects", ["name"], unique=False)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("ncert_code", sa.String(length=20), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "ncert_code", "academic_year", name="uq_books_subject_code_year"),
    )
    op.create_index(op.f("ix_books_academic_year"), "books", ["academic_year"], unique=False)
    op.create_index(op.f("ix_books_ncert_code"), "books", ["ncert_code"], unique=False)
    op.create_index(op.f("ix_books_subject_id"), "books", ["subject_id"], unique=False)
    op.create_index(op.f("ix_books_title"), "books", ["title"], unique=False)

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "chapter_number", name="uq_chapters_book_number"),
    )
    op.create_index(op.f("ix_chapters_book_id"), "chapters", ["book_id"], unique=False)
    op.create_index(op.f("ix_chapters_chapter_number"), "chapters", ["chapter_number"], unique=False)
    op.create_index(op.f("ix_chapters_content_hash"), "chapters", ["content_hash"], unique=False)
    op.create_index(op.f("ix_chapters_title"), "chapters", ["title"], unique=False)

    op.create_table(
        "chapter_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("section_text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "section_number", name="uq_chapter_sections_number"),
    )
    op.create_index(op.f("ix_chapter_sections_chapter_id"), "chapter_sections", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_chapter_sections_section_number"), "chapter_sections", ["section_number"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "name", name="uq_topics_chapter_name"),
    )
    op.create_index(op.f("ix_topics_chapter_id"), "topics", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_topics_name"), "topics", ["name"], unique=False)

    op.create_table(
        "generated_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_type", content_type_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("cache_key", sa.String(length=128), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("class_level", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("source_context", sa.Text(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("artifact_url", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("request_options", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key", name="uq_generated_contents_cache_key"),
    )
    op.create_index(op.f("ix_generated_contents_academic_year"), "generated_contents", ["academic_year"], unique=False)
    op.create_index(op.f("ix_generated_contents_cache_key"), "generated_contents", ["cache_key"], unique=False)
    op.create_index(op.f("ix_generated_contents_chapter_id"), "generated_contents", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_generated_contents_class_level"), "generated_contents", ["class_level"], unique=False)
    op.create_index(op.f("ix_generated_contents_content_type"), "generated_contents", ["content_type"], unique=False)
    op.create_index(op.f("ix_generated_contents_status"), "generated_contents", ["status"], unique=False)
    op.create_index(op.f("ix_generated_contents_subject_id"), "generated_contents", ["subject_id"], unique=False)
    op.create_index(op.f("ix_generated_contents_topic_id"), "generated_contents", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_table("generated_contents")
    op.drop_table("topics")
    op.drop_table("chapter_sections")
    op.drop_table("chapters")
    op.drop_table("books")
    op.drop_table("subjects")
    op.drop_table("school_classes")
    op.drop_table("academic_years")
    status_enum.drop(op.get_bind(), checkfirst=True)
    content_type_enum.drop(op.get_bind(), checkfirst=True)
