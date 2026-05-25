"""Service for parent → child "well-done note" messages
(Stage 6 of the child-centric roadmap).

A learner sees up to a handful of undismissed notes on their
dashboard in a small "Notes from family" card. Dismissing a note
hides it from the dashboard but doesn't delete the row — the parent
can scroll their own send history later.

Constraints:
  - The message is capped to 280 chars at the model level; this
    service additionally trims whitespace and rejects empty strings
    so a "send" without any actual content can't happen.
  - The parent ↔ child link must currently be APPROVED. Revoked
    parents can't send fresh notes; old notes remain visible to the
    learner until they dismiss.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import ParentEncouragement
from app.services import parent_link_service


class EncouragementError(Exception):
    """Domain-level error surfaced at the endpoint."""


# Hard cap matches the DB column. The frontend should enforce it
# client-side as well, but we re-check here so a hand-rolled API
# call can't write longer values.
MAX_MESSAGE_LENGTH = 280


def send(
    db: Session,
    *,
    parent_user_id: int,
    student_user_id: int,
    message: str,
) -> ParentEncouragement:
    """Validate the link + message, then write one row. Returns the
    newly-created row so the endpoint can echo it back to the
    parent's "you sent…" toast."""
    text = (message or "").strip()
    if not text:
        raise EncouragementError("Write a short message before sending.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise EncouragementError(
            f"Keep it under {MAX_MESSAGE_LENGTH} characters."
        )

    try:
        parent_link_service.assert_link_active(
            db,
            parent_user_id=parent_user_id,
            student_user_id=student_user_id,
        )
    except parent_link_service.ParentLinkError as exc:
        raise EncouragementError(str(exc)) from exc

    row = ParentEncouragement(
        parent_user_id=parent_user_id,
        student_user_id=student_user_id,
        message=text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_learner(
    db: Session, *, student_user_id: int, limit: int = 20, only_undismissed: bool = True
) -> list[ParentEncouragement]:
    """Notes received by a learner. The dashboard uses
    `only_undismissed=True` so dismissed notes drop off automatically;
    a future "history" view could pass False."""
    stmt = select(ParentEncouragement).where(
        ParentEncouragement.student_user_id == student_user_id
    )
    if only_undismissed:
        stmt = stmt.where(ParentEncouragement.dismissed_at.is_(None))
    stmt = stmt.order_by(desc(ParentEncouragement.sent_at)).limit(limit)
    return list(db.scalars(stmt).all())


def list_sent_by_parent(
    db: Session, *, parent_user_id: int, child_user_id: int | None = None, limit: int = 20
) -> list[ParentEncouragement]:
    """Audit view for a parent — what they've sent recently. Optional
    `child_user_id` filter for multi-child parents."""
    stmt = select(ParentEncouragement).where(
        ParentEncouragement.parent_user_id == parent_user_id
    )
    if child_user_id is not None:
        stmt = stmt.where(ParentEncouragement.student_user_id == child_user_id)
    stmt = stmt.order_by(desc(ParentEncouragement.sent_at)).limit(limit)
    return list(db.scalars(stmt).all())


def dismiss(
    db: Session, *, encouragement_id: int, student_user_id: int
) -> ParentEncouragement:
    """The learner clears one note off their dashboard. Idempotent:
    a re-dismiss on an already-dismissed note is a no-op."""
    row = db.get(ParentEncouragement, encouragement_id)
    if row is None or row.student_user_id != student_user_id:
        raise EncouragementError("That note doesn't exist.")
    if row.dismissed_at is None:
        row.dismissed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return row


def to_dict(row: ParentEncouragement) -> dict:
    """Shape for the API layer. Includes the parent's user_id but
    NOT their email / school_id — the learner doesn't need it."""
    return {
        "id": row.id,
        "parent_user_id": row.parent_user_id,
        "message": row.message,
        "sent_at": row.sent_at,
        "dismissed_at": row.dismissed_at,
    }
