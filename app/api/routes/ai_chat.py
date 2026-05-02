"""HTTP surface for the premium AI tutor.

- /me/chat-sessions/* — student / individual learner reads + writes their
  own sessions. Gated on `User.ai_chat_enabled`.
- /admin/users/{id}/ai-chat-enabled — platform admin toggles entitlement.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_learner,
    require_platform_admin,
)
from app.db.session import get_db
from app.models.ai_chat import ChatMessage, ChatScope, ChatSession
from app.models.school import Student, User
from app.services import ai_chat_service
from app.services.ai_chat_service import (
    ChatNotEntitledError,
    ChatScopeError,
)


# ---------- DTOs ----------

class ChatSessionCreateRequest(BaseModel):
    scope: str = Field(description="'CHAPTER' or 'TOPIC'")
    chapter_id: int | None = None
    topic_id: int | None = None


class ChatSessionRead(BaseModel):
    id: int
    student_id: int
    scope: str
    chapter_id: int | None
    topic_id: int | None
    title: str
    message_count: int
    last_message_at: datetime | None
    created_at: datetime


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionDetailRead(ChatSessionRead):
    messages: list[ChatMessageRead] = []


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AiChatEnabledRequest(BaseModel):
    enabled: bool


# ---------- learner-facing routes ----------

router = APIRouter(prefix="/me/chat-sessions", tags=["ai-chat"])


def _student_for(db: Session, user: User) -> Student:
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise HTTPException(
            status_code=400, detail="No student profile is associated with this user."
        )
    return student


def _serialise_session(session: ChatSession) -> ChatSessionRead:
    return ChatSessionRead(
        id=session.id,
        student_id=session.student_id,
        scope=session.scope.value,
        chapter_id=session.chapter_id,
        topic_id=session.topic_id,
        title=session.title,
        message_count=session.message_count,
        last_message_at=session.last_message_at,
        created_at=session.created_at,
    )


def _serialise_detail(session: ChatSession) -> ChatSessionDetailRead:
    base = _serialise_session(session)
    return ChatSessionDetailRead(
        **base.model_dump(),
        messages=[
            ChatMessageRead(
                id=m.id, role=m.role.value, content=m.content, created_at=m.created_at
            )
            for m in sorted(session.messages, key=lambda m: m.id)
        ],
    )


@router.get("", response_model=list[ChatSessionRead])
def list_chat_sessions(
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    if not user.ai_chat_enabled:
        # Empty list — UI can show the "Premium feature" CTA without 403'ing.
        return []
    student = _student_for(db, user)
    return [_serialise_session(s) for s in ai_chat_service.list_sessions(db, student=student)]


@router.post("", response_model=ChatSessionDetailRead, status_code=201)
def create_chat_session(
    payload: ChatSessionCreateRequest,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    if not user.ai_chat_enabled:
        raise HTTPException(
            status_code=403,
            detail=(
                "AI tutor is a premium feature. Ask your school admin to "
                "enable it for your account."
            ),
        )
    student = _student_for(db, user)
    try:
        scope = ChatScope(payload.scope.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="scope must be CHAPTER or TOPIC.")
    try:
        session = ai_chat_service.create_session(
            db,
            user=user,
            student=student,
            scope=scope,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
        )
    except ChatNotEntitledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ChatScopeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return _serialise_detail(session)


@router.get("/{session_id}", response_model=ChatSessionDetailRead)
def get_chat_session(
    session_id: int,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    if not user.ai_chat_enabled:
        raise HTTPException(status_code=403, detail="AI tutor is disabled.")
    student = _student_for(db, user)
    session = db.get(ChatSession, session_id)
    if session is None or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return _serialise_detail(session)


@router.post("/{session_id}/messages", response_model=ChatMessageRead, status_code=201)
def post_chat_message(
    session_id: int,
    payload: ChatMessageCreateRequest,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    if not user.ai_chat_enabled:
        raise HTTPException(status_code=403, detail="AI tutor is disabled.")
    student = _student_for(db, user)
    session = db.get(ChatSession, session_id)
    if session is None or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    try:
        assistant_msg = ai_chat_service.send_user_message(
            db,
            user=user,
            student=student,
            session=session,
            user_text=payload.content,
        )
    except ChatNotEntitledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ChatScopeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(assistant_msg)
    return ChatMessageRead(
        id=assistant_msg.id,
        role=assistant_msg.role.value,
        content=assistant_msg.content,
        created_at=assistant_msg.created_at,
    )


@router.delete("/{session_id}", status_code=204)
def delete_chat_session(
    session_id: int,
    user: User = Depends(require_learner),
    db: Session = Depends(get_db),
):
    student = _student_for(db, user)
    session = db.get(ChatSession, session_id)
    if session is None or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    ai_chat_service.delete_session(db, student=student, session=session)
    db.commit()


# ---------- admin entitlement toggle ----------

admin_router = APIRouter(prefix="/admin", tags=["ai-chat-admin"])


@admin_router.post("/users/{user_id}/ai-chat-enabled")
def set_ai_chat_enabled(
    user_id: int,
    payload: AiChatEnabledRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    target.ai_chat_enabled = payload.enabled
    db.commit()
    return {"user_id": target.id, "ai_chat_enabled": target.ai_chat_enabled}


@admin_router.get("/users")
def list_users_for_admin(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """Compact user list for the platform admin entitlement console."""
    rows = db.scalars(select(User).order_by(User.id))
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "school_id": u.school_id,
            "ai_chat_enabled": u.ai_chat_enabled,
        }
        for u in rows
    ]


@router.get("/_/me", include_in_schema=False)
def whoami_chat_status(user: User = Depends(get_current_user)):
    """Cheap probe for the frontend to show the right CTA without fetching
    the whole user object via /auth/me.
    """
    return {"ai_chat_enabled": bool(user.ai_chat_enabled)}
