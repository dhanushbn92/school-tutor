"""Video lectures for a chapter (read-only).

Learners and teachers only ever see published rows; the list is ordered by
play sequence so the chapter's "The Lesson" comes before its word-by-word parts.

Both endpoints are scoped the same way the curriculum is: learners see their own
class and board, staff see their school's board, and the platform team sees
everything.

`GET /chapter-videos/featured` summarises which chapters have videos so the
dashboard can promote them.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, is_platform_admin
from app.db.session import get_db
from app.models.chapter_video import ChapterVideo
from app.models.curriculum import Book, Chapter, Subject
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    User,
    UserRole,
)
from app.schemas.chapter_video import (
    ChapterVideoRead,
    FeaturedChapterRead,
    FeaturedVideosRead,
)

router = APIRouter(prefix="/chapter-videos", tags=["chapter-videos"])


def _scope_to_user(db: Session, user: User, stmt: Select) -> Select | None:
    """Limit a ChapterVideo -> Chapter -> Book -> Subject query to what this user may see.

    Returns None when the user can see nothing (no school, or a learner with no
    active class), so callers can short-circuit to an empty result.
    """
    if is_platform_admin(user):
        return stmt

    # Same rule as the curriculum: stay inside the user's school board.
    school = db.get(School, user.school_id) if user.school_id else None
    if school is None:
        return None
    stmt = stmt.where(Subject.board == school.board)

    if user.role in (UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER):
        # Learners additionally see only their own class.
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        section = (
            db.scalar(
                select(Section)
                .join(Enrollment, Enrollment.section_id == Section.id)
                .where(
                    Enrollment.student_id == student.id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
            if student is not None
            else None
        )
        if section is None:
            return None
        stmt = stmt.where(Subject.class_id == section.class_id)
    return stmt


@router.get("", response_model=list[ChapterVideoRead])
def list_chapter_videos(
    chapter_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ChapterVideo)
        .join(Chapter, ChapterVideo.chapter_id == Chapter.id)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .where(ChapterVideo.chapter_id == chapter_id, ChapterVideo.is_published.is_(True))
        .order_by(ChapterVideo.sequence)
    )
    stmt = _scope_to_user(db, user, stmt)
    if stmt is None:
        return []
    return list(db.scalars(stmt))


@router.get("/featured", response_model=FeaturedVideosRead)
def featured_videos(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Chapters that have video lectures, for the dashboard promo."""
    stmt = (
        select(
            Chapter.id,
            Chapter.chapter_number,
            Chapter.title,
            Subject.id,
            Subject.name,
            func.count(ChapterVideo.id),
        )
        .join(ChapterVideo, ChapterVideo.chapter_id == Chapter.id)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .where(ChapterVideo.is_published.is_(True))
        .group_by(Chapter.id, Chapter.chapter_number, Chapter.title, Subject.id, Subject.name)
        .order_by(Subject.name, Chapter.chapter_number)
    )
    stmt = _scope_to_user(db, user, stmt)
    if stmt is None:
        return FeaturedVideosRead(total_videos=0, total_chapters=0, chapters=[])

    rows = db.execute(stmt).all()
    chapters = [
        FeaturedChapterRead(
            chapter_id=r[0],
            chapter_number=r[1],
            chapter_title=r[2],
            subject_id=r[3],
            subject_name=r[4],
            video_count=r[5],
        )
        for r in rows
    ]
    return FeaturedVideosRead(
        total_videos=sum(c.video_count for c in chapters),
        total_chapters=len(chapters),
        chapters=chapters,
    )
