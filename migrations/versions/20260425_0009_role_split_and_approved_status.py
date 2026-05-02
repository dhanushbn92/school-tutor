"""role split (admin -> school_admin; +platform_admin/individual_learner) and GC approved status

Revision ID: 20260425_0009
Revises: 20260424_0008
Create Date: 2026-04-25

NOTE: SQLAlchemy's Enum() column maps to PostgreSQL enum labels using the
Python enum NAME (uppercase) by default — i.e. UserRole.SCHOOL_ADMIN persists
as 'SCHOOL_ADMIN', not 'school_admin'. This migration adds the uppercase
labels to keep the existing convention intact.

(Lowercase variants of these labels may also exist in the type from earlier
exploratory ALTERs; they are dead weight, never used by SQLAlchemy, and
PostgreSQL doesn't support DROP VALUE so we leave them.)
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260425_0009"
down_revision: Union[str, None] = "20260424_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PLATFORM_ADMIN'")
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SCHOOL_ADMIN'")
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'INDIVIDUAL_LEARNER'")
        op.execute("ALTER TYPE generatedcontentstatus ADD VALUE IF NOT EXISTS 'APPROVED'")

    # Re-badge existing ADMIN users as SCHOOL_ADMIN now that the new label exists.
    op.execute("UPDATE users SET role = 'SCHOOL_ADMIN' WHERE role = 'ADMIN'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SCHOOL_ADMIN'")
    # PostgreSQL has no DROP VALUE on enums; new labels remain. Recreating the
    # type to reverse this is not worth the operational risk for MVP.
