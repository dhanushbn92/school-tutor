"""Models for the parent / guardian view (Stage 6 of the
child-centric roadmap).

Three small tables backing the parent feature set:

  ParentInviteCode  — short codes the learner generates and hands to
                      a parent. Single-use, 7-day TTL. The code IS
                      the consent — a parent who has the code has the
                      learner's explicit permission to link.
  ParentChildLink   — the live link once a code is consumed. Soft-
                      deleted via `status='REVOKED'` rather than a
                      hard DELETE so the audit trail survives.
  ParentEncouragement — a "well-done" note from parent → child. The
                      learner can dismiss off their dashboard without
                      removing the row (the parent still sees they
                      sent it).

The PARENT user role is declared on `UserRole` itself
(`app.models.school`), not here — adding a value to a StrEnum is
straightforward and keeps role-membership lookups in one place.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParentLinkStatus(StrEnum):
    """Lifecycle of one parent ↔ child link.

    APPROVED — the live state, set the moment a parent consumes a valid
              invite code. Parent can read the child's encouraging
              summary and send notes.
    REVOKED — soft-deleted by the learner. The row stays for audit,
              but parent reads return 403 and encouragements aren't
              accepted.

    PENDING is reserved for a future admin-mediated flow (e.g.
    "parent self-signs-up with no code; school admin must approve").
    Stage 6's invite-code flow skips it entirely.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REVOKED = "REVOKED"


class ParentInviteCode(Base):
    """Short single-use code a learner generates from their profile
    and hands to their parent. The parent enters it during signup;
    the backend consumes the code + creates the link in one shot.

    `expires_at` enforces the 7-day TTL — old codes can sit in the
    table indefinitely (audit), they just can't be used. A daily
    cleanup script could prune consumed/expired rows later; not
    necessary at MVP volume.
    """

    __tablename__ = "parent_invite_codes"

    # The code itself is the primary key — short, random, the lookup
    # path is `WHERE code = ?` so making it the PK saves an index.
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    student_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ParentChildLink(Base):
    """One row per (parent_user_id, student_user_id) pair. The UNIQUE
    constraint blocks duplicate active links; the learner has to
    revoke an existing link before the same parent can relink."""

    __tablename__ = "parent_child_link"
    __table_args__ = (
        UniqueConstraint(
            "parent_user_id",
            "student_user_id",
            name="uq_parent_child_link_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    student_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ParentLinkStatus] = mapped_column(
        String(20), default=ParentLinkStatus.APPROVED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ParentEncouragement(Base):
    """A "well-done" note from a parent to a child. Capped at 280
    chars (Twitter-length on purpose — encouragement, not lectures).

    Visible on the child's dashboard until they dismiss it
    (`dismissed_at` is set). The row is never deleted so the parent
    can scroll their own send history.
    """

    __tablename__ = "parent_encouragement"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    student_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(String(280))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
