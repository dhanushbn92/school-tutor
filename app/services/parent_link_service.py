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


# ---------------------------------------------------------------------------
# Parent insights — Stage 6 enrichment
# ---------------------------------------------------------------------------
#
# Encouraging-view summary helpers for the parent dashboard:
#   - chapter_rollup    counts of mastered / in-practice / to-explore
#   - top strengths     outcomes the child is consistently strong on
#   - top "growing in"  outcomes still being worked on (NEVER framed
#                       as failures)
#   - stamps tally      total stamps grouped by kind
#
# Stays inside the parent_link_service module so the privacy invariant
# is easier to audit: there is exactly ONE place where parent-facing
# data is shaped, and it never touches `LearnerMistake`.


# Same thresholds as the learner-side narrative tiles (Stage 4) — keeps
# the parent's "Mastered" count consistent with what the child sees on
# their own dashboard.
_MASTERY_FLOOR = 0.75
_CHAPTER_MASTERED_RATIO = 0.8
_TOP_N = 3


def compute_child_insights(db: Session, *, child_user_id: int) -> dict:
    """Build the enriched parent-view payload for one child.

    Resolves the child's primary class + subject from their active
    enrollment, builds the mastery grid for that subject, and derives
    the encouraging aggregates above. Returns {} when the child has
    no mastery data yet — the frontend renders an empty-state in that
    case rather than zeros.

    Mistake detail is deliberately NOT included. The mastery grid we
    consume has no per-mistake info — it's a snapshot of outcome
    mastery levels. So even an audit of the response payload can't
    accidentally surface a child's mistakes.
    """
    from app.models import (  # local import to dodge cycles
        Enrollment,
        EnrollmentStatus,
        Section,
        Student,
        Subject,
    )
    from app.services import mastery_service

    student = db.scalar(select(Student).where(Student.user_id == child_user_id))
    if student is None:
        return {}

    # Pick the active enrollment to anchor class_level. Multi-section
    # students just get the first active section's class — same as
    # the learner's own dashboard does.
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrollment is None:
        return {}
    section = db.get(Section, enrollment.section_id)
    if section is None:
        return {}

    # Subject: prefer "Science" (matches the learner dashboard's
    # default) so parent + learner views agree; fall back to any
    # subject the section's class has.
    subjects = list(
        db.scalars(
            select(Subject).where(Subject.class_id == section.class_id)
        ).all()
    )
    if not subjects:
        return {}
    subject = next((s for s in subjects if s.name == "Science"), subjects[0])

    class_level = _class_level_for(db, section)
    if class_level is None:
        return {}
    grid = mastery_service.build_student_grid(
        db,
        student_id=student.id,
        class_level=class_level,
        subject_id=subject.id,
    )

    chapter_rollup, strengths, growing = _derive_outcome_aggregates(grid)
    stamps_by_kind = _stamps_tally(db, user_id=child_user_id)

    return {
        "subject_name": subject.name,
        "subject_id": subject.id,
        "class_level": grid.get("class_level"),
        "chapter_rollup": chapter_rollup,
        "strengths": strengths,
        "growing_in": growing,
        "stamps_by_kind": stamps_by_kind,
    }


def _class_level_for(db: Session, section) -> int | None:  # type: ignore[no-untyped-def]
    """Fallback class_level resolver for Section rows that don't
    expose it directly. Section.class_id -> SchoolClass.level."""
    from app.models import SchoolClass

    cls = db.get(SchoolClass, section.class_id)
    return cls.level if cls is not None else None


def _derive_outcome_aggregates(
    grid: dict,
) -> tuple[dict, list[dict], list[dict]]:
    """Pure transform: chapter rollup + top-N strengths + top-N
    "growing in" lists. Mirrors the LearnerProgressNarrative logic
    on the frontend so the parent sees the same counts as the child
    sees on their own dashboard."""
    mastered_chapters = 0
    in_practice_chapters = 0
    to_explore_chapters = 0

    attempted: list[dict] = []
    for ch in grid.get("chapters", []):
        outcomes = ch.get("outcomes", [])
        if not outcomes:
            to_explore_chapters += 1
            continue
        n_total = len(outcomes)
        n_mastered = 0
        n_attempted = 0
        for o in outcomes:
            mastery = o.get("mastery")
            attempts = o.get("attempts", 0)
            if attempts > 0 and mastery is not None:
                n_attempted += 1
                attempted.append(
                    {
                        "code": o.get("code"),
                        "description": o.get("description"),
                        "mastery": mastery,
                        "attempts": attempts,
                        "chapter_id": ch.get("chapter_id"),
                        "chapter_number": ch.get("chapter_number"),
                        "chapter_title": ch.get("chapter_title"),
                    }
                )
                if mastery >= _MASTERY_FLOOR:
                    n_mastered += 1

        if n_attempted == 0:
            to_explore_chapters += 1
        elif n_total > 0 and n_mastered / n_total >= _CHAPTER_MASTERED_RATIO:
            mastered_chapters += 1
        else:
            in_practice_chapters += 1

    strengths = sorted(
        [o for o in attempted if o["mastery"] >= _MASTERY_FLOOR],
        key=lambda o: (-o["mastery"], -o["attempts"]),
    )[:_TOP_N]

    growing = sorted(
        [o for o in attempted if o["mastery"] < _MASTERY_FLOOR],
        key=lambda o: (o["mastery"], -o["attempts"]),
    )[:_TOP_N]

    chapter_rollup = {
        "mastered": mastered_chapters,
        "in_practice": in_practice_chapters,
        "to_explore": to_explore_chapters,
    }
    return chapter_rollup, strengths, growing


def _stamps_tally(db: Session, *, user_id: int) -> dict[str, int]:
    """Total stamp counts grouped by kind. Includes only the four
    known kinds — anything unexpected falls through silently."""
    from app.models import LearnerStamp, StampKind
    from sqlalchemy import func as _f

    rows = db.execute(
        select(LearnerStamp.kind, _f.count(LearnerStamp.id))
        .where(LearnerStamp.user_id == user_id)
        .group_by(LearnerStamp.kind)
    ).all()
    by_kind: dict[str, int] = {k.value: 0 for k in StampKind}
    for kind, count in rows:
        # `kind` is a StampKind StrEnum value
        key = kind.value if hasattr(kind, "value") else str(kind)
        by_kind[key] = int(count)
    return by_kind


# Re-export for the auth router to use without importing the model.
PARENT_ROLE = UserRole.PARENT
