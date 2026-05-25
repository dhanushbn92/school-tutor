"""Add parent_child_link, parent_invite_codes, parent_encouragement tables

Revision ID: 20260526_0028
Revises: 20260526_0027
Create Date: 2026-05-26

Stage 6 of the child-centric roadmap — the parent / guardian view.

Three new tables, no schema change to existing ones:

  parent_invite_codes
    Learner-generated 6-char codes the parent enters during signup.
    Single-use, 7-day TTL. Multiple codes per child are fine — that
    lets a second guardian sign up with a fresh code without first
    revoking the first guardian.

  parent_child_link
    The link itself, created when a parent successfully consumes an
    invite code. Status starts at APPROVED because the invite code IS
    the approval (the learner explicitly handed it over). REVOKED is
    a soft delete the learner can trigger from their settings.

  parent_encouragement
    "Send a well-done note" payload from parent → child. Append-only
    (dismissals are a separate timestamp, not a DELETE) so the parent
    can audit what they've sent.

The PARENT user role is added at the Python enum level
(`app.models.school.UserRole`) — the column is VARCHAR with
app-level validation, so no ALTER TYPE is needed here.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0028"
down_revision: Union[str, None] = "20260526_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parent_invite_codes",
        # The code itself is the PK — short, random, A-Z0-9 minus
        # ambiguous chars (I/O/0/1). Eight chars × ~32 symbols =
        # ~10^12 — collision-resistant for the small per-learner
        # volume we expect.
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column(
            "student_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consumed_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_parent_invite_codes_student_user_id",
        "parent_invite_codes",
        ["student_user_id"],
    )

    op.create_table(
        "parent_child_link",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "parent_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # APPROVED (live) or REVOKED (soft-deleted). PENDING is
        # reserved for a future admin-mediated flow where the learner
        # hasn't yet confirmed; for now invite codes skip that state.
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="APPROVED",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        # Block duplicate active links — a single parent can only be
        # linked to a given child once. Revoke first to relink.
        sa.UniqueConstraint(
            "parent_user_id",
            "student_user_id",
            name="uq_parent_child_link_pair",
        ),
    )
    op.create_index(
        "ix_parent_child_link_parent_user_id",
        "parent_child_link",
        ["parent_user_id"],
    )
    op.create_index(
        "ix_parent_child_link_student_user_id",
        "parent_child_link",
        ["student_user_id"],
    )

    op.create_table(
        "parent_encouragement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "parent_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message", sa.String(280), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # The learner can dismiss a note off their dashboard without
        # deleting it (the parent still sees they sent it). Null
        # means undismissed → renders in the "Notes from family" card.
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_parent_encouragement_student_user_id",
        "parent_encouragement",
        ["student_user_id"],
    )
    op.create_index(
        "ix_parent_encouragement_parent_user_id",
        "parent_encouragement",
        ["parent_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parent_encouragement_parent_user_id",
        table_name="parent_encouragement",
    )
    op.drop_index(
        "ix_parent_encouragement_student_user_id",
        table_name="parent_encouragement",
    )
    op.drop_table("parent_encouragement")
    op.drop_index(
        "ix_parent_child_link_student_user_id", table_name="parent_child_link"
    )
    op.drop_index(
        "ix_parent_child_link_parent_user_id", table_name="parent_child_link"
    )
    op.drop_table("parent_child_link")
    op.drop_index(
        "ix_parent_invite_codes_student_user_id",
        table_name="parent_invite_codes",
    )
    op.drop_table("parent_invite_codes")
