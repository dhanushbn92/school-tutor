"""Smart-speaker API: key handling, session tokens, board scoping, replay and grading.

Runs against a throwaway in-memory SQLite DB with a minimal app, so nothing here
can touch the configured (real) database.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register every table on Base.metadata)
from app.api.routes import chapter_videos, smart_speaker
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.models.assessment import Submission
from app.models.curriculum import AcademicYear, Book, Chapter, SchoolClass, Subject
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType
from app.models.school import (
    Enrollment,
    EnrollmentStatus,
    School,
    Section,
    Student,
    User,
    UserRole,
)
from app.services import question_bank_service
from app.services import smart_speaker_service as svc

KEY = "test-device-key"
EMAIL = "learner@x.org"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def speaker_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "smart_speaker_api_key", KEY)


def _world(db, *, school_active=True):
    """A NIOS class-12 learner. CBSE also has a class-12 subject with the same name."""
    c12 = SchoolClass(level=12, display_name="Class 12")
    year = AcademicYear(name="2026-27")
    school = School(name="S", board="NIOS", is_active=school_active)
    db.add_all([c12, year, school])
    db.flush()

    nios = Subject(class_id=c12.id, name="Sanskrit", board="NIOS")
    cbse = Subject(class_id=c12.id, name="Sanskrit", board="CBSE")
    db.add_all([nios, cbse])
    db.flush()
    book = Book(subject_id=nios.id, title="B", ncert_code="NIOS-1", academic_year="2026-27")
    db.add(book)
    db.flush()
    chapter = Chapter(book_id=book.id, chapter_number=1, title="Lesson one")
    db.add(chapter)

    user = User(
        email=EMAIL, hashed_password="x", role=UserRole.INDIVIDUAL_LEARNER, full_name="L", school_id=school.id
    )
    db.add(user)
    db.flush()
    student = Student(school_id=school.id, full_name="L", user_id=user.id)
    section = Section(school_id=school.id, class_id=c12.id, academic_year_id=year.id, name="P")
    db.add_all([student, section])
    db.flush()
    db.add(
        Enrollment(
            student_id=student.id,
            section_id=section.id,
            academic_year_id=year.id,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    db.commit()
    return user, chapter, nios


def _questions(db, chapter, user, kinds):
    rows = []
    for i, (qtype, options, correct) in enumerate(kinds, start=1):
        q = Question(
            chapter_id=chapter.id,
            type=qtype,
            difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.APPROVED,
            text=f"Question {i}?",
            options=options,
            correct_answer=correct,
            marks=1,
            created_by_id=user.id,
        )
        db.add(q)
        rows.append(q)
    db.commit()
    return rows


def _client(session_factory) -> TestClient:
    app = FastAPI()
    app.include_router(smart_speaker.router)
    app.include_router(chapter_videos.router)

    def _db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


def _headers(key=KEY, email=EMAIL):
    return {"X-API-Key": key, "X-User-Email": email}


# --------------------------------------------------------------------------- #
# API key and identity
# --------------------------------------------------------------------------- #
def test_correct_key_and_known_learner_is_accepted(session_factory):
    with session_factory() as db:
        _world(db)
    res = _client(session_factory).get("/smart-speaker/subjects", headers=_headers())
    assert res.status_code == 200


def test_wrong_key_is_rejected(session_factory):
    with session_factory() as db:
        _world(db)
    res = _client(session_factory).get("/smart-speaker/subjects", headers=_headers(key="nope"))
    assert res.status_code == 401


def test_non_ascii_key_is_a_401_not_a_server_error(session_factory):
    with session_factory() as db:
        _world(db)
    res = _client(session_factory).get(
        "/smart-speaker/subjects", headers={"X-API-Key": "café".encode("latin-1"), "X-User-Email": EMAIL}
    )
    assert res.status_code == 401


def test_unknown_email_is_rejected(session_factory):
    with session_factory() as db:
        _world(db)
    res = _client(session_factory).get(
        "/smart-speaker/subjects", headers=_headers(email="who@x.org")
    )
    assert res.status_code == 401


def test_learner_of_a_disabled_school_is_locked_out(session_factory):
    with session_factory() as db:
        _world(db, school_active=False)
    res = _client(session_factory).get("/smart-speaker/subjects", headers=_headers())
    assert res.status_code == 401


# --------------------------------------------------------------------------- #
# A speaker session token must never work as a web login
# --------------------------------------------------------------------------- #
def test_session_token_is_not_a_login_token(session_factory):
    with session_factory() as db:
        user, _chapter, _subject = _world(db)
    token = svc._encode_session(user, assessment_id=1, qids=[1], cursor=0, answers={})
    res = _client(session_factory).get(
        "/chapter-videos/featured", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401


# --------------------------------------------------------------------------- #
# Subjects stay inside the learner's board
# --------------------------------------------------------------------------- #
def test_subjects_are_limited_to_the_learners_board(session_factory):
    with session_factory() as db:
        _world(db)
    body = _client(session_factory).get("/smart-speaker/subjects", headers=_headers()).json()
    assert [(s["name"], s["board"]) for s in body["subjects"]] == [("Sanskrit", "NIOS")]


# --------------------------------------------------------------------------- #
# Answer grading
# --------------------------------------------------------------------------- #
def test_true_false_letters_map_to_true_and_false():
    q = Question(type=QuestionType.TRUE_FALSE, correct_answer="True")
    assert svc._coerce_choice_answer(q, "A") == "True"
    assert svc._coerce_choice_answer(q, "(b)") == "False"
    assert svc._coerce_choice_answer(q, "True") == "True"


def test_mcq_letters_still_map_to_the_option_text():
    q = Question(type=QuestionType.MCQ, options={"choices": ["red", "green"]}, correct_answer="green")
    assert svc._coerce_choice_answer(q, "B") == "green"
    assert svc._coerce_choice_answer(q, "green") == "green"


# --------------------------------------------------------------------------- #
# A whole voice quiz, and replaying it
# --------------------------------------------------------------------------- #
def _start(session_factory, monkeypatch, kinds):
    with session_factory() as db:
        user, chapter, subject = _world(db)
        rows = _questions(db, chapter, user, kinds)
        chapter_id = chapter.id
    monkeypatch.setattr(
        question_bank_service, "sample_questions", lambda db, **kw: [db.get(Question, r.id) for r in rows]
    )
    client = _client(session_factory)
    res = client.post(
        "/smart-speaker/tests/start",
        headers=_headers(),
        json={"subject": "Sanskrit", "chapter_id": chapter_id, "question_count": len(kinds)},
    )
    assert res.status_code == 201, res.text
    return client, res.json()


def test_quiz_grades_each_answer_and_cannot_be_replayed(session_factory, monkeypatch):
    client, started = _start(
        session_factory,
        monkeypatch,
        [
            (QuestionType.MCQ, {"choices": ["red", "green"]}, "green"),
            (QuestionType.TRUE_FALSE, None, "True"),
        ],
    )
    token0 = started["session_token"]

    # Q1: the letter "B" means "green", which is right.
    first = client.post(
        "/smart-speaker/tests/answer", headers=_headers(), json={"session_token": token0, "answer_text": "B"}
    ).json()
    assert first["verdict"] == "correct" and first["finished"] is False

    # Q2: the spoken letter "A" means True, which is right.
    last = client.post(
        "/smart-speaker/tests/answer",
        headers=_headers(),
        json={"session_token": first["session_token"], "answer_text": "A"},
    ).json()
    assert last["verdict"] == "correct" and last["finished"] is True
    assert last["result"]["score"] == 2 and last["result"]["percent"] == 100

    with session_factory() as db:
        assert len(db.scalars(select(Submission)).all()) == 1

    # Replaying an earlier token after the test is done is refused, and creates nothing new.
    replay = client.post(
        "/smart-speaker/tests/answer",
        headers=_headers(),
        json={"session_token": first["session_token"], "answer_text": "A"},
    )
    assert replay.status_code == 409
    with session_factory() as db:
        assert len(db.scalars(select(Submission)).all()) == 1


def test_tell_me_more_needs_an_answered_question(session_factory, monkeypatch):
    client, started = _start(
        session_factory, monkeypatch, [(QuestionType.MCQ, {"choices": ["red", "green"]}, "green")]
    )
    res = client.post(
        "/smart-speaker/tests/more",
        headers=_headers(),
        json={"session_token": started["session_token"], "kind": "example"},
    )
    assert res.status_code == 400
