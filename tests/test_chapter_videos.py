"""GET /chapter-videos: ordered, published-only, auth required.

Uses a throwaway in-memory SQLite DB and a minimal app that mounts only this
router, so nothing here can touch the configured (real) database.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register every table on Base.metadata)
from app.api.routes import chapter_videos
from app.auth.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.models.chapter_video import ChapterVideo
from app.models.curriculum import AcademicYear, Book, Chapter, SchoolClass, Subject
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    User,
    UserRole,
)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _app(session_factory, *, user=None) -> TestClient:
    app = FastAPI()
    app.include_router(chapter_videos.router)

    def _db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _video(chapter_id, seq, *, published=True, kind="word_by_word"):
    return ChapterVideo(
        chapter_id=chapter_id,
        sequence=seq,
        title=f"part {seq}",
        kind=kind,
        provider="gdrive",
        external_id=f"id{chapter_id}x{seq}".ljust(25, "z"),
        is_published=published,
    )


def _admin():
    """A platform admin: sees every chapter, so these tests only exercise ordering."""
    return User(
        email="a@x.org", hashed_password="x", role=UserRole.PLATFORM_ADMIN, full_name="A", school_id=None
    )


def _two_chapters(db):
    """Two chapters of one NIOS class-12 subject; returns their ids."""
    c12 = SchoolClass(level=12, display_name="Class 12")
    db.add(c12)
    db.flush()
    subj = Subject(class_id=c12.id, name="Sanskrit", board="NIOS")
    db.add(subj)
    db.flush()
    book = Book(subject_id=subj.id, title="B", ncert_code="NIOS-1", academic_year="2026-27")
    db.add(book)
    db.flush()
    chapters = [Chapter(book_id=book.id, chapter_number=n, title=f"C{n}") for n in (1, 2)]
    db.add_all(chapters)
    db.flush()
    return [c.id for c in chapters]


def test_lists_published_videos_in_sequence_order(session_factory):
    with session_factory() as db:
        ch1, ch2 = _two_chapters(db)
        # Inserted out of order on purpose.
        db.add_all(
            [
                _video(ch1, 3),
                _video(ch1, 1, kind="lesson"),
                _video(ch1, 2),
                _video(ch1, 4, published=False),  # draft: hidden
                _video(ch2, 1, kind="lesson"),  # other chapter: excluded
            ]
        )
        db.commit()

    res = _app(session_factory, user=_admin()).get("/chapter-videos", params={"chapter_id": ch1})
    assert res.status_code == 200
    body = res.json()
    assert [v["sequence"] for v in body] == [1, 2, 3]
    assert body[0]["kind"] == "lesson"
    assert {v["chapter_id"] for v in body} == {ch1}
    assert set(body[0]) == {"id", "chapter_id", "sequence", "title", "kind", "provider", "external_id"}


def test_chapter_without_videos_returns_empty_list(session_factory):
    res = _app(session_factory, user=_admin()).get("/chapter-videos", params={"chapter_id": 99})
    assert res.status_code == 200
    assert res.json() == []


def test_requires_chapter_id(session_factory):
    res = _app(session_factory, user=_admin()).get("/chapter-videos")
    assert res.status_code == 422


def test_requires_login(session_factory):
    res = _app(session_factory, user=None).get("/chapter-videos", params={"chapter_id": 7})
    assert res.status_code == 401


# --------------------------------------------------------------------------- #
# GET /chapter-videos/featured: scoped by board and (for learners) class.
# --------------------------------------------------------------------------- #
def _world(db, *, enrol=True, role=UserRole.INDIVIDUAL_LEARNER, board="NIOS"):
    """NIOS and CBSE both have a class 12; NIOS also has a class 10."""
    c12 = SchoolClass(level=12, display_name="Class 12")
    c10 = SchoolClass(level=10, display_name="Class 10")
    year = AcademicYear(name="2026-27")
    school = School(name="S", board=board)
    db.add_all([c12, c10, year, school])
    db.flush()

    books = {}  # one subject + book per (class, board, subject)

    def chapter(cls, board_, subject, num, title):
        key = (cls.id, board_, subject)
        if key not in books:
            subj = Subject(class_id=cls.id, name=subject, board=board_)
            db.add(subj)
            db.flush()
            book = Book(subject_id=subj.id, title="B", ncert_code=f"{board_}-{subject}-{cls.level}", academic_year="2026-27")
            db.add(book)
            db.flush()
            books[key] = book
        book = books[key]
        ch = Chapter(book_id=book.id, chapter_number=num, title=title)
        db.add(ch)
        db.flush()
        return ch

    nios12 = chapter(c12, "NIOS", "Sanskrit", 1, "Jivana")
    nios12b = chapter(c12, "NIOS", "Sanskrit", 2, "Yadi")
    nios10 = chapter(c10, "NIOS", "Maths", 1, "Sets")
    cbse12 = chapter(c12, "CBSE", "Physics", 1, "Waves")
    for ch, n in ((nios12, 3), (nios12b, 2), (nios10, 4), (cbse12, 5)):
        for i in range(1, n + 1):
            db.add(_video(ch.id, i))
    # a draft video that must never be counted
    db.add(_video(nios12.id, 99, published=False))

    user = User(
        email="u@x.org", hashed_password="x", role=role, full_name="U", school_id=school.id
    )
    db.add(user)
    db.flush()
    if enrol:
        stu = Student(school_id=school.id, full_name="U", user_id=user.id)
        sec = Section(school_id=school.id, class_id=c12.id, academic_year_id=year.id, name="P")
        db.add_all([stu, sec])
        db.flush()
        db.add(
            Enrollment(
                student_id=stu.id,
                section_id=sec.id,
                academic_year_id=year.id,
                status=EnrollmentStatus.ACTIVE,
            )
        )
    db.commit()
    return user


def _featured(session_factory, user):
    app = FastAPI()
    app.include_router(chapter_videos.router)

    def _db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app).get("/chapter-videos/featured")


def test_featured_learner_sees_only_own_board_and_class(session_factory):
    with session_factory() as db:
        user = _world(db)
    res = _featured(session_factory, user)
    assert res.status_code == 200
    body = res.json()
    # NIOS class 12 only: Sanskrit ch1 (3 published, the draft is excluded) + ch2 (2).
    # Not NIOS class 10 (4), not CBSE class 12 (5).
    assert body["total_videos"] == 5
    assert body["total_chapters"] == 2
    assert [(c["chapter_number"], c["video_count"]) for c in body["chapters"]] == [(1, 3), (2, 2)]
    assert {c["subject_name"] for c in body["chapters"]} == {"Sanskrit"}


def test_featured_learner_without_enrolment_gets_nothing(session_factory):
    with session_factory() as db:
        user = _world(db, enrol=False)
    body = _featured(session_factory, user).json()
    assert body == {"total_videos": 0, "total_chapters": 0, "chapters": []}


def test_featured_teacher_sees_whole_board_but_not_other_boards(session_factory):
    with session_factory() as db:
        user = _world(db, role=UserRole.TEACHER, enrol=False)
    body = _featured(session_factory, user).json()
    # NIOS class 12 (5) + NIOS class 10 (4); never CBSE.
    assert body["total_videos"] == 9
    assert {c["subject_name"] for c in body["chapters"]} == {"Sanskrit", "Maths"}


def test_featured_platform_admin_sees_everything(session_factory):
    with session_factory() as db:
        user = _world(db, role=UserRole.PLATFORM_ADMIN, enrol=False)
        user.school_id = None
    body = _featured(session_factory, user).json()
    assert body["total_videos"] == 14  # 3 + 2 + 4 + 5, drafts excluded


def _list(session_factory, user, chapter_id):
    return _app(session_factory, user=user).get("/chapter-videos", params={"chapter_id": chapter_id})


def test_list_is_scoped_to_the_learners_board_and_class(session_factory):
    with session_factory() as db:
        user = _world(db)
        ids = {
            (c.title, c.chapter_number): c.id
            for c in db.query(Chapter).all()
        }
    # Own board + class: allowed.
    assert len(_list(session_factory, user, ids[("Jivana", 1)]).json()) == 3
    # Another class of the same board, and another board's chapter: nothing leaks.
    assert _list(session_factory, user, ids[("Sets", 1)]).json() == []
    assert _list(session_factory, user, ids[("Waves", 1)]).json() == []


def test_list_for_a_learner_without_enrolment_is_empty(session_factory):
    with session_factory() as db:
        user = _world(db, enrol=False)
        chapter_id = db.query(Chapter).filter(Chapter.title == "Jivana").one().id
    assert _list(session_factory, user, chapter_id).json() == []
