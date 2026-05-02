"""AI tutor chat service.

Each session is bound to one chapter or one topic. Each user turn pulls in
the chapter or topic text as the LLM context so answers stay on-scope.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm import LLMError, get_llm_provider
from app.llm.base import ChatTurn
from app.llm.prompts.ai_chat import build_chat_system_prompt
from app.models.ai_chat import ChatMessage, ChatRole, ChatScope, ChatSession
from app.models.curriculum import Book, Chapter, SchoolClass, Subject, Topic
from app.models.school import Student, User


# Cap chapter / topic text fed to the LLM so we stay under per-request token
# limits. ~30k chars ≈ 7-8k tokens — leaves room for chat history + response.
_MAX_CONTEXT_CHARS = 30_000

# How many prior turns we replay back to the model on each call. Higher = more
# coherent follow-ups, but eats into the token budget.
_HISTORY_WINDOW = 6


class ChatNotEntitledError(Exception):
    """User does not have the AI chat premium flag enabled."""


class ChatScopeError(Exception):
    """The session's scope (chapter / topic) is malformed."""


def create_session(
    db: Session,
    *,
    user: User,
    student: Student,
    scope: ChatScope,
    chapter_id: int | None = None,
    topic_id: int | None = None,
) -> ChatSession:
    if not user.ai_chat_enabled:
        raise ChatNotEntitledError(
            "AI tutor is a premium feature. Ask your school admin to enable it."
        )

    chapter, topic = _resolve_scope(db, scope, chapter_id, topic_id)
    title = (
        f"AI tutor · {topic.name}"
        if scope == ChatScope.TOPIC
        else f"AI tutor · Ch {chapter.chapter_number} {chapter.title}"
    )
    session = ChatSession(
        student_id=student.id,
        scope=scope,
        chapter_id=chapter.id if scope == ChatScope.CHAPTER else None,
        topic_id=topic.id if scope == ChatScope.TOPIC else None,
        title=title,
    )
    db.add(session)
    db.flush()
    return session


def list_sessions(db: Session, *, student: Student) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.student_id == student.id)
            .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.id.desc())
        )
    )


def send_user_message(
    db: Session,
    *,
    user: User,
    student: Student,
    session: ChatSession,
    user_text: str,
) -> ChatMessage:
    """Append a user turn, call the LLM with the RAG context + history, and
    save the assistant turn. Returns the assistant message."""
    if not user.ai_chat_enabled:
        raise ChatNotEntitledError("AI tutor is disabled for this account.")
    if session.student_id != student.id:
        raise ChatScopeError("Session does not belong to this student.")

    cleaned = (user_text or "").strip()
    if not cleaned:
        raise ChatScopeError("Empty message.")

    # Resolve scope context fresh so a chapter retitled / topic edited still
    # gets the latest text.
    chapter, topic = _resolve_scope(
        db,
        session.scope,
        session.chapter_id,
        session.topic_id,
    )
    context_text = _context_text(chapter, topic)
    book = db.get(Book, chapter.book_id)
    subject = db.get(Subject, book.subject_id) if book else None
    klass = db.get(SchoolClass, subject.class_id) if subject else None

    system_prompt = build_chat_system_prompt(
        class_level=klass.level if klass else 6,
        subject_name=subject.name if subject else "Science",
        chapter_number=chapter.chapter_number,
        chapter_title=chapter.title,
        topic_name=topic.name if topic is not None else None,
        context_text=context_text,
    )

    history = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.desc())
            .limit(_HISTORY_WINDOW)
        )
    )
    history.reverse()

    messages: list[ChatTurn] = [{"role": "system", "content": system_prompt}]
    for m in history:
        messages.append({
            "role": "user" if m.role == ChatRole.USER else "assistant",
            "content": m.content,
        })
    messages.append({"role": "user", "content": cleaned})

    # Persist the user turn before calling the LLM so a failed call still
    # leaves a record of what the student tried to ask.
    user_msg = ChatMessage(
        session_id=session.id,
        role=ChatRole.USER,
        content=cleaned,
    )
    db.add(user_msg)
    db.flush()

    provider = get_llm_provider()
    try:
        reply = provider.chat(messages=messages, temperature=0.4, max_tokens=800)
    except LLMError as exc:
        # Save a graceful assistant fallback so the conversation thread isn't
        # broken even when Groq is rate-limited.
        reply = (
            "I'm having trouble reaching my brain right now. Please try again "
            f"in a moment. (technical detail: {exc})"
        )

    assistant_msg = ChatMessage(
        session_id=session.id,
        role=ChatRole.ASSISTANT,
        content=reply,
    )
    db.add(assistant_msg)
    db.flush()

    now = datetime.now(timezone.utc)
    session.last_message_at = now
    session.message_count = (session.message_count or 0) + 2
    db.flush()
    return assistant_msg


def delete_session(db: Session, *, student: Student, session: ChatSession) -> None:
    if session.student_id != student.id:
        raise ChatScopeError("Session does not belong to this student.")
    db.delete(session)
    db.flush()


# ---- helpers ----

def _resolve_scope(
    db: Session,
    scope: ChatScope,
    chapter_id: int | None,
    topic_id: int | None,
) -> tuple[Chapter, Topic | None]:
    if scope == ChatScope.TOPIC:
        if topic_id is None:
            raise ChatScopeError("topic-scoped session requires topic_id.")
        topic = db.get(Topic, topic_id)
        if topic is None:
            raise ChatScopeError(f"Topic {topic_id} not found.")
        chapter = db.get(Chapter, topic.chapter_id)
        if chapter is None:
            raise ChatScopeError(f"Chapter {topic.chapter_id} not found.")
        return chapter, topic

    if scope == ChatScope.CHAPTER:
        if chapter_id is None:
            raise ChatScopeError("chapter-scoped session requires chapter_id.")
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise ChatScopeError(f"Chapter {chapter_id} not found.")
        return chapter, None

    raise ChatScopeError(f"Unknown scope {scope}.")


def _context_text(chapter: Chapter, topic: Topic | None) -> str:
    """Pick the right slice of text for the LLM context.

    Prefer topic.full_text when set; fall back to the full chapter text.
    Cap to _MAX_CONTEXT_CHARS so we stay under the token budget.
    """
    if topic is not None and topic.full_text and topic.full_text.strip():
        text = topic.full_text
    else:
        text = chapter.full_text or ""
    if len(text) > _MAX_CONTEXT_CHARS:
        text = text[:_MAX_CONTEXT_CHARS] + "\n…[truncated for token budget]"
    return text
