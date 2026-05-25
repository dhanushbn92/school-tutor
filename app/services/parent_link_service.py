"""Service for the parent ↔ child link workflow (Stage 6).

The flow:
  1. Learner clicks "Invite a parent" on their dashboard.
  2. `generate_invite_code` creates a short, single-use 8-char code
     with a 7-day TTL and stores it in `parent_invite_codes`.
  3. Learner hands the code to the parent (SMS, in person, whatever).
  4. Parent signs up via `POST /auth/signup-parent` with the code in
     the payload.
  5. `consume_invite_code` validates the code, creates a User row +
     a `ParentChildLink` in one transaction, and marks the code
     consumed.

The invite code IS the consent — a parent who has the code has the
learner's explicit permission to link. The learner can later revoke
the link from their settings; the row stays for audit, but
`status='REVOKED'` blocks all read / write access from the parent
side.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ParentChildLink,
    ParentInviteCode,
    ParentLinkStatus,
    User,
    UserRole,
)


# Code charset: 32 unambiguous characters (no I/O/0/1, which are
# easily confused on SMS / paper). 8 chars × 32 symbols = ~10^12
# possibilities — collision-resistant for the small per-learner
# volume we expect.
_CODE_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8
_CODE_TTL_DAYS = 7
_MAX_GENERATION_ATTEMPTS = 10  # vanishingly unlikely to need more than 1


class ParentLinkError(Exception):
    """Domain-level error for the parent-link pipeline."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _random_code() -> str:
    return "".join(secrets.choice(_CODE_CHARSET) for _ in range(_CODE_LENGTH))


