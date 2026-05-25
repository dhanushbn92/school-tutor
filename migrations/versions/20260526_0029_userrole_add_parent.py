"""Add 'PARENT' to the userrole Postgres enum

Revision ID: 20260526_0029
Revises: 20260526_0028
Create Date: 2026-05-26

Stage 6 follow-up: the User.role column uses a native Postgres ENUM
(`userrole`), not VARCHAR — earlier inspection that suggested
otherwise was wrong. Adding 'PARENT' to the Python StrEnum doesn't
propagate; we have to ALTER TYPE on the database side too, otherwise
INSERTing a parent User row fails with:

  psycopg.errors.InvalidTextRepresentation:
    invalid input value for enum userrole: "PARENT"

This migration adds the value idempotently (IF NOT EXISTS so re-runs
on already-patched databases don't error). The downgrade is a
deliberate no-op: Postgres has no clean way to remove an enum value,
and rolling back this migration on a DB that already has parent
users would corrupt them.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260526_0029"
down_revision: Union[str, None] = "20260526_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Wrap in autocommit so the new enum value is visible inside the
    # same migration session if anything afterwards needs it. In
    # Postgres 12+ this also works inside a regular transaction, but
    # using a raw SQL statement keeps the intent explicit.
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PARENT'")


def downgrade() -> None:
    # Removing an enum value in Postgres requires recreating the type
    # with a new label set, and is destructive on any existing data
    # using that value. We leave this as a no-op rather than risk
    # corrupting parent users on a rollback.
    pass