def generate_invite_code(db: Session, *, student_user_id: int) -> ParentInviteCode:
    """Create a fresh single-use invite code for a learner. The
    learner can generate as many codes as they want (one per parent
    they want to link); each code is independently valid until
    consumed or expired.

    Retries on PK collision because the charset is 32^8 but we'd
    rather defend than crash on the astronomically rare bad luck.
    """
    expires_at = _now_utc() + timedelta(days=_CODE_TTL_DAYS)
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        code = _random_code()
        existing = db.get(ParentInviteCode, code)
        if existing is not None:
            continue
        row = ParentInviteCode(
            code=code,
            student_user_id=student_user_id,
            expires_at=expires_at,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    # Hit the retry ceiling — almost certainly a bug, not bad luck.
    raise ParentLinkError("Could not generate a unique invite code; try again.")


def consume_invite_code(
    db: Session, *, code: str, parent_user_id: int
) -> ParentChildLink:
    """Validate the invite code and create / re-activate the parent
    ↔ child link. Raises `ParentLinkError` with a friendly message
    for every failure mode the parent should see at signup.

    The code is consumed atomically — only one parent can use a given
    code. The link is `status=APPROVED` immediately because the code
    itself was the learner's consent.
    """
    if not code or len(code) != _CODE_LENGTH:
        raise ParentLinkError("That invite code doesn't look right.")
    code = code.strip().upper()

    invite = db.get(ParentInviteCode, code)
    if invite is None:
        raise ParentLinkError("We couldn't find that invite code.")
    if invite.consumed_at is not None:
        raise ParentLinkError(
            "That invite code has already been used. Ask your child for a fresh one."
        )
    now = _now_utc()
    if invite.expires_at <= now:
        raise ParentLinkError(
            "That invite code has expired. Ask your child for a fresh one."
        )
    if invite.student_user_id == parent_user_id:
        # Defensive — should never happen because the parent is a
        # newly-created User, but explicit guard is cheap.
        raise ParentLinkError("You can't link to your own account.")

    # If a link already exists (e.g. soft-deleted REVOKED row from a
    # previous link), flip it back to APPROVED rather than creating a
    # duplicate. Honours the UNIQUE constraint without a try/catch.
    link = db.scalar(
        select(ParentChildLink).where(
            ParentChildLink.parent_user_id == parent_user_id,
            ParentChildLink.student_user_id == invite.student_user_id,
        )
    )
    if link is None:
        link = ParentChildLink(
            parent_user_id=parent_user_id,
            student_user_id=invite.student_user_id,
            status=ParentLinkStatus.APPROVED,
            approved_at=now,
        )
        db.add(link)
    else:
        link.status = ParentLinkStatus.APPROVED
        link.approved_at = now
        link.revoked_at = None

    invite.consumed_at = now
    invite.consumed_by_user_id = parent_user_id
    db.commit()
    db.refresh(link)
    return link


def list_children(db: Session, *, parent_user_id: int) -> list[User]:
    """Children (User rows) the parent currently has an APPROVED
    link to. Returned in creation order so the dashboard layout is
    stable when a parent has multiple children."""
    rows = list(
        db.scalars(
            select(User)
            .join(
                ParentChildLink,
                ParentChildLink.student_user_id == User.id,
            )
            .where(
                ParentChildLink.parent_user_id == parent_user_id,
                ParentChildLink.status == ParentLinkStatus.APPROVED,
            )
            .order_by(ParentChildLink.created_at)
        ).all()
    )
    return rows


def list_parents(db: Session, *, student_user_id: int) -> list[User]:
    """Parents currently linked to a learner. Used by the learner's
    "Manage parents" UI (the place where they generate codes and
    revoke links)."""
    return list(
        db.scalars(
            select(User)
            .join(
                ParentChildLink,
                ParentChildLink.parent_user_id == User.id,
            )
            .where(
                ParentChildLink.student_user_id == student_user_id,
                ParentChildLink.status == ParentLinkStatus.APPROVED,
            )
            .order_by(ParentChildLink.created_at)
        ).all()
    )


def revoke_link(
    db: Session, *, student_user_id: int, parent_user_id: int
) -> ParentChildLink:
    """Soft-delete the link from the learner's side. The parent's
    next read returns an empty children list; their next encouragement
    POST is rejected."""
    link = db.scalar(
        select(ParentChildLink).where(
            ParentChildLink.parent_user_id == parent_user_id,
            ParentChildLink.student_user_id == student_user_id,
            ParentChildLink.status == ParentLinkStatus.APPROVED,
        )
    )
    if link is None:
        raise ParentLinkError("No active link found to revoke.")
    link.status = ParentLinkStatus.REVOKED
    link.revoked_at = _now_utc()
    db.commit()
    db.refresh(link)
    return link


def assert_link_active(
    db: Session, *, parent_user_id: int, student_user_id: int
) -> ParentChildLink:
    """Raise unless the parent currently has an APPROVED link to the
    learner. Used as the gatekeeper for /me/children/{id}/* reads
    and the encouragement POST."""
    link = db.scalar(
        select(ParentChildLink).where(
            ParentChildLink.parent_user_id == parent_user_id,
            ParentChildLink.student_user_id == student_user_id,
            ParentChildLink.status == ParentLinkStatus.APPROVED,
        )
    )
    if link is None:
        raise ParentLinkError("You aren't linked to this child.")
    return link


def list_invite_codes(
    db: Session, *, student_user_id: int, only_active: bool = True
) -> list[ParentInviteCode]:
    """Codes the learner has generated. `only_active` filters out
    expired / consumed rows so the UI can show "your live codes".
    The audit view (rarely needed) can call with only_active=False."""
    stmt = select(ParentInviteCode).where(
        ParentInviteCode.student_user_id == student_user_id
    )
    if only_active:
        now = _now_utc()
        stmt = stmt.where(
            ParentInviteCode.consumed_at.is_(None),
            ParentInviteCode.expires_at > now,
        )
    stmt = stmt.order_by(ParentInviteCode.created_at.desc())
    return list(db.scalars(stmt).all())


def child_to_dict(child: User) -> dict:
    """Serialise a child User for the parent's children list. The
    parent's encouraging-view promise means we DO NOT include
    school_id / sensitive fields here."""
    return {
        "user_id": child.id,
        "full_name": child.full_name,
        "email": child.email,
    }


# Re-export for the auth router to use without importing the model.
PARENT_ROLE = UserRole.PARENT
